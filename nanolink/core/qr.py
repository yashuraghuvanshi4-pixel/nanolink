"""Pure-Python QR code matrix generator and terminal/SVG renderer.

Implements ISO/IEC 18004 standard QR Code (Versions 1-3, Byte Mode, Error Correction L).
Requires zero third-party dependencies.
"""

from __future__ import annotations

from typing import List, Tuple

# Galois Field GF(2^8) with primitive polynomial x^8 + x^4 + x^3 + x^2 + 1 (0x11D / 285)
GF_EXP = [0] * 512
GF_LOG = [0] * 256

x = 1
for i in range(255):
    GF_EXP[i] = x
    GF_EXP[i + 255] = x
    GF_LOG[x] = i
    x <<= 1
    if x & 0x100:
        x ^= 0x11D


def gf_mul(x: int, y: int) -> int:
    """Multiply two numbers in GF(2^8)."""
    if x == 0 or y == 0:
        return 0
    return GF_EXP[GF_LOG[x] + GF_LOG[y]]


def rs_generator_poly(degree: int) -> List[int]:
    """Generate Reed-Solomon generator polynomial of given degree."""
    poly = [1]
    for i in range(degree):
        # Multiply poly by (x - α^i)
        next_poly = [0] * (len(poly) + 1)
        root = GF_EXP[i]
        for j, coeff in enumerate(poly):
            next_poly[j] ^= gf_mul(coeff, root)
            next_poly[j + 1] ^= coeff
        poly = next_poly
    return poly


def rs_encode(data: List[int], num_ec_bytes: int) -> List[int]:
    """Compute Reed-Solomon error correction bytes for data words."""
    gen = rs_generator_poly(num_ec_bytes)
    msg = list(data) + [0] * num_ec_bytes
    for i in range(len(data)):
        coeff = msg[i]
        if coeff != 0:
            for j in range(len(gen)):
                msg[i + j] ^= gf_mul(gen[j], coeff)
    return msg[len(data):]


# Capacity specifications for Error Correction Level L:
# (Version, Size, Total Data Bytes, EC Bytes)
QR_SPECS = [
    (1, 21, 19, 7),
    (2, 25, 34, 10),
    (3, 29, 55, 15),
    (4, 33, 80, 20),
]


def select_version(data_len: int) -> Tuple[int, int, int, int]:
    """Select the smallest QR version that fits the byte payload."""
    for ver, size, data_bytes, ec_bytes in QR_SPECS:
        # Byte mode header: 4 bits mode + 8 bits count = 12 bits = 1.5 bytes
        if data_len + 2 <= data_bytes:
            return (ver, size, data_bytes, ec_bytes)
    raise ValueError(f"Payload too large for compact QR generator ({data_len} bytes)")


class QRCode:
    """Generates and renders QR Codes."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.raw_bytes = text.encode("utf-8")
        self.version, self.size, self.data_cap, self.ec_bytes = select_version(len(self.raw_bytes))
        self.matrix: List[List[int]] = [[0] * self.size for _ in range(self.size)]
        self.reserved: List[List[bool]] = [[False] * self.size for _ in range(self.size)]
        self._build_matrix()

    def _set_module(self, r: int, c: int, val: int, reserved: bool = True) -> None:
        if 0 <= r < self.size and 0 <= c < self.size:
            self.matrix[r][c] = val
            if reserved:
                self.reserved[r][c] = True

    def _draw_finder_pattern(self, top: int, left: int) -> None:
        for r in range(-1, 8):
            for c in range(-1, 8):
                nr, nc = top + r, left + c
                if 0 <= nr < self.size and 0 <= nc < self.size:
                    if 0 <= r <= 6 and 0 <= c <= 6:
                        if r in (0, 6) or c in (0, 6) or (2 <= r <= 4 and 2 <= c <= 4):
                            self._set_module(nr, nc, 1)
                        else:
                            self._set_module(nr, nc, 0)
                    else:
                        self._set_module(nr, nc, 0)

    def _draw_alignment_pattern(self, cr: int, cc: int) -> None:
        for r in range(-2, 3):
            for c in range(-2, 3):
                val = 1 if max(abs(r), abs(c)) in (0, 2) else 0
                self._set_module(cr + r, cc + c, val)

    def _build_matrix(self) -> None:
        # 1. Finder patterns
        self._draw_finder_pattern(0, 0)
        self._draw_finder_pattern(0, self.size - 7)
        self._draw_finder_pattern(self.size - 7, 0)

        # 2. Timing patterns
        for i in range(8, self.size - 8):
            val = 1 if i % 2 == 0 else 0
            if not self.reserved[6][i]:
                self._set_module(6, i, val)
            if not self.reserved[i][6]:
                self._set_module(i, 6, val)

        # 3. Alignment patterns for v2+
        if self.version >= 2:
            align_pos = [6, 18] if self.version == 2 else [6, 22] if self.version == 3 else [6, 26]
            for r in align_pos:
                for c in align_pos:
                    if not (r <= 8 and c <= 8) and not (r <= 8 and c >= self.size - 8) and not (r >= self.size - 8 and c <= 8):
                        self._draw_alignment_pattern(r, c)

        # Dark module
        self._set_module(4 * self.version + 9, 8, 1)

        # Reserve format information area
        for i in range(9):
            if not self.reserved[8][i]:
                self.reserved[8][i] = True
            if not self.reserved[i][8]:
                self.reserved[i][8] = True
        for i in range(8):
            self.reserved[8][self.size - 1 - i] = True
            self.reserved[self.size - 1 - i][8] = True

        # 4. Encode data bitstream
        bitstream = []
        # Mode indicator: Byte mode = 0100 (4 bits)
        bitstream.extend([0, 1, 0, 0])
        # Character count indicator (8 bits for v1-9 byte mode)
        char_count = len(self.raw_bytes)
        for i in range(7, -1, -1):
            bitstream.append((char_count >> i) & 1)
        # Data bytes
        for b in self.raw_bytes:
            for i in range(7, -1, -1):
                bitstream.append((b >> i) & 1)

        # Terminator (up to 4 bits)
        total_data_bits = self.data_cap * 8
        rem = total_data_bits - len(bitstream)
        bitstream.extend([0] * min(4, rem))

        # Pad to multiple of 8
        while len(bitstream) % 8 != 0:
            bitstream.append(0)

        # Pad bytes 0xEC (236) and 0x11 (17)
        pad_bytes = [0xEC, 0x11]
        pad_idx = 0
        while len(bitstream) < total_data_bits:
            b = pad_bytes[pad_idx % 2]
            for i in range(7, -1, -1):
                bitstream.append((b >> i) & 1)
            pad_idx += 1

        # Convert to bytes
        data_words = []
        for i in range(0, len(bitstream), 8):
            byte = 0
            for bit in bitstream[i : i + 8]:
                byte = (byte << 1) | bit
            data_words.append(byte)

        # Compute error correction bytes
        ec_words = rs_encode(data_words, self.ec_bytes)
        final_bytes = data_words + ec_words

        # Convert final bytes into full bit sequence
        final_bits = []
        for b in final_bytes:
            for i in range(7, -1, -1):
                final_bits.append((b >> i) & 1)

        # 5. Place data bits using zigzag column traversal
        bit_idx = 0
        r = self.size - 1
        c = self.size - 1
        dir_up = True

        while c > 0:
            if c == 6:  # Skip vertical timing pattern column
                c -= 1
            for _ in range(self.size):
                for dc in (0, -1):
                    col = c + dc
                    row = r
                    if not self.reserved[row][col]:
                        bit = final_bits[bit_idx] if bit_idx < len(final_bits) else 0
                        # Mask pattern 0: (row + col) % 2 == 0
                        masked = bit ^ (1 if (row + col) % 2 == 0 else 0)
                        self.matrix[row][col] = masked
                        bit_idx += 1
                r += -1 if dir_up else 1
            dir_up = not dir_up
            r += 1 if dir_up else -1
            c -= 2

        # 6. Format info: Level L, Mask 0 -> 15-bit format sequence 0x77C4 (0b111011111000100)
        # Standard BCH(15,5) format with mask 0x5412 XOR
        format_bits = [1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0]
        # Top-left placement
        pos_tl = [
            (8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 7), (8, 8),
            (7, 8), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8),
        ]
        for (row, col), bit in zip(pos_tl, format_bits):
            self.matrix[row][col] = bit

        # Bottom-left / Top-right placement
        pos_split = [
            (self.size - 1, 8), (self.size - 2, 8), (self.size - 3, 8),
            (self.size - 4, 8), (self.size - 5, 8), (self.size - 6, 8),
            (self.size - 7, 8), (8, self.size - 8), (8, self.size - 7),
            (8, self.size - 6), (8, self.size - 5), (8, self.size - 4),
            (8, self.size - 3), (8, self.size - 2), (8, self.size - 1),
        ]
        for (row, col), bit in zip(pos_split, format_bits):
            self.matrix[row][col] = bit

    def to_terminal(self, border: int = 1) -> str:
        """Render high-resolution QR Code in terminal using Unicode half-blocks.

        Pairs 2 vertical pixels per text row:
        - Both 0: ' ' (White)
        - Top 1, Bot 0: '▀'
        - Top 0, Bot 1: '▄'
        - Both 1: '█'
        """
        lines = []
        pad = border
        total_dim = self.size + 2 * pad

        full_grid = [[0] * total_dim for _ in range(total_dim)]
        for r in range(self.size):
            for c in range(self.size):
                full_grid[r + pad][c + pad] = self.matrix[r][c]

        # Invert for dark terminal background (black on white)
        # Pair rows r and r+1
        for r in range(0, total_dim, 2):
            line_chars = []
            for c in range(total_dim):
                top = full_grid[r][c]
                bot = full_grid[r + 1][c] if r + 1 < total_dim else 0
                if top == 1 and bot == 1:
                    line_chars.append("\033[47;30m█\033[0m")
                elif top == 1 and bot == 0:
                    line_chars.append("\033[47;30m▀\033[0m")
                elif top == 0 and bot == 1:
                    line_chars.append("\033[47;30m▄\033[0m")
                else:
                    line_chars.append(" ")
            lines.append("".join(line_chars))

        return "\n".join(lines)

    def to_ascii(self, border: int = 2) -> str:
        """Render QR Code using standard ASCII characters (## for dark, spaces for light)."""
        lines = []
        pad = border
        total_dim = self.size + 2 * pad
        for r in range(total_dim):
            row_chars = []
            for c in range(total_dim):
                if pad <= r < self.size + pad and pad <= c < self.size + pad:
                    val = self.matrix[r - pad][c - pad]
                    row_chars.append("██" if val == 1 else "  ")
                else:
                    row_chars.append("  ")
            lines.append("".join(row_chars))
        return "\n".join(lines)

    def to_svg(self, module_size: int = 10, border: int = 4) -> str:
        """Render QR Code as an SVG vector image."""
        total_dim = (self.size + 2 * border) * module_size
        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_dim} {total_dim}" width="{total_dim}" height="{total_dim}">',
            f'<rect width="100%" height="100%" fill="#ffffff"/>',
            '<path d="',
        ]
        path_data = []
        for r in range(self.size):
            for c in range(self.size):
                if self.matrix[r][c] == 1:
                    x = (c + border) * module_size
                    y = (r + border) * module_size
                    path_data.append(f"M{x},{y}h{module_size}v{module_size}h-{module_size}z")
        svg_parts.append(" ".join(path_data))
        svg_parts.append('" fill="#000000"/>')
        svg_parts.append("</svg>")
        return "".join(svg_parts)
