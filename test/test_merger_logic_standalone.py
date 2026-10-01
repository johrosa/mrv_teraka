# -*- coding: utf-8 -*-
"""
Standalone unit tests and performance benchmark for MerginDataMerger logic.
Does not require PyQGIS or external dependencies.
"""

import time
import unittest
from mergin_workflow_manager import MerginDataMerger


class TestMerginDataMergerStandalone(unittest.TestCase):

    def setUp(self):
        self.merger = MerginDataMerger(postgrest_client=None)

    def test_empty_datasets(self):
        conflicts = self.merger.detect_conflicts([], [], pk_field='id')
        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        added = next(c for c in conflicts if c['type'] == 'added')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(deleted['count'], 0)
        self.assertEqual(added['count'], 0)
        self.assertEqual(len(modified), 0)

    def test_unchanged_dataset(self):
        original = [{'id': 1, 'val': 'A'}, {'id': 2, 'val': 'B'}]
        collected = [{'id': 1, 'val': 'A'}, {'id': 2, 'val': 'B'}]
        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')

        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        added = next(c for c in conflicts if c['type'] == 'added')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(deleted['count'], 0)
        self.assertEqual(added['count'], 0)
        self.assertEqual(len(modified), 0)

    def test_additions_deletions_modifications(self):
        original = [
            {'id': 1, 'val': 'A'},
            {'id': 2, 'val': 'B'},
            {'id': 3, 'val': 'C'}
        ]
        collected = [
            {'id': 1, 'val': 'A'},          # Unchanged
            {'id': 2, 'val': 'B_modified'}, # Modified
            {'id': 4, 'val': 'D'}           # Added (3 deleted)
        ]

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')

        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        added = next(c for c in conflicts if c['type'] == 'added')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(deleted['count'], 1)
        self.assertIn(3, deleted['ids'])

        self.assertEqual(added['count'], 1)
        self.assertIn(4, added['ids'])

        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 2)
        self.assertEqual(modified[0]['original']['val'], 'B')
        self.assertEqual(modified[0]['collected']['val'], 'B_modified')

    def test_none_pk_handling(self):
        original = [{'id': None, 'val': 'X'}, {'id': 1, 'val': 'Y'}]
        collected = [{'id': None, 'val': 'X'}, {'id': 1, 'val': 'Y'}]

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')
        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        added = next(c for c in conflicts if c['type'] == 'added')

        self.assertNotIn(None, deleted['ids'])
        self.assertNotIn(None, added['ids'])

    def test_performance_benchmark(self):
        num_items = 2000
        original = [{'id': i, 'val': f'value_{i}'} for i in range(num_items)]
        collected = [{'id': i, 'val': f'value_{i}' if i % 2 == 0 else f'value_{i}_mod'} for i in range(num_items)]

        start = time.perf_counter()
        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')
        elapsed = time.perf_counter() - start

        modified = [c for c in conflicts if c['type'] == 'modified']
        self.assertEqual(len(modified), 1000)

        # Ensure performance target: 2000 items processed in < 20ms
        self.assertLess(elapsed, 0.02, f"Expected < 0.02s, took {elapsed:.6f}s")
        print(f"\n[BENCHMARK] detect_conflicts for {num_items} items took {elapsed:.6f}s")


if __name__ == '__main__':
    unittest.main()
