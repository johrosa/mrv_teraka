# -*- coding: utf-8 -*-
import unittest
import time
from mergin_workflow_manager import MerginDataMerger


class TestMerginDataMergerStandalone(unittest.TestCase):
    def setUp(self):
        self.merger = MerginDataMerger(postgrest_client=None)

    def test_detect_conflicts_basic(self):
        original = [
            {'id': 1, 'name': 'Alpha', 'val': 100},
            {'id': 2, 'name': 'Beta', 'val': 200},
            {'id': 3, 'name': 'Gamma', 'val': 300},
        ]
        collected = [
            {'id': 1, 'name': 'Alpha', 'val': 100},          # Unchanged
            {'id': 2, 'name': 'Beta', 'val': 250},          # Modified
            {'id': 4, 'name': 'Delta', 'val': 400},         # Added (3 deleted)
        ]

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')

        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        added = next(c for c in conflicts if c['type'] == 'added')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(deleted['ids'], [3])
        self.assertEqual(added['ids'], [4])
        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 2)
        self.assertEqual(modified[0]['original']['val'], 200)
        self.assertEqual(modified[0]['collected']['val'], 250)

    def test_detect_conflicts_custom_pk(self):
        original = [
            {'code': 'A1', 'status': 'active'},
            {'code': 'A2', 'status': 'pending'},
        ]
        collected = [
            {'code': 'A1', 'status': 'closed'},
            {'code': 'A2', 'status': 'pending'},
        ]

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='code')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 'A1')

    def test_detect_conflicts_none_pk_handling(self):
        original = [{'id': None, 'val': 1}, {'id': 1, 'val': 2}]
        collected = [{'id': None, 'val': 1}, {'id': 1, 'val': 3}]

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 1)

    def test_detect_conflicts_performance_benchmark(self):
        N = 2000
        original = [{'id': i, 'val': f'value_{i}'} for i in range(N)]
        collected = [{'id': i, 'val': f'value_{i}' if i % 2 == 0 else f'value_{i}_mod'} for i in range(N)]

        t0 = time.perf_counter()
        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')
        t1 = time.perf_counter()

        elapsed = t1 - t0
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(len(modified), 1000)
        # Verify execution is extremely fast (< 50ms for 2000 items)
        self.assertLess(elapsed, 0.05, f"Expected < 0.05s, got {elapsed:.4f}s")


if __name__ == '__main__':
    unittest.main()
