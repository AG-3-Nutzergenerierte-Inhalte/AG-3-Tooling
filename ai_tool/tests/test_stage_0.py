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
    @patch(
        "pipeline.stage_0.inheritance.generate_full_zielobjekt_controls_map"
    )
    def test_run_phase_0_generates_correct_outputs(
        self,
        mock_generate_full_map,
        mock_match_baustein,
        mock_data_parser,
        mock_data_loader,
        mock_ai_client,
        mock_os_exists,
    ):
        """
        Test that Stage 0 correctly generates its two primary output files:
        - A deterministic map of all Zielobjekte to their controls.
        - An AI-driven map of Bausteine to Zielobjekte.
        """
        # --- Mock AppConfig ---
        mock_config = AppConfig()
        mock_config.is_test_mode = False

        # --- Mock Data Loading and Parsing ---
        mock_baustein = {
            "id": "B.1",
            "title": "Test Baustein",
            "description": "This is a test baustein.",
        }
        mock_zielobjekte_map = {
            "Z.1": {
                "Zielobjekt": "Test Zielobjekt",
                "Definition": "This is a test zielobjekt.",
            }
        }
        mock_data_parser.parse_bsi_2023_controls.return_value = ([mock_baustein], [])
        mock_data_parser.parse_zielobjekte_hierarchy.return_value = mock_zielobjekte_map
        mock_data_parser.parse_gpp_kompendium_controls.return_value = ({}, {})

        # --- Mock Inheritance and AI Logic ---
        mock_generate_full_map.return_value = {
            "Z.1": ["GPP.1", "GPP.2"]
        }
        mock_match_baustein.return_value = "Z.1"

        # --- Mock Data Loader ---
        def load_json_side_effect(path):
            if path == PROMPT_CONFIG_PATH:
                return {"baustein_to_zielobjekt_prompt": "test prompt"}
            if path == BAUSTEIN_TO_ZIELOBJEKT_SCHEMA_PATH:
                return {"$schema": "http://json-schema.org/draft-07/schema#"}
            return {}
        mock_data_loader.load_json_file.side_effect = load_json_side_effect

        # --- Run the pipeline ---
        with patch('pipeline.stage_0.app_config', mock_config):
            asyncio.run(stage_0.run_phase_0())

        # --- Assertions ---
        # Verify that the deterministic control map was generated and passed to save
        mock_generate_full_map.assert_called_once()

        # Verify that the AI matching was called for the mock baustein
        mock_match_baustein.assert_called_once()

        # Verify the final files were saved correctly
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
