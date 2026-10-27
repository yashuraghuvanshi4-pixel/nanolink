import unittest
from nanolink.core.base62 import (
    BASE62_ALPHABET,
    encode,
    decode,
    generate_code_from_hash,
    generate_random_code,
)


class TestBase62(unittest.TestCase):
    def test_encode_zero(self):
        self.assertEqual(encode(0), "0")

    def test_encode_single_digits(self):
        self.assertEqual(encode(1), "1")
        self.assertEqual(encode(9), "9")
        self.assertEqual(encode(10), "a")
        self.assertEqual(encode(35), "z")
        self.assertEqual(encode(36), "A")
        self.assertEqual(encode(61), "Z")

    def test_encode_large_numbers(self):
        self.assertEqual(encode(62), "10")
        self.assertEqual(encode(3843), "ZZ")
        self.assertEqual(encode(3844), "100")

    def test_decode_basic(self):
        self.assertEqual(decode("0"), 0)
        self.assertEqual(decode("1"), 1)
        self.assertEqual(decode("a"), 10)
        self.assertEqual(decode("Z"), 61)
        self.assertEqual(decode("10"), 62)
        self.assertEqual(decode("ZZ"), 3843)
        self.assertEqual(decode("100"), 3844)

    def test_encode_decode_roundtrip(self):
        test_values = [0, 1, 42, 61, 62, 1000, 999999, 123456789012345]
        for val in test_values:
            with self.subTest(val=val):
                self.assertEqual(decode(encode(val)), val)

    def test_encode_negative_raises(self):
        with self.assertRaises(ValueError):
            encode(-1)

    def test_decode_invalid_chars_raises(self):
        with self.assertRaises(ValueError):
            decode("invalid-char!")
        with self.assertRaises(ValueError):
            decode("")

    def test_generate_code_from_hash_determinism(self):
        url = "https://github.com/yashuraghuvanshi4-pixel"
        code1 = generate_code_from_hash(url, length=7)
        code2 = generate_code_from_hash(url, length=7)
        self.assertEqual(code1, code2)
        self.assertEqual(len(code1), 7)
        for char in code1:
            self.assertIn(char, BASE62_ALPHABET)

    def test_generate_code_from_hash_with_salt(self):
        url = "https://example.com"
        code_no_salt = generate_code_from_hash(url, length=7, salt="")
        code_with_salt = generate_code_from_hash(url, length=7, salt="attempt_1")
        self.assertNotEqual(code_no_salt, code_with_salt)

    def test_generate_random_code(self):
        code = generate_random_code(length=8)
        self.assertEqual(len(code), 8)
        for char in code:
            self.assertIn(char, BASE62_ALPHABET)


if __name__ == "__main__":
    unittest.main()
