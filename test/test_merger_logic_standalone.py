# -*- coding: utf-8 -*-
import unittest
import time
from mergin_workflow_manager import MerginDataMerger

class TestMerginDataMergerStandalone(unittest.TestCase):
    def setUp(self):
        self.merger = MerginDataMerger(postgrest_client=None)

    def test_detect_conflicts_correctness(self):
        original = [
            {'id': 1, 'name': 'Alpha'},
            {'id': 2, 'name': 'Beta'},
            {'id': 3, 'name': 'Gamma'},
            {'id': None, 'name': 'NullPKOriginal'}
        ]
        collected = [
            {'id': 1, 'name': 'Alpha'},            # Unchanged
            {'id': 2, 'name': 'Beta_Modified'},   # Modified
            {'id': 4, 'name': 'Delta'},           # Added
            {'id': None, 'name': 'NullPKCollected'}
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
        self.assertEqual(modified[0]['original']['name'], 'Beta')
        self.assertEqual(modified[0]['collected']['name'], 'Beta_Modified')

    def test_performance_benchmark(self):
        N = 3000
        original = [{'id': i, 'val': f'v_{i}'} for i in range(N)]
        collected = [{'id': i, 'val': f'v_{i}' if i % 10 != 0 else f'v_{i}_mod'} for i in range(N)]

        t0 = time.perf_counter()
        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')
        t1 = time.perf_counter()

        elapsed = t1 - t0
        print(f"\n[BENCHMARK] detect_conflicts for {N} items took {elapsed:.6f}s")
        self.assertLess(elapsed, 0.05, "detect_conflicts should execute in under 50ms for 3000 items")

if __name__ == '__main__':
    unittest.main()
