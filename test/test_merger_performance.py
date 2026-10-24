# -*- coding: utf-8 -*-
import time
import unittest
from mergin_workflow_manager import MerginDataMerger

class TestMergerPerformanceAndCorrectness(unittest.TestCase):
    def setUp(self):
        self.merger = MerginDataMerger(postgrest_client=None)

    def test_conflict_detection_correctness(self):
        original = [
            {'id': 1, 'name': 'Alpha', 'val': 100},
            {'id': 2, 'name': 'Beta', 'val': 200},
            {'id': 3, 'name': 'Gamma', 'val': 300},
        ]
        collected = [
            {'id': 2, 'name': 'Beta Updated', 'val': 200},  # Modified
            {'id': 3, 'name': 'Gamma', 'val': 300},          # Unchanged
            {'id': 4, 'name': 'Delta', 'val': 400},          # Added
        ]  # id 1 deleted

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')

        conflict_dict = {c['type']: c for c in conflicts}

        self.assertEqual(conflict_dict['deleted']['ids'], [1])
        self.assertEqual(conflict_dict['added']['ids'], [4])

        modified = [c for c in conflicts if c['type'] == 'modified']
        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 2)
        self.assertEqual(modified[0]['original']['name'], 'Beta')
        self.assertEqual(modified[0]['collected']['name'], 'Beta Updated')

    def test_performance_benchmark(self):
        num_items = 2000
        original = [{'id': i, 'val': f'value_{i}'} for i in range(num_items)]
        collected = [
            {'id': i, 'val': f'value_{i}' if i % 2 == 0 else f'modified_{i}'}
            for i in range(num_items // 2, num_items + num_items // 2)
        ]

        start = time.perf_counter()
        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')
        elapsed = time.perf_counter() - start

        print(f"\n[BENCHMARK] detect_conflicts for {num_items} items took: {elapsed:.6f} seconds")
        self.assertLess(elapsed, 0.05, "detect_conflicts should complete in less than 50ms for 2000 items")

if __name__ == '__main__':
    unittest.main()
