import unittest
from utils.text_utils import sanitize_filename, replace_umlauts

class TestTextUtilsExtra(unittest.TestCase):
    def test_replace_umlauts(self):
        self.assertEqual(replace_umlauts("Müller"), "Mueller")
        self.assertEqual(replace_umlauts("ÄÖÜäöüß"), "AeOeUeaeoeuess")
        self.assertEqual(replace_umlauts("NoUmlauts"), "NoUmlauts")

    def test_sanitize_filename_with_umlauts(self):
        self.assertEqual(sanitize_filename("Müller Gebäude"), "mueller_gebaeude")
        self.assertEqual(sanitize_filename("Schloßstraße 1"), "schlossstrasse_1")

if __name__ == '__main__':
    unittest.main()
