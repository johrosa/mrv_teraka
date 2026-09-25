# -*- coding: utf-8 -*-
import unittest
import time
from mergin_workflow_manager import MerginDataMerger


class TestMerginDataMergerOptimized(unittest.TestCase):

    def setUp(self):
        self.merger = MerginDataMerger(postgrest_client=None)

    def test_detect_conflicts_correctness(self):
        original = [
            {'id': 1, 'name': 'Alpha'},
            {'id': 2, 'name': 'Beta'},
            {'id': 3, 'name': 'Gamma'},
            {'id': None, 'name': 'Invalid'}
        ]
        collected = [
            {'id': 1, 'name': 'Alpha'},           # Unchanged
            {'id': 2, 'name': 'Beta Modified'},  # Modified
            {'id': 4, 'name': 'Delta'},          # Added
            {'id': None, 'name': 'Invalid2'}
        ]

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')

        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        added = next(c for c in conflicts if c['type'] == 'added')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(deleted['ids'], [3])
        self.assertEqual(added['ids'], [4])
        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 2)
        self.assertEqual(modified[0]['collected']['name'], 'Beta Modified')

    def test_detect_conflicts_benchmark(self):
        N = 2000
        original = [{'id': i, 'val': f'orig_{i}'} for i in range(N)]
        collected = [{'id': i, 'val': f'coll_{i}' if i % 2 == 0 else f'orig_{i}'} for i in range(N)]

        start = time.perf_counter()
        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')
        elapsed = time.perf_counter() - start

        print(f"\n[Benchmark] detect_conflicts for {N} items took {elapsed:.6f}s")
        self.assertLess(elapsed, 0.1, "Conflict detection took too long!")


if __name__ == '__main__':
    unittest.main()
