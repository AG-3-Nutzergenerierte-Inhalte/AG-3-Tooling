import unittest
from unittest.mock import patch

class TestStageGpp(unittest.TestCase):

    @patch('pipeline.stage_gpp.load_json_file', return_value={'catalog': {}})
    @patch('pipeline.stage_gpp.load_zielobjekte_csv', return_value=[])
    @patch('pipeline.stage_gpp.save_json_file')
    def test_run_stage_gpp_importable_and_runnable(self, mock_save_json, mock_load_csv, mock_load_json):
        """
        Tests that the stage_gpp module can be imported and its main function can be run without errors.
        Mocks out file I/O to prevent actual file operations.
        """
        try:
            from pipeline.stage_gpp import run_stage_gpp
            # The test passes if this runs without import or other errors
            run_stage_gpp()
        except Exception as e:
            self.fail(f"run_stage_gpp failed to import or run: {e}")

if __name__ == '__main__':
    unittest.main()
