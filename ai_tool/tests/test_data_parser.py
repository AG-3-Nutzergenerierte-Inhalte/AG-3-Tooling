import unittest
from unittest.mock import patch, mock_open
from ai_tool.src.utils import data_parser

class TestDataParser(unittest.TestCase):

    def test_parse_gpp_kompendium_controls_title_handling(self):
        """
        Tests that parse_gpp_kompendium_controls correctly handles both
        list and string titles for G++ controls.
        """
        mock_gpp_data = {
            "catalog": {
                "groups": [
                    {
                        "groups": [
                            {
                                "controls": [
                                    {
                                        "id": "GPP.01",
                                        "title": ["First Title", "Second Title"],
                                        "parts": [
                                            {
                                                "props": [
                                                    {
                                                        "name": "target_objects",
                                                        "value": "Server, Client"
                                                    }
                                                ]
                                            }
                                        ]
                                    },
                                    {
                                        "id": "GPP.02",
                                        "title": "Single Title",
                                        "parts": [
                                            {
                                                "props": [
                                                    {
                                                        "name": "target_objects",
                                                        "value": "Network"
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        }

        _, gpp_control_titles = data_parser.parse_gpp_kompendium_controls(mock_gpp_data)

        # Check that the control with a list title has its first title extracted
        self.assertIn("GPP.01", gpp_control_titles)
        self.assertEqual(gpp_control_titles["GPP.01"], "First Title")

        # Check that the control with a string title is handled correctly
        self.assertIn("GPP.02", gpp_control_titles)
        self.assertEqual(gpp_control_titles["GPP.02"], "Single Title")

if __name__ == '__main__':
    unittest.main()
