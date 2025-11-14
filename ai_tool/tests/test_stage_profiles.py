"""
Unit tests for the stage_profiles pipeline stage.
"""

import os
import json
import unittest
from unittest.mock import patch, mock_open, MagicMock

from pipeline import stage_profiles
from constants import SDT_PROFILES_DIR

class TestStageProfiles(unittest.TestCase):
    """
    Test suite for the OSCAL profile generation stage.
    """

    def setUp(self):
        """
        Set up the test environment.
        """
        self.output_dir = SDT_PROFILES_DIR
        self.mock_zielobjekt_controls = {
            "zielobjekt_controls_map": {
                "efd76832-f5a1-432a-836d-c8d5c6d212cc": ["ASST.3.1", "ASST.3.1.1"],
                "d2a23b62-9c66-4f72-98e2-17518d5dbe0f": ["ASST.3.12"],
                "00000000-0000-0000-0000-000000000000": ["TEST.1.1"],
                "ISMS": ["ISMS.1", "ISMS.2"]
            }
        }
        self.mock_zielobjekte_csv = [
            {"UUID": "efd76832-f5a1-432a-836d-c8d5c6d212cc", "Zielobjekt": "Administrierende"},
            {"UUID": "d2a23b62-9c66-4f72-98e2-17518d5dbe0f", "Zielobjekt": "Cloud-Dienste"}
        ]

    @patch('pipeline.stage_profiles.create_dir_if_not_exists')
    @patch('pipeline.stage_profiles.read_json_file')
    @patch('pipeline.stage_profiles.read_csv_file')
    @patch('pipeline.stage_profiles.write_json_file')
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
        self.assertEqual(mock_write_json.call_count, 3)

        # Verify the content of the written profiles
        call_args_list = [call.args for call in mock_write_json.call_args_list]

        # Profile 1: Administrierende
        admin_profile_args = next(args for args in call_args_list if "administrierende_profile.json" in args[0])
        self.assertIsNotNone(admin_profile_args)
        profile1_content = admin_profile_args[1]
        self.assertEqual(profile1_content['profile']['metadata']['title'], 'efd76832-f5a1-432a-836d-c8d5c6d212cc Administrierende')
        self.assertEqual(profile1_content['profile']['imports'][0]['include-controls'][0]['with-ids'], ["ASST.3.1", "ASST.3.1.1"])

        # Profile 2: Cloud-Dienste
        cloud_profile_args = next(args for args in call_args_list if "cloud-dienste_profile.json" in args[0])
        self.assertIsNotNone(cloud_profile_args)
        profile2_content = cloud_profile_args[1]
        self.assertEqual(profile2_content['profile']['metadata']['title'], 'd2a23b62-9c66-4f72-98e2-17518d5dbe0f Cloud-Dienste')
        self.assertEqual(profile2_content['profile']['imports'][0]['include-controls'][0]['with-ids'], ["ASST.3.12"])

        # Profile 3: ISMS
        isms_profile_args = next(args for args in call_args_list if "isms_profile.json" in args[0])
        self.assertIsNotNone(isms_profile_args)
        profile3_content = isms_profile_args[1]
        self.assertEqual(profile3_content['profile']['metadata']['title'], 'ISMS ISMS')
        self.assertEqual(profile3_content['profile']['imports'][0]['include-controls'][0]['with-ids'], ["ISMS.1", "ISMS.2"])

        # Verify that a warning is logged for the missing Zielobjekt
        mock_log_warning.assert_called_once_with("No name found for Zielobjekt with UUID 00000000-0000-0000-0000-000000000000. Skipping profile generation.")

if __name__ == '__main__':
    unittest.main()
