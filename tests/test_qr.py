import unittest
from nanolink.core.qr import QRCode, select_version, rs_encode


class TestQRCode(unittest.TestCase):
    def test_reed_solomon_encoding(self):
        # 3 bytes message with 2 EC bytes
        data = [16, 32, 64]
        ec = rs_encode(data, 2)
        self.assertEqual(len(ec), 2)
        for b in ec:
            self.assertTrue(0 <= b <= 255)

    def test_version_selection(self):
        # Version 1 fits small strings
        v1, size1, _, _ = select_version(10)
        self.assertEqual(v1, 1)
        self.assertEqual(size1, 21)

        # Longer URL requires Version 2 or 3
        v2, size2, _, _ = select_version(28)
        self.assertGreaterEqual(v2, 2)
        self.assertGreaterEqual(size2, 25)

    def test_qr_generation(self):
        qr = QRCode("https://nano.lk/abc")
        self.assertGreaterEqual(len(qr.matrix), 21)
        self.assertEqual(len(qr.matrix), len(qr.matrix[0]))

        # Finder pattern at top-left should be present
        self.assertEqual(qr.matrix[0][0], 1)
        self.assertEqual(qr.matrix[0][6], 1)
        self.assertEqual(qr.matrix[6][0], 1)
        self.assertEqual(qr.matrix[6][6], 1)

    def test_qr_render_terminal(self):
        qr = QRCode("https://example.com")
        term_str = qr.to_terminal()
        self.assertIn("█", term_str)

    def test_qr_render_ascii(self):
        qr = QRCode("https://example.com")
        ascii_str = qr.to_ascii()
        self.assertIn("██", ascii_str)

    def test_qr_render_svg(self):
        qr = QRCode("https://example.com")
        svg = qr.to_svg()
        self.assertTrue(svg.startswith("<svg"))
        self.assertTrue(svg.endswith("</svg>"))
        self.assertIn('fill="#000000"', svg)


if __name__ == "__main__":
    unittest.main()
