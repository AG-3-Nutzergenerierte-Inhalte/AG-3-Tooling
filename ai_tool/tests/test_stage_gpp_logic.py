import unittest
from unittest.mock import patch, MagicMock
from pipeline.stage_gpp import _process_control

class TestStageGppLogic(unittest.TestCase):
    def test_process_control_methodik(self):
        # Control without target_objects and modalverb MUSS
        control = {
            "id": "SENS.1.1",
            "title": "Test Methodik",
            "props": [{"name": "alt-identifier", "value": "uuid-1"}],
            "parts": [{
                "name": "statement",
                "prose": "MUSS do something",
                "props": [{"name": "modalverb", "value": "MUSS"}]
            }]
        }
        keys, uuid, simplified = _process_control(control)
        self.assertIn("Methodik", keys)
        self.assertEqual(uuid, "uuid-1")

    def test_process_control_prozesse(self):
        # Control without target_objects and modalverb NOT MUSS
        control = {
            "id": "SENS.1.2",
            "title": "Test Prozesse",
            "props": [{"name": "alt-identifier", "value": "uuid-2"}],
            "parts": [{
                "name": "statement",
                "prose": "SOLLTE do something",
                "props": [{"name": "modalverb", "value": "SOLLTE"}]
            }]
        }
        keys, uuid, simplified = _process_control(control)
        self.assertIn("SENSprozesse", keys)
        self.assertEqual(uuid, "uuid-2")

    def test_process_control_with_target(self):
        # Control with target_objects
        control = {
            "id": "SYS.1.1",
            "title": "Test Target",
            "props": [{"name": "alt-identifier", "value": "uuid-3"}],
            "parts": [{
                "name": "statement",
                "props": [{"name": "target_objects", "value": "Server"}]
            }]
        }
        keys, uuid, simplified = _process_control(control)
        self.assertIn("Server", keys)
        self.assertEqual(uuid, "uuid-3")

if __name__ == '__main__':
    unittest.main()
