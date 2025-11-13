import unittest
from unittest.mock import patch, MagicMock

class TestStageMatchBausteine(unittest.TestCase):

    @patch('pipeline.stage_match_bausteine.load_json_file', return_value={})
    @patch('pipeline.stage_match_bausteine.load_zielobjekte_csv', return_value=[])
    @patch('pipeline.stage_match_bausteine.save_json_file')
    @patch('pipeline.stage_match_bausteine.AiClient')
    def test_run_stage_match_bausteine_importable_and_runnable(self, mock_ai_client, mock_save_json, mock_load_csv, mock_load_json):
        """
        Tests that the stage_match_bausteine module can be imported and its main function can be run without errors.
        Mocks out file I/O and the AI client.
        """
        # Mock the async run method
        mock_ai_client.return_value.generate_validated_json_response = MagicMock()

        try:
            from pipeline.stage_match_bausteine import run_stage_match_bausteine
            # The test passes if this runs without import or other errors
            run_stage_match_bausteine()
        except Exception as e:
            self.fail(f"run_stage_match_bausteine failed to import or run: {e}")

if __name__ == '__main__':
    unittest.main()
