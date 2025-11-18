
import unittest
from unittest.mock import patch, AsyncMock
import asyncio

from pipeline.stage_decomposition import run_stage_decomposition
from constants import DECOMPOSED_ANFORDERUNGEN_JSON_PATH

class TestStageDecomposition(unittest.TestCase):

    @patch("pipeline.stage_decomposition.data_parser")
    @patch("pipeline.stage_decomposition.data_loader")
    @patch("pipeline.stage_decomposition.AiClient")
    def test_run_stage_decomposition_success(self, mock_ai_client, mock_data_loader, mock_data_parser):
        # Arrange
        mock_ai_instance = mock_ai_client.return_value
        mock_ai_instance.generate_validated_json_response = AsyncMock(return_value={
            "decomposed_anforderungen": [
                {
                    "original_anforderung_id": "ORP.4.A6",
                    "sub_requirements": [
                        { "id": "ORP.4.A6_sub_1", "description": "Sub-requirement 1 for ORP.4.A6" }
                    ]
                }
            ]
        })

        mock_data_loader.load_json_file.return_value = {"decomposition_prompt": "Test prompt"}
        mock_data_parser.get_anforderungen_for_bausteine.return_value = {"ORP.4.A6": "Test anforderung text"}

        # Act
        asyncio.run(run_stage_decomposition())

        # Assert
        mock_data_loader.save_json_file.assert_called_once()
        saved_data = mock_data_loader.save_json_file.call_args[0][0]
        self.assertEqual(len(saved_data["decomposed_anforderungen"]), 1)

    @patch("pipeline.stage_decomposition.data_loader")
    @patch("pipeline.stage_decomposition.AiClient")
    def test_run_stage_decomposition_no_ai_response(self, mock_ai_client, mock_data_loader):
        # Arrange
        mock_ai_instance = mock_ai_client.return_value
        mock_ai_instance.generate_validated_json_response = AsyncMock(return_value={"decomposed_anforderungen": []})
        mock_data_loader.load_json_file.return_value = {"decomposition_prompt": "Test prompt"}
        with patch("pipeline.stage_decomposition.data_parser.get_anforderungen_for_bausteine", return_value={"ORP.4.A6": "Test text"}):
            # Act & Assert
            with self.assertRaises(SystemExit):
                asyncio.run(run_stage_decomposition())

if __name__ == '__main__':
    unittest.main()
