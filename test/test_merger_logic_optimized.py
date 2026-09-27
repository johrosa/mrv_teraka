# -*- coding: utf-8 -*-
"""
Tests and benchmarks for optimized MerginDataMerger logic.
Runs without QGIS dependencies.
"""

import time
import unittest
from mergin_workflow_manager import MerginDataMerger


class TestMergerLogicOptimized(unittest.TestCase):

    def setUp(self):
        self.merger = MerginDataMerger(postgrest_client=None)

    def test_detect_conflicts_correctness(self):
        original = [
            {'id': 1, 'name': 'Item 1', 'value': 100},
            {'id': 2, 'name': 'Item 2', 'value': 200},
            {'id': 3, 'name': 'Item 3', 'value': 300},
            {'id': None, 'name': 'Invalid', 'value': 0},
        ]
        collected = [
            {'id': 1, 'name': 'Item 1', 'value': 100},       # Unchanged
            {'id': 2, 'name': 'Item 2', 'value': 250},       # Modified
            {'id': 4, 'name': 'Item 4', 'value': 400},       # Added
            {'id': None, 'name': 'Invalid2', 'value': 0},
        ]

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')

        # Extract conflicts by type
        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        added = next(c for c in conflicts if c['type'] == 'added')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(deleted['count'], 1)
        self.assertEqual(deleted['ids'], [3])

        self.assertEqual(added['count'], 1)
        self.assertEqual(added['ids'], [4])

        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 2)
        self.assertEqual(modified[0]['original']['value'], 200)
        self.assertEqual(modified[0]['collected']['value'], 250)

    def test_detect_conflicts_performance_benchmark(self):
        n = 2000
        original = [{'id': i, 'val': f'val_{i}'} for i in range(n)]
        collected = [{'id': i, 'val': f'val_{i}' if i % 2 == 0 else f'updated_{i}'} for i in range(n // 2, n + n // 2)]

        start_time = time.perf_counter()
        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')
        elapsed = time.perf_counter() - start_time

        print(f"\n[BENCHMARK] MerginDataMerger.detect_conflicts for N={n}: {elapsed:.4f}s")
        self.assertLess(elapsed, 0.1, f"Expected detect_conflicts to complete in < 0.1s, took {elapsed:.4f}s")


if __name__ == '__main__':
    unittest.main()
