import unittest
from unittest.mock import patch, mock_open, call
import os
import sys

# Adjust the Python path to include the 'src' directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Import the functions to be tested
from pipeline.stage_strip import _strip_gpp_file, _strip_bsi_file
# Import constants from the centralized source for assertions
from constants import (
    GPP_STRIPPED_MD_PATH,
    GPP_STRIPPED_ISMS_MD_PATH,
    BSI_STRIPPED_MD_PATH,
    BSI_STRIPPED_ISMS_MD_PATH,
    SDT_HELPER_OUTPUT_DIR,
)

# Load mock data content as strings to be used by mock_open
with open('ai_tool/tests/mock_gpp_kompendium.json', 'r', encoding='utf-8') as f:
    mock_gpp_content = f.read()
    # Also get the raw prose to calculate the correct slice for the test
    import json
    mock_gpp_prose = json.loads(mock_gpp_content)["catalog"]["groups"][0]["groups"][0]["controls"][0]["parts"][0]["prose"]


with open('ai_tool/tests/mock_bsi_2023.json', 'r', encoding='utf-8') as f:
    mock_bsi_content = f.read()

class TestStageStrip(unittest.TestCase):

    @patch('pipeline.stage_strip.os.makedirs')
    @patch('pipeline.stage_strip.GPP_KOMPENDIUM_JSON_PATH', 'ai_tool/tests/mock_gpp_kompendium.json')
    @patch('pipeline.stage_strip.app_config.overwrite_temp_files', True)
    @patch('pipeline.stage_strip.os.remove')
    @patch('pipeline.stage_strip.os.path.exists', return_value=True)
    def test_strip_gpp_file_handles_recursion_and_filtering(self, mock_exists, mock_remove, mock_makedirs):
        """
        Tests that the G++ stripping logic correctly processes nested controls
        and filters them into the appropriate files.
        """
        # Dynamically get the correct truncated prose from the mock file
        import json
        mock_data = json.loads(mock_gpp_content)
        target_objects_prose = mock_data["catalog"]["groups"][0]["groups"][0]["controls"][0]["parts"][0]["prose"]
        isms_control_prose = mock_data["catalog"]["groups"][0]["groups"][0]["controls"][1]["parts"][0]["prose"]
        expected_truncated_desc = isms_control_prose[:150]

        written_content = {}
        def mock_open_side_effect(filename, mode='r', **kwargs):
            if mode == 'r':
                return mock_open(read_data=mock_gpp_content).return_value

            mock_file = mock_open().return_value
            mock_file.write.side_effect = lambda data: written_content.update({filename: data})
            return mock_file

        with patch('builtins.open', side_effect=mock_open_side_effect):
            _strip_gpp_file()

            mock_makedirs.assert_called_once_with(SDT_HELPER_OUTPUT_DIR, exist_ok=True)
            mock_remove.assert_has_calls([
                call(GPP_STRIPPED_MD_PATH),
                call(GPP_STRIPPED_ISMS_MD_PATH)
            ], any_order=True)

            # --- Assertions for the file WITH target_objects ---
            target_objects_content = written_content.get(GPP_STRIPPED_MD_PATH, "")
            self.assertIn(f"| GPP.1.A1 | GPP Test Control (With Target Objects) | {target_objects_prose} | 12345-uuid-with-target |", target_objects_content)
            self.assertNotIn("GPP.2.A2", target_objects_content)
            self.assertNotIn("GPP.1.A1.1", target_objects_content)

            # --- Assertions for the ISMS file WITHOUT target_objects ---
            isms_content = written_content.get(GPP_STRIPPED_ISMS_MD_PATH, "")
            self.assertIn(f"| GPP.2.A2 | GPP Test Control (ISMS) | {expected_truncated_desc} | 67890-uuid-isms |", isms_content)
            # Check for the nested control
            self.assertIn("| GPP.1.A1.1 | Nested ISMS Control | This is a nested ISMS control. | nested-isms-uuid |", isms_content)
            # Ensure the parent control (which has target_objects) is NOT in the ISMS file
            self.assertNotIn("| GPP.1.A1 | GPP Test Control (With Target Objects)", isms_content)

    @patch('pipeline.stage_strip.os.makedirs')
    @patch('pipeline.stage_strip.BSI_2023_JSON_PATH', 'ai_tool/tests/mock_bsi_2023.json')
    def test_strip_bsi_file_filters_and_truncates(self, mock_makedirs):
        """
        Tests that the BSI stripping logic correctly filters controls into two
        separate files and truncates their descriptions.
        """
        written_content = {}

        def mock_open_side_effect(filename, mode='r', **kwargs):
            if mode == 'r':
                return mock_open(read_data=mock_bsi_content).return_value

            mock_file = mock_open().return_value
            mock_file.write.side_effect = lambda data: written_content.update({filename: data})
            return mock_file

        with patch('builtins.open', side_effect=mock_open_side_effect):
            _strip_bsi_file()

            mock_makedirs.assert_called_once_with(SDT_HELPER_OUTPUT_DIR, exist_ok=True)

            allowed_content = written_content.get(BSI_STRIPPED_MD_PATH, "")
            isms_content = written_content.get(BSI_STRIPPED_ISMS_MD_PATH, "")

            self.assertIn("| SYS.1.1.A1 | BSI Test Control (SYS) | This is a BSI test description for an allowed group. |", allowed_content)
            self.assertNotIn("ISMS.1.A1", allowed_content)

            expected_truncated_desc = "This is a BSI test description for a non-allowed group that should be long enough to be truncated. This part of the text will definitely be cut off be"
            self.assertIn(f"| ISMS.1.A1 | BSI Test Control (ISMS) | {expected_truncated_desc} |", isms_content)
            self.assertTrue(len(expected_truncated_desc) == 150)
            self.assertNotIn("well over one hundred and fifty characters long", isms_content)
            self.assertNotIn("SYS.1.1.A1", isms_content)

if __name__ == '__main__':
    unittest.main()
