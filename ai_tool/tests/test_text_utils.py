import unittest
from utils.text_utils import sanitize_oscal_prop_name

class TestTextUtils(unittest.TestCase):

    def test_sanitize_oscal_prop_name(self):
        self.assertEqual(sanitize_oscal_prop_name("ValidName"), "ValidName")
        self.assertEqual(sanitize_oscal_prop_name("Valid_Name-With.Dots"), "Valid_Name-With.Dots")
        self.assertEqual(sanitize_oscal_prop_name("1InvalidStart"), "_1InvalidStart")
        self.assertEqual(sanitize_oscal_prop_name(" Invalid Chars "), "_Invalid_Chars_")
        self.assertEqual(sanitize_oscal_prop_name(""), "_")
        self.assertEqual(sanitize_oscal_prop_name("123"), "_123")
        self.assertEqual(sanitize_oscal_prop_name(" leading_space"), "_leading_space")
        self.assertEqual(sanitize_oscal_prop_name("Größe"), "Größe")
        self.assertEqual(sanitize_oscal_prop_name("Maßnahme"), "Maßnahme")
        self.assertEqual(sanitize_oscal_prop_name(" François"), "_François")

if __name__ == '__main__':
    unittest.main()
