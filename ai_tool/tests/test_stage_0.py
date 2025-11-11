"""
Tests for the Stage 0 pipeline, focusing on control matching logic.
"""

import unittest
import asyncio
from unittest.mock import patch, MagicMock, call, AsyncMock

from pipeline import stage_0
from config import AppConfig
from constants import *


class TestStage0(unittest.TestCase):
    @patch("os.path.exists", return_value=False)
    @patch("pipeline.stage_0.AiClient")
    @patch("pipeline.stage_0.data_loader")
    @patch("pipeline.stage_0.data_parser")
    @patch("pipeline.stage_0.matching.match_baustein_to_zielobjekt", new_callable=AsyncMock)
    @patch("pipeline.stage_0.inheritance.get_all_inherited_controls")
    def test_run_phase_0_generates_correct_outputs(
        self,
        mock_get_inherited_controls,
        mock_match_baustein,
        mock_data_parser,
        mock_data_loader,
        mock_ai_client,
        mock_os_exists,
    ):
        """
        Test that the refactored Stage 0 pipeline correctly generates its
        two primary output files without performing control matching.
        """
        # --- Mock AppConfig ---
        mock_config = AppConfig()
        mock_config.is_test_mode = False

        # --- Mock Data Loading and Parsing ---
        mock_baustein = {"id": "B.1", "title": "Test Baustein"}
        mock_data_parser.parse_bsi_2023_controls.return_value = ([mock_baustein], [])
        mock_data_parser.parse_zielobjekte_hierarchy.return_value = {"Z.1": {}}
        mock_data_parser.parse_gpp_kompendium_controls.return_value = (
            {"Zielobjekt 1": ["GPP.1", "GPP.2"]},
            {"GPP.1": "GPP Control 1", "GPP.2": "GPP Control 2"},
        )

        # --- Mock AI and Inheritance Logic ---
        mock_match_baustein.return_value = "Z.1"
        mock_inherited_controls_with_titles = {
            "GPP.1": "GPP Control 1",
            "GPP.2": "GPP Control 2",
        }
        mock_get_inherited_controls.return_value = mock_inherited_controls_with_titles

        # --- Run the pipeline ---
        # Set up a side_effect function for load_json_file to handle multiple calls
        def load_json_side_effect(path):
            if path == PROMPT_CONFIG_PATH:
                return {"baustein_to_zielobjekt_prompt": "test prompt"}
            if path == BAUSTEIN_TO_ZIELOBJEKT_SCHEMA_PATH:
                return {"$schema": "http://json-schema.org/draft-07/schema#"}
            return {} # Default empty dict for other calls
        mock_data_loader.load_json_file.side_effect = load_json_side_effect

        # --- Run the pipeline ---
        with patch('pipeline.stage_0.app_config', mock_config):
            asyncio.run(stage_0.run_phase_0())

        # --- Assertions ---
        self.assertEqual(mock_data_loader.save_json_file.call_count, 2)

        # Verify bausteine_zielobjekte.json
        bausteine_call = mock_data_loader.save_json_file.call_args_list[0]
        self.assertEqual(bausteine_call.args[1], BAUSTEINE_ZIELOBJEKTE_JSON_PATH)
        self.assertDictEqual(
            bausteine_call.args[0],
            {"bausteine_zielobjekte_map": {"B.1": "Z.1"}},
        )

        # Verify zielobjekt_controls.json
        controls_call = mock_data_loader.save_json_file.call_args_list[1]
        self.assertEqual(controls_call.args[1], ZIELOBJEKT_CONTROLS_JSON_PATH)
        self.assertDictEqual(
            controls_call.args[0],
            {"zielobjekt_controls_map": {"Z.1": ["GPP.1", "GPP.2"]}},
        )

if __name__ == "__main__":
    unittest.main()
