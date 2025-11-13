"""
Unit tests for the stage_profiles pipeline stage.
"""

import os
import json
import unittest
from unittest.mock import patch, mock_open, MagicMock

from ai_tool.src.pipeline import stage_profiles
from ai_tool.src.constants import SDT_OUTPUT_DIR

class TestStageProfiles(unittest.TestCase):
    """
    Test suite for the OSCAL profile generation stage.
    """

    def setUp(self):
        """
        Set up the test environment.
        """
        self.output_dir = os.path.join(SDT_OUTPUT_DIR, "profiles")
        self.mock_zielobjekt_controls = {
            "zielobjekt_controls_map": {
                "efd76832-f5a1-432a-836d-c8d5c6d212cc": ["ASST.3.1", "ASST.3.1.1"],
                "d2a23b62-9c66-4f72-98e2-17518d5dbe0f": ["ASST.3.12"],
                "00000000-0000-0000-0000-000000000000": ["TEST.1.1"]
            }
        }
        self.mock_zielobjekte_csv = [
            {"UUID": "efd76832-f5a1-432a-836d-c8d5c6d212cc", "Zielobjekt": "Administrierende"},
            {"UUID": "d2a23b62-9c66-4f72-98e2-17518d5dbe0f", "Zielobjekt": "Cloud-Dienste"}
        ]

    @patch('ai_tool.src.pipeline.stage_profiles.create_dir_if_not_exists')
    @patch('ai_tool.src.pipeline.stage_profiles.read_json_file')
    @patch('ai_tool.src.pipeline.stage_profiles.read_csv_file')
    @patch('ai_tool.src.pipeline.stage_profiles.write_json_file')
    @patch('logging.Logger.warning')
    def test_run_stage_profiles(self, mock_log_warning, mock_write_json, mock_read_csv, mock_read_json, mock_create_dir):
        """
        Test the successful execution of the run_stage_profiles function.
        """
        mock_read_json.return_value = self.mock_zielobjekt_controls
        mock_read_csv.return_value = self.mock_zielobjekte_csv

        stage_profiles.run_stage_profiles()

        # Verify that the output directory is created
        mock_create_dir.assert_called_once_with(self.output_dir)

        # Verify that the correct number of profiles are written
        self.assertEqual(mock_write_json.call_count, 2)

        # Verify the content of the written profiles
        first_call_args = mock_write_json.call_args_list[0].args
        second_call_args = mock_write_json.call_args_list[1].args

        # First profile
        self.assertIn("administrierende_profile.json", first_call_args[0])
        profile1_content = first_call_args[1]
        self.assertEqual(profile1_content['profile']['metadata']['title'], 'efd76832-f5a1-432a-836d-c8d5c6d212cc Administrierende')
        self.assertEqual(profile1_content['profile']['imports'][0]['include-controls'][0]['with-ids'], ["ASST.3.1", "ASST.3.1.1"])

        # Second profile
        self.assertIn("cloud-dienste_profile.json", second_call_args[0])
        profile2_content = second_call_args[1]
        self.assertEqual(profile2_content['profile']['metadata']['title'], 'd2a23b62-9c66-4f72-98e2-17518d5dbe0f Cloud-Dienste')
        self.assertEqual(profile2_content['profile']['imports'][0]['include-controls'][0]['with-ids'], ["ASST.3.12"])

        # Verify that a warning is logged for the missing Zielobjekt
        mock_log_warning.assert_called_once_with("No name found for Zielobjekt with UUID 00000000-0000-0000-0000-000000000000. Skipping profile generation.")

if __name__ == '__main__':
    unittest.main()
