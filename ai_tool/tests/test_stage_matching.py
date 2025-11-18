
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
    def test_run_stage_matching_success(
        self, mock_data_loader, mock_ai_client_constructor, mock_os_exists
    ):
        # --- Mock AppConfig ---
        mock_config = AppConfig()
        mock_config.is_test_mode = True

        # --- Mock AI Client ---
        mock_ai_client = MagicMock()
        mock_ai_client.generate_validated_json_response = AsyncMock(
            return_value={
                "mapping": {"APP.1.A1_sub_1": "GPP.1"},
            }
        )
        mock_ai_client_constructor.return_value = mock_ai_client

        # --- Mock Data Loading ---
        mock_data_loader.load_json_file.side_effect = lambda path: {
            BAUSTEIN_ZIELOBJEKT_JSON_PATH: {"baustein_zielobjekt_map": {"APP.1": "Z.1"}},
            ZIELOBJEKT_CONTROLS_JSON_PATH: {"zielobjekt_controls_map": {"Z.1": ["GPP.1"]}},
            DECOMPOSED_ANFORDERUNGEN_JSON_PATH: {
                "decomposed_anforderungen": [
                    {
                        "original_anforderung_id": "APP.1.A1",
                        "sub_requirements": [
                            {"id": "APP.1.A1_sub_1", "description": "Sub 1"},
                        ],
                    }
                ]
            },
            PROMPT_CONFIG_PATH: {"anforderung_to_kontrolle_1_1_prompt": "test prompt"}
        }.get(path, {})
        mock_data_loader.load_zielobjekte_csv.return_value = [{"UUID": "Z.1", "Zielobjekt": "Zielobjekt 1"}]
        mock_data_loader.load_text_file.return_value = "| ID | name |\n|---|---|\n| GPP.1 | GPP 1 |"

        # --- Run the pipeline ---
        with patch('pipeline.stage_matching.app_config', mock_config):
            asyncio.run(stage_matching.run_stage_matching())

        # --- Assertions ---
        mock_data_loader.save_json_file.assert_called_once()


    @patch("os.path.exists", return_value=False)
    @patch("pipeline.stage_matching.AiClient")
    @patch("pipeline.stage_matching.data_loader")
    def test_run_stage_matching_no_ai_response(
        self, mock_data_loader, mock_ai_client_constructor, mock_os_exists
    ):
        # --- Mock AppConfig ---
        mock_config = AppConfig()
        mock_config.is_test_mode = True
        # --- Mock AI Client ---
        mock_ai_client = MagicMock()
        mock_ai_client.generate_validated_json_response = AsyncMock(return_value=None)
        mock_ai_client_constructor.return_value = mock_ai_client
        # --- Mock Data Loading ---
        mock_data_loader.load_json_file.side_effect = lambda path: {
            BAUSTEIN_ZIELOBJEKT_JSON_PATH: {"baustein_zielobjekt_map": {"APP.1": "Z.1"}},
            ZIELOBJEKT_CONTROLS_JSON_PATH: {"zielobjekt_controls_map": {"Z.1": ["GPP.1"]}},
            DECOMPOSED_ANFORDERUNGEN_JSON_PATH: {
                "decomposed_anforderungen": [
                    {
                        "original_anforderung_id": "APP.1.A1",
                        "sub_requirements": [
                            {"id": "APP.1.A1_sub_1", "description": "Sub 1"},
                        ],
                    }
                ]
            },
            PROMPT_CONFIG_PATH: {"anforderung_to_kontrolle_1_1_prompt": "test prompt"}
        }.get(path, {})
        mock_data_loader.load_zielobjekte_csv.return_value = [{"UUID": "Z.1", "Zielobjekt": "Zielobjekt 1"}]
        mock_data_loader.load_text_file.return_value = "| ID | name |\n|---|---|\n| GPP.1 | GPP 1 |"
        # --- Run the pipeline ---
        with patch('pipeline.stage_matching.app_config', mock_config):
            with self.assertRaises(SystemExit):
                asyncio.run(stage_matching.run_stage_matching())


if __name__ == "__main__":
    unittest.main()
