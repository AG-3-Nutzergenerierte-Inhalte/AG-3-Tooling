
import unittest
from pipeline.stage_component import chunk_controls

class TestChunkControls(unittest.TestCase):

    def test_basic_grouping_and_chunking(self):
        """Test that controls are grouped by prefix and chunked correctly."""
        # Setup: 2 groups. Group 'A' has 60 items (should split into 50 + 10). Group 'B' has 5 items.
        ids = [f"A.{i}" for i in range(60)] + [f"B.{i}" for i in range(5)]

        chunks = chunk_controls(ids, max_chunk_size=50)

        # Expect 3 chunks: A_part1 (50), A_part2 (10), B (5)
        self.assertEqual(len(chunks), 3)

        # Verify A split
        self.assertEqual(len(chunks[0]), 50)
        self.assertTrue(all(cid.startswith("A.") for cid in chunks[0]))

        self.assertEqual(len(chunks[1]), 10)
        self.assertTrue(all(cid.startswith("A.") for cid in chunks[1]))

        # Verify B
        self.assertEqual(len(chunks[2]), 5)
        self.assertTrue(all(cid.startswith("B.") for cid in chunks[2]))

    def test_exact_limit(self):
        """Test that a group exactly equal to max_chunk_size is one chunk."""
        ids = [f"A.{i}" for i in range(50)]
        chunks = chunk_controls(ids, max_chunk_size=50)

        self.assertEqual(len(chunks), 1)
        self.assertEqual(len(chunks[0]), 50)

    def test_mixed_prefixes_sorting(self):
        """Test that output is sorted by prefix."""
        ids = ["Z.1", "A.1", "C.1"]
        chunks = chunk_controls(ids, max_chunk_size=50)

        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0], ["A.1"])
        self.assertEqual(chunks[1], ["C.1"])
        self.assertEqual(chunks[2], ["Z.1"])

    def test_weird_ids(self):
        """Test IDs without dots."""
        ids = ["SIMPLE", "COMPLEX.1"]
        chunks = chunk_controls(ids, max_chunk_size=50)

        # Should be 2 chunks, sorted C then S
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0], ["COMPLEX.1"])
        self.assertEqual(chunks[1], ["SIMPLE"])

if __name__ == '__main__':
    unittest.main()
