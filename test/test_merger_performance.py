# -*- coding: utf-8 -*-
"""
Unit tests and performance benchmarks for MerginDataMerger.detect_conflicts
"""

import unittest
import time
from mergin_workflow_manager import MerginDataMerger


class TestMerginDataMergerPerformance(unittest.TestCase):

    def setUp(self):
        self.merger = MerginDataMerger(postgrest_client=None)

    def test_detect_conflicts_correctness(self):
        """Verify that detect_conflicts correctly identifies added, deleted, and modified records."""
        original = [
            {'id': 1, 'name': 'Tree 1', 'val': 10},
            {'id': 2, 'name': 'Tree 2', 'val': 20},
            {'id': 3, 'name': 'Tree 3', 'val': 30},
        ]
        collected = [
            {'id': 2, 'name': 'Tree 2 Updated', 'val': 20},  # modified
            {'id': 3, 'name': 'Tree 3', 'val': 30},          # unchanged
            {'id': 4, 'name': 'Tree 4 New', 'val': 40},      # added
        ]
        # id=1 was deleted

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')

        # Check deleted
        deleted_conflict = next(c for c in conflicts if c['type'] == 'deleted')
        self.assertEqual(deleted_conflict['count'], 1)
        self.assertIn(1, deleted_conflict['ids'])

        # Check added
        added_conflict = next(c for c in conflicts if c['type'] == 'added')
        self.assertEqual(added_conflict['count'], 1)
        self.assertIn(4, added_conflict['ids'])

        # Check modified
        modified_conflicts = [c for c in conflicts if c['type'] == 'modified']
        self.assertEqual(len(modified_conflicts), 1)
        self.assertEqual(modified_conflicts[0]['id'], 2)
        self.assertEqual(modified_conflicts[0]['original']['name'], 'Tree 2')
        self.assertEqual(modified_conflicts[0]['collected']['name'], 'Tree 2 Updated')

    def test_detect_conflicts_handles_empty_and_none(self):
        """Verify that detect_conflicts safely handles empty lists and None primary keys."""
        original = [{'id': None, 'name': 'Invalid'}]
        collected = []
        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')

        deleted_conflict = next(c for c in conflicts if c['type'] == 'deleted')
        self.assertEqual(deleted_conflict['count'], 0)

    def test_detect_conflicts_benchmark(self):
        """Benchmark detect_conflicts execution time on 2000 items."""
        N = 2000
        original = [{'id': i, 'val': f'val_{i}', 'status': 'ok'} for i in range(N)]
        collected = [
            {'id': i, 'val': f'val_{i}' if i % 2 == 0 else f'modified_{i}', 'status': 'ok'}
            for i in range(N)
        ]

        t0 = time.perf_counter()
        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')
        duration = time.perf_counter() - t0

        # Should complete in less than 0.05 seconds for 2000 items with O(N+M)
        self.assertLess(duration, 0.05, f"Execution took {duration:.4f}s, expected < 0.05s")
        print(f"\n⚡ Benchmark: detect_conflicts completed in {duration * 1000:.2f}ms for N={N}")


if __name__ == '__main__':
    unittest.main()
