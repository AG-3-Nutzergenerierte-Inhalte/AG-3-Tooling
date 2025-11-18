
import unittest
from unittest.mock import patch, AsyncMock
import asyncio

from config import app_config
from pipeline.stage_match_bausteine import run_stage_match_bausteine

class TestStageMatchBausteine(unittest.TestCase):

    @patch('pipeline.stage_match_bausteine.find_bausteine_with_prose')
    @patch('pipeline.stage_match_bausteine.load_json_file')
    @patch('pipeline.stage_match_bausteine.load_zielobjekte_csv')
    @patch('pipeline.stage_match_bausteine.save_json_file')
    @patch('pipeline.stage_match_bausteine.AiClient')
    def test_run_stage_match_bausteine_success(
        self, mock_ai_client, mock_save_json, mock_load_csv, mock_load_json, mock_find_bausteine
    ):
        # Arrange
        app_config.is_test_mode = True
        app_config.overwrite_temp_files = True

        mock_ai_instance = mock_ai_client.return_value
        mock_ai_instance.generate_validated_json_response = AsyncMock(
            return_value={"matched_zielobjekt": "Test Zielobjekt"}
        )

        mock_load_json.return_value = {"baustein_to_zielobjekt_prompt": "test prompt"}
        mock_load_csv.return_value = [{"UUID": "uuid-1", "Zielobjekt": "Test Zielobjekt", "Definition": "def"}]
        mock_find_bausteine.return_value = [{"id": "APP.1", "title": "Test Baustein", "description": "desc"}]

        # Act
        asyncio.run(run_stage_match_bausteine())

        # Assert
        mock_save_json.assert_called_once()
        saved_data = mock_save_json.call_args[0][0]
        self.assertEqual(saved_data["baustein_zielobjekt_map"], {"APP.1": "uuid-1"})

        # Clean up
        app_config.is_test_mode = False
        app_config.overwrite_temp_files = False


if __name__ == '__main__':
    unittest.main()
