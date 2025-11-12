"""
Tests for the Stage 'Profiles': OSCAL Profile Generation.
"""

import unittest
from unittest.mock import patch, MagicMock, call

from pipeline import stage_profiles
from constants import *


class TestStageProfiles(unittest.TestCase):
    @patch("pipeline.stage_profiles.data_loader")
    @patch("pipeline.stage_profiles.data_parser")
    def test_run_stage_profiles_generates_correct_outputs(
        self, mock_data_parser, mock_data_loader
    ):
        """
        Test that the Stage 'Profiles' pipeline correctly generates the OSCAL
        profile files for both Zielobjekte and ISMS controls.
        """
        # --- Mock Data Loading and Parsing ---
        mock_data_loader.load_text_file.return_value = "| ID | name | description | UUID |\n|---|---|---|---|\n| ISMS.1 | ISMS Control 1 | Desc 1 | uuid1 |"
        mock_data_parser.parse_gpp_isms_controls.return_value = ["ISMS.1"]

        mock_zielobjekt_controls = {
            "zielobjekt_controls_map": {"Z.1": ["GPP.1", "GPP.2"]}
        }
        mock_data_loader.load_json_file.return_value = mock_zielobjekt_controls

        mock_zielobjekte_data = [{"UUID": "Z.1", "name": "Test Zielobjekt"}]
        mock_data_loader.load_zielobjekte_csv.return_value = mock_zielobjekte_data
        mock_data_parser.parse_zielobjekte_hierarchy.return_value = {
            "Z.1": {"name": "Test Zielobjekt"}
        }

        # --- Run the pipeline ---
        stage_profiles.run_stage_profiles()

        # --- Assertions ---
        self.assertEqual(mock_data_loader.save_json_file.call_count, 3)

        # Verify ISMS controls mapping file
        isms_mapping_call = mock_data_loader.save_json_file.call_args_list[0]
        self.assertEqual(isms_mapping_call.args[1], PROZZESSBAUSTEINE_CONTROLS_JSON_PATH)
        self.assertDictEqual(
            isms_mapping_call.args[0],
            {"isms_controls": ["ISMS.1"]},
        )

        # Verify ISMS profile file
        isms_profile_call = mock_data_loader.save_json_file.call_args_list[1]
        self.assertTrue("ISMS_profile.json" in isms_profile_call.args[1])
        self.assertEqual(isms_profile_call.args[0]["profile"]["metadata"]["title"], "ISMS_profile")
        self.assertEqual(isms_profile_call.args[0]["profile"]["include"]["with-ids"], ["ISMS.1"])

        # Verify Zielobjekt profile file
        zielobjekt_profile_call = mock_data_loader.save_json_file.call_args_list[2]
        self.assertTrue("Test_Zielobjekt_profile.json" in zielobjekt_profile_call.args[1])
        self.assertEqual(zielobjekt_profile_call.args[0]["profile"]["metadata"]["title"], "Test Zielobjekt_profile")
        self.assertEqual(zielobjekt_profile_call.args[0]["profile"]["include"]["with-ids"], ["GPP.1", "GPP.2"])


if __name__ == "__main__":
    unittest.main()
