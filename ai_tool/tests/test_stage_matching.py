"""
Tests for the Stage 'Matching' pipeline.
"""

import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock, mock_open

from pipeline import stage_matching
from config import AppConfig
from constants import *


class TestStageMatching(unittest.TestCase):
    @patch("os.path.exists", return_value=False)
    @patch("pipeline.stage_matching.AiClient")
    @patch("pipeline.stage_matching.data_loader")
    def test_run_stage_matching_flow(
        self, mock_data_loader, mock_ai_client_constructor, mock_os_exists
    ):
        """
        Test the full flow of the stage_matching pipeline, from data loading
        to the final JSON output, with mocked AI responses.
        """
        # --- Mock AppConfig ---
        mock_config = AppConfig()
        mock_config.is_test_mode = False

        # --- Mock AI Client ---
        mock_ai_client = MagicMock()
        mock_ai_client.prompt_config = {
            "anforderung_to_kontrolle_1_1_prompt": "test_prompt"
        }
        # Mock the async method directly on the instance
        mock_ai_client.generate_json_response = AsyncMock(
            return_value={
                "mapping": {"B.1.A1": "GPP.1"},
                "unmapped_gpp": ["GPP.2"],
                "unmapped_ed2023": ["B.1.A2"],
            }
        )
        mock_ai_client_constructor.return_value = mock_ai_client

        # --- Mock Data Loading ---
        mock_data_loader.load_json_file.side_effect = [
            {"bausteine_zielobjekte_map": {"B.1": "Z.1"}},
            {"zielobjekt_controls_map": {"Z.1": ["GPP.1", "GPP.2"]}},
            {"$schema": "http://json-schema.org/draft-07/schema#"}, # matching_schema
        ]
        # Make the mock return the correct values for each call
        mock_data_loader.load_json_file.side_effect = lambda path: {
            BAUSTEINE_ZIELOBJEKTE_JSON_PATH: {"bausteine_zielobjekte_map": {"B.1": "Z.1"}},
            ZIELOBJEKT_CONTROLS_JSON_PATH: {"zielobjekt_controls_map": {"Z.1": ["GPP.1", "GPP.2"]}},
            MATCHING_SCHEMA_PATH: {"$schema": "http://json-schema.org/draft-07/schema#"},
            PROMPT_CONFIG_PATH: {"anforderung_to_kontrolle_1_1_prompt": "test prompt"},
        }.get(path, {})
        mock_data_loader.load_zielobjekte_csv.return_value = [
            {"UUID": "Z.1", "name": "Zielobjekt 1", "ChildOfUUID": ""}
        ]

        # Mock reading the markdown files
        mock_gpp_md = "| GPP-ID  | Titel | Beschreibung |\n| :--- | :--- | :--- |\n| GPP.1 | GPP Control 1 | Desc 1 |\n| GPP.2 | GPP Control 2 | Desc 2 |"
        mock_bsi_md = "| Anforderung-ID | Anforderungstitel | Anforderungstext |\n| :--- | :--- | :--- |\n| B.1.A1 | BSI Anforderung 1 | Text 1 |\n| B.1.A2 | BSI Anforderung 2 | Text 2 |"

        m = mock_open(read_data=mock_gpp_md)
        m.side_effect = [
            mock_gpp_md, # GPP_STRIPPED_MD_PATH
            "", # GPP_STRIPPED_ISMS_MD_PATH
            mock_bsi_md, # BSI_STRIPPED_MD_PATH
        ]
        mock_data_loader.load_text_file.side_effect = [
            mock_gpp_md,
            "",
            mock_bsi_md,
        ]


        # --- Run the pipeline ---
        with patch('pipeline.stage_matching.app_config', mock_config):
            asyncio.run(stage_matching.run_stage_matching())

        # --- Assertions ---
        # Verify AI client was called correctly
        mock_ai_client.generate_json_response.assert_called_once()
        call_args = mock_ai_client.generate_json_response.call_args
        self.assertIn("Ed2023 Source:", call_args.kwargs["context"])
        self.assertIn("G++ Source:", call_args.kwargs["context"])

        # Verify the final JSON output was saved correctly
        mock_data_loader.save_json_file.assert_called_once()
        output_filename = mock_data_loader.save_json_file.call_args[0][1]
        output_data = mock_data_loader.save_json_file.call_args[0][0]

        self.assertEqual(output_filename, CONTROLS_ANFORDERUNGEN_JSON_PATH)
        expected_output = {
            "Z.1": {
                "zielobjekt_name": "Zielobjekt 1",
                "baustein_id": "B.1",
                "mapping": {"B.1.A1": "GPP.1"},
                "unmapped_gpp": ["GPP.2"],
                "unmapped_ed2023": ["B.1.A2"],
            }
        }
        self.assertDictEqual(output_data, expected_output)


if __name__ == "__main__":
    unittest.main()
