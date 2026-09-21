# -*- coding: utf-8 -*-
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
        ]
        collected = [
            {'id': 1, 'name': 'A', 'val': 10},  # Unchanged
            {'id': 2, 'name': 'B', 'val': 25},  # Modified
            {'id': 4, 'name': 'D', 'val': 40},  # Added
        ]
        # Item id=3 was deleted

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')

        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        added = next(c for c in conflicts if c['type'] == 'added')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(deleted['ids'], [3])
        self.assertEqual(added['ids'], [4])
        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 2)
        self.assertEqual(modified[0]['collected']['val'], 25)

    def test_detect_conflicts_benchmark(self):
        n = 2000
        original = [{'id': i, 'name': f'item_{i}', 'val': i * 2} for i in range(n)]
        collected = [{'id': i, 'name': f'item_{i}', 'val': i * 2 + (1 if i % 10 == 0 else 0)} for i in range(n)]

        t0 = time.perf_counter()
        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')
        t1 = time.perf_counter()

        elapsed = t1 - t0
        print(f"\n[Bolt ⚡ Benchmark] detect_conflicts for {n} items completed in {elapsed:.6f} seconds.")
        # O(N+M) dictionary lookup should complete well under 0.05 seconds for 2000 items
        self.assertLess(elapsed, 0.05)

if __name__ == '__main__':
    unittest.main()
