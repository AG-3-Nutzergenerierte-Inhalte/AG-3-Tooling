import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os
import json
import logging
import asyncio

# Set necessary environment variables for testing
os.environ["TEST"] = "true"

# Adjust sys.path to include src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pipeline import stage_component
from clients.ai_client import AiClient
from constants import GROUND_TRUTH_MODEL_PRO

class TestStageComponentEnhanced(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Configure logging to suppress output during tests
        logging.getLogger('pipeline.stage_component').setLevel(logging.CRITICAL)

    @patch('pipeline.stage_component.read_json_file')
    @patch('pipeline.stage_component.write_json_file')
    @patch('pipeline.stage_component.validate_oscal')
    @patch('pipeline.stage_component.read_csv_file')
    @patch('os.path.exists')
    async def test_generate_detailed_component_enhanced(self, mock_exists, mock_read_csv, mock_validate_oscal, mock_write_json, mock_read_json):
        # Mock file existence
        mock_exists.return_value = True

        # Mock Data Setup
        baustein_id = "APP.1"
        baustein_title = "Web Applications"
        zielobjekt_name = "Webserver"
        profile_path = "mock/profile/path.json"

        # Mock BSI Catalog (Baustein Source)
        mock_bsi_catalog = {
            "catalog": {
                "groups": [{
                    "groups": [{
                        "id": "APP.1",
                        "title": "Web Applications",
                        "parts": [
                            {"title": "Introduction", "prose": "Intro text..."},
                            {"title": "Risks", "prose": "Risk text..."}
                        ],
                        "controls": []
                    }]
                }]
            }
        }

        # Mock G++ Catalog (Control Source)
        mock_gpp_catalog = {
            "catalog": {
                "groups": [{
                    "controls": [
                        {
                            "id": "GPP.APP.1.1",
                            "title": "Control 1",
                            "parts": [
                                {"name": "prose", "prose": "Do this."},
                                {"name": "guidance", "prose": "How to do this."}
                            ]
                        },
                        {
                            "id": "GPP.APP.1.2",
                            "title": "Control 2",
                            "parts": [
                                {"name": "prose", "prose": "Do that."},
                            ]
                        }
                    ]
                }]
            }
        }

        # Mock Profile
        mock_profile = {
            "profile": {
                "imports": [{
                    "include-controls": [{
                        "with-ids": ["GPP.APP.1.1", "GPP.APP.1.2"]
                    }]
                }]
            }
        }

        def read_json_side_effect(path):
            if path == profile_path:
                return mock_profile
            return {}

        mock_read_json.side_effect = read_json_side_effect

        # Mock AI Client
        mock_ai_client = MagicMock(spec=AiClient)

        # Mock AI Response
        mock_ai_response = [
            {
                "id": "GPP.APP.1.1",
                "class": "Technical",
                "phase": "Implementation",
                "effective_on_c": "high",
                "effective_on_i": "medium",
                "effective_on_a": "low",
                "level_1_statement": "L1 Statement 1", "level_1_guidance": "L1 Guidance 1", "level_1_assessment": "L1 Assess 1",
                "level_2_statement": "L2 Statement 1", "level_2_guidance": "L2 Guidance 1", "level_2_assessment": "L2 Assess 1",
                "level_3_statement": "L3 Statement 1", "level_3_guidance": "L3 Guidance 1", "level_3_assessment": "L3 Assess 1",
                "level_4_statement": "L4 Statement 1", "level_4_guidance": "L4 Guidance 1", "level_4_assessment": "L4 Assess 1",
                "level_5_statement": "L5 Statement 1", "level_5_guidance": "L5 Guidance 1", "level_5_assessment": "L5 Assess 1"
            },
            {
                "id": "GPP.APP.1.2",
                "class": "Operational",
                "phase": "Operation",
                "effective_on_c": "low",
                "effective_on_i": "low",
                "effective_on_a": "high",
                "level_1_statement": "L1 Statement 2", "level_1_guidance": "L1 Guidance 2", "level_1_assessment": "L1 Assess 2",
                "level_2_statement": "L2 Statement 2", "level_2_guidance": "L2 Guidance 2", "level_2_assessment": "L2 Assess 2",
                "level_3_statement": "L3 Statement 2", "level_3_guidance": "L3 Guidance 2", "level_3_assessment": "L3 Assess 2",
                "level_4_statement": "L4 Statement 2", "level_4_guidance": "L4 Guidance 2", "level_4_assessment": "L4 Assess 2",
                "level_5_statement": "L5 Statement 2", "level_5_guidance": "L5 Guidance 2", "level_5_assessment": "L5 Assess 2"
            }
        ]

        # Correctly mock the async method
        mock_ai_client.generate_validated_json_response = AsyncMock(return_value=mock_ai_response)

        # Execute
        mapping = {}
        await stage_component.generate_detailed_component(
            baustein_id, baustein_title, zielobjekt_name, profile_path, mapping, mock_bsi_catalog, mock_gpp_catalog, "output_dir", mock_ai_client
        )

        # Verification
        mock_ai_client.generate_validated_json_response.assert_called_once()
        call_args = mock_ai_client.generate_validated_json_response.call_args
        prompt_input = call_args[1]['prompt']

        # Verify that model_override is passed correctly
        self.assertEqual(call_args[1].get('model_override'), GROUND_TRUTH_MODEL_PRO)

        self.assertIn("Intro text...", prompt_input)
        self.assertIn("GPP.APP.1.1", prompt_input)

        mock_write_json.assert_called_once()
        written_data = mock_write_json.call_args[0][1]

        components = written_data["component-definition"]["components"]
        self.assertEqual(len(components), 1)
        component = components[0]

        impl_reqs = component["control-implementations"][0]["implemented-requirements"]
        self.assertEqual(len(impl_reqs), 2)

        req1 = next(r for r in impl_reqs if r["control-id"] == "GPP.APP.1.1")
        self.assertEqual(len(req1["statements"]), 5)

if __name__ == '__main__':
    unittest.main()
