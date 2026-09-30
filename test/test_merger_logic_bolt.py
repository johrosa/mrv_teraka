# -*- coding: utf-8 -*-
"""
Standalone test and benchmark script for MerginDataMerger.detect_conflicts.
Does not require PyQGIS dependencies.
"""

import unittest
import time
from mergin_workflow_manager import MerginDataMerger


class TestMergerLogicBolt(unittest.TestCase):

    def setUp(self):
        self.merger = MerginDataMerger(postgrest_client=None)

    def test_detect_conflicts_correctness(self):
        original = [
            {'id': 1, 'name': 'A', 'val': 10},
            {'id': 2, 'name': 'B', 'val': 20},
            {'id': 3, 'name': 'C', 'val': 30},
            {'id': None, 'name': 'Invalid'},
        ]
        collected = [
            {'id': 1, 'name': 'A', 'val': 10},       # Unchanged
            {'id': 2, 'name': 'B', 'val': 25},       # Modified
            {'id': 4, 'name': 'D', 'val': 40},       # Added
            {'id': None, 'name': 'Invalid'},
        ]

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')

        # Deleted
        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        self.assertEqual(deleted['count'], 1)
        self.assertIn(3, deleted['ids'])

        # Added
        added = next(c for c in conflicts if c['type'] == 'added')
        self.assertEqual(added['count'], 1)
        self.assertIn(4, added['ids'])

        # Modified
        modified = [c for c in conflicts if c['type'] == 'modified']
        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 2)
        self.assertEqual(modified[0]['collected']['val'], 25)

    def test_benchmark_detect_conflicts(self):
        N = 2000
        original = [{'id': i, 'name': f'item_{i}', 'val': i} for i in range(N)]
        collected = [{'id': i, 'name': f'item_{i}', 'val': i + 1 if i % 2 == 0 else i} for i in range(N)]

        t0 = time.perf_counter()
        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')
        t1 = time.perf_counter()

        elapsed = t1 - t0
        print(f"\n[⚡ Bolt Benchmark] N={N} items processed in {elapsed:.5f} seconds")

        # Performance assertion: 2000 items should take well under 0.05 seconds with O(1) hash map lookup
        self.assertLess(elapsed, 0.05)
        self.assertEqual(len([c for c in conflicts if c['type'] == 'modified']), N // 2)


if __name__ == '__main__':
    unittest.main()
