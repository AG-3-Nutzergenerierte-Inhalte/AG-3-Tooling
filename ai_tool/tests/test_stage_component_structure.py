import unittest
import uuid
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from pipeline.stage_component import build_oscal_control

class TestStageComponentStructure(unittest.TestCase):
    def test_build_oscal_control_structure(self):
        # Mock generated data from AI
        generated_data = {
            "id": "APP.4.3.A1",
            "class": "Technical",
            "phase": "Implementation",
            "effective_on_c": "low",
            "effective_on_i": "high",
            "effective_on_a": "medium",
            "practice": "Practice description...",
            "level": "3",
            "level_1_statement": "L1 Statement",
            "level_1_guidance": "L1 Guidance",
            "level_1_assessment": "L1 Assessment",
        }

        control_id = "APP.4.3.A1"
        title = "Test Control"

        result = build_oscal_control(control_id, title, generated_data)

        # Verify props
        props = result.get("props", [])
        prop_map = {p["name"]: p["value"] for p in props}

        # Check if 'level' is present (it might fail if code doesn't support it yet)
        # We expect it to be there based on user requirements
        self.assertIn("level", prop_map, "Prop 'level' missing")
        self.assertEqual(prop_map["level"], "3")
        self.assertIn("phase", prop_map)
        self.assertIn("practice", prop_map)
        self.assertIn("effective_on_c", prop_map)

        # Verify statements (Maturity Levels)
        statements = result.get("statements", [])
        self.assertTrue(len(statements) > 0, "Should have statements")

        stmt = statements[0]
        # Check for JSON structure compliance
        self.assertIn("statement-id", stmt, "Should use statement-id")
        self.assertIn("uuid", stmt)
        self.assertIn("description", stmt)
        self.assertIn("props", stmt, "Statement should have props")

        # Check props inside statement
        stmt_props = {p["name"]: p["value"] for p in stmt["props"]}
        self.assertIn("statement", stmt_props)
        self.assertEqual(stmt_props["statement"], "L1 Statement")
        self.assertIn("guidance", stmt_props)
        self.assertIn("assessment-method", stmt_props)
