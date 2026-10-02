# -*- coding: utf-8 -*-
"""
Tests unitaires et benchmarks pour MerginDataMerger.detect_conflicts.
"""

import unittest
import time
from mergin_workflow_manager import MerginDataMerger


class TestMergerLogicOptimized(unittest.TestCase):

    def setUp(self):
        self.merger = MerginDataMerger(postgrest_client=None)

    def test_empty_datasets(self):
        conflicts = self.merger.detect_conflicts([], [])
        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        added = next(c for c in conflicts if c['type'] == 'added')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(deleted['count'], 0)
        self.assertEqual(added['count'], 0)
        self.assertEqual(len(modified), 0)

    def test_additions_deletions_modifications(self):
        orig = [
            {'id': 1, 'val': 'a'},
            {'id': 2, 'val': 'b'},
            {'id': 3, 'val': 'c'},
        ]
        coll = [
            {'id': 2, 'val': 'b_modified'},
            {'id': 3, 'val': 'c'},
            {'id': 4, 'val': 'd'},
        ]

        conflicts = self.merger.detect_conflicts(orig, coll, pk_field='id')

        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        added = next(c for c in conflicts if c['type'] == 'added')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(deleted['ids'], [1])
        self.assertEqual(added['ids'], [4])
        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 2)
        self.assertEqual(modified[0]['original'], {'id': 2, 'val': 'b'})
        self.assertEqual(modified[0]['collected'], {'id': 2, 'val': 'b_modified'})

    def test_missing_or_none_pk(self):
        orig = [{'id': None, 'val': 'x'}, {'id': 1, 'val': 'a'}]
        coll = [{'id': None, 'val': 'y'}, {'id': 1, 'val': 'a'}]

        conflicts = self.merger.detect_conflicts(orig, coll, pk_field='id')
        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        added = next(c for c in conflicts if c['type'] == 'added')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(deleted['count'], 0)
        self.assertEqual(added['count'], 0)
        self.assertEqual(len(modified), 0)

    def test_performance_large_dataset(self):
        N = 2000
        orig = [{'id': i, 'val': f'value_{i}'} for i in range(N)]
        coll = [{'id': i, 'val': f'value_{i}' if i % 2 == 0 else f'mod_{i}'} for i in range(N)]

        start = time.perf_counter()
        conflicts = self.merger.detect_conflicts(orig, coll, pk_field='id')
        elapsed = time.perf_counter() - start

        modified = [c for c in conflicts if c['type'] == 'modified']
        self.assertEqual(len(modified), N // 2)

        # Ensure performance target (< 0.05 seconds for 2000 items)
        print(f"\n[BENCHMARK] detect_conflicts for {N} records took: {elapsed:.5f}s")
        self.assertLess(elapsed, 0.05, f"detect_conflicts took too long: {elapsed:.5f}s")


if __name__ == '__main__':
    unittest.main()
