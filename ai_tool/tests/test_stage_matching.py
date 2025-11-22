
import asyncio
import unittest
from unittest.mock import patch, MagicMock, mock_open, AsyncMock

from config import AppConfig
from constants import *
from pipeline import stage_matching


class TestStageMatching(unittest.TestCase):
    @patch("os.path.exists", return_value=False)
    @patch("pipeline.stage_matching.AiClient")
    @patch("pipeline.stage_matching.data_loader")
    def test_run_stage_matching_flow(
        self, mock_data_loader, mock_ai_client_constructor, mock_os_exists
    ):
        # --- Mock AppConfig ---
        mock_config = AppConfig()
        mock_config.is_test_mode = True

        # --- Mock AI Client ---
        mock_ai_client = MagicMock()
        mock_ai_client.generate_validated_json_response = AsyncMock(
            return_value={
                "mapping": {"APP.1.1.A1": "GPP.1"},
                "unmapped_gpp": ["GPP.2"],
                "unmapped_ed2023": ["APP.1.1.A2"],
            }
        )
        mock_ai_client_constructor.return_value = mock_ai_client

        # --- Mock Data Loading ---
        mock_data_loader.load_json_file.side_effect = lambda path: {
            BAUSTEIN_ZIELOBJEKT_JSON_PATH: {"baustein_zielobjekt_map": {"APP.1.1": "Z.1"}},
            ZIELOBJEKT_CONTROLS_JSON_PATH: {"zielobjekt_controls_map": {"Z.1": ["GPP.1", "GPP.2"]}},
            MATCHING_SCHEMA_PATH: {"$schema": "http://json-schema.org/draft-07/schema#"},
            PROMPT_CONFIG_PATH: {"anforderung_to_kontrolle_1_1_prompt": "test prompt"},
            BSI_2023_JSON_PATH: {
                "catalog": {
                    "groups": [
                        {
                            "id": "APP",
                            "groups": [
                                {
                                    "id": "APP.1.1",
                                    "controls": [
                                        {"id": "APP.1.1.A1"},
                                        {"id": "APP.1.1.A2"},
                                    ],
                                }
                            ],
                        }
                    ]
                }
            },
        }.get(path, {})
        mock_data_loader.load_zielobjekte_csv.return_value = [
            {"UUID": "Z.1", "Zielobjekt": "Zielobjekt 1", "ChildOfUUID": ""}
        ]

        mock_gpp_md = "| ID | name | description |\n|---|---|---|\n| GPP.1 | GPP Control 1 | Desc 1 |\n| GPP.2 | GPP Control 2 | Desc 2 |"
        mock_isms_md = "| ID | name | description |\n|---|---|---|\n| ISMS.1 | ISMS Control 1 | Desc 1 |"
        mock_bsi_md = "| ID | name | description |\n|---|---|---|\n| APP.1.1.A1 | BSI Anforderung 1 | Text 1 |\n| APP.1.1.A2 | BSI Anforderung 2 | Text 2 |"
        mock_data_loader.load_text_file.side_effect = [
            mock_gpp_md,
            mock_isms_md,
            mock_bsi_md,
        ]

        # --- Run the pipeline ---
        with patch('pipeline.stage_matching.app_config', mock_config):
            asyncio.run(stage_matching.run_stage_matching())

        # --- Assertions ---
        mock_ai_client.generate_validated_json_response.assert_called_once()

        # Verify that the final JSON is saved with the correct content
        expected_output = {
            "Z.1": {
                "zielobjekt_name": "Zielobjekt 1",
                "baustein_id": "APP.1.1",
                "mapping": {"APP.1.1.A1": "GPP.1"},
                "unmapped_gpp": ["GPP.2"],
                "unmapped_ed2023": ["APP.1.1.A2"],
            }
        }
        mock_data_loader.save_json_file.assert_called_once_with(
            expected_output, CONTROLS_ANFORDERUNGEN_JSON_PATH
        )


if __name__ == "__main__":
    unittest.main()
