# -*- coding: utf-8 -*-
"""
Tests unitaires et de performance pour MerginDataMerger (Optimisé).
"""

import unittest
import time
from mergin_workflow_manager import MerginDataMerger


class MockPostgRESTClient:
    pass


class TestMergerLogicOptimized(unittest.TestCase):

    def setUp(self):
        self.merger = MerginDataMerger(MockPostgRESTClient())

    def test_detect_conflicts_correctness(self):
        original = [
            {'id': 1, 'name': 'Alpha', 'value': 10},
            {'id': 2, 'name': 'Beta', 'value': 20},
            {'id': 3, 'name': 'Gamma', 'value': 30},
            {'id': None, 'name': 'Invalid'},
        ]
        collected = [
            {'id': 1, 'name': 'Alpha', 'value': 10},        # Unchanged
            {'id': 2, 'name': 'Beta', 'value': 25},         # Modified
            {'id': 4, 'name': 'Delta', 'value': 40},        # Added
            {'id': None, 'name': 'Invalid'},
        ]

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')

        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        added = next(c for c in conflicts if c['type'] == 'added')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(deleted['ids'], [3])
        self.assertEqual(added['ids'], [4])
        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 2)
        self.assertEqual(modified[0]['original']['value'], 20)
        self.assertEqual(modified[0]['collected']['value'], 25)

    def test_detect_conflicts_performance(self):
        N = 2000
        original = [{'id': i, 'val': f'v_{i}', 'status': 'ok'} for i in range(N)]
        collected = [{'id': i, 'val': f'v_{i}' if i % 2 == 0 else f'v_{i}_mod', 'status': 'ok'} for i in range(N)]

        t0 = time.perf_counter()
        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')
        t1 = time.perf_counter()

        elapsed = t1 - t0
        print(f"\n[Performance] detect_conflicts for {N} items: {elapsed:.6f} seconds")

        # Performance assertion: must complete in < 0.05 seconds (baseline was ~0.107s)
        self.assertLess(elapsed, 0.05)


if __name__ == '__main__':
    unittest.main()
