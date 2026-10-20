# -*- coding: utf-8 -*-
import unittest
import time
from mergin_workflow_manager import MerginDataMerger


class TestMergerLogicOptimized(unittest.TestCase):
    """Unit tests for optimized MerginDataMerger conflict detection."""

    def setUp(self):
        self.merger = MerginDataMerger(None)

    def test_detect_conflicts_empty(self):
        conflicts = self.merger.detect_conflicts([], [])
        self.assertEqual(conflicts[0]['ids'], [])
        self.assertEqual(conflicts[1]['ids'], [])
        self.assertEqual(len(conflicts), 2)

    def test_detect_conflicts_add_delete_modify(self):
        original = [
            {'id': 1, 'name': 'Item 1'},
            {'id': 2, 'name': 'Item 2'},
            {'id': 3, 'name': 'Item 3'},
        ]
        collected = [
            {'id': 1, 'name': 'Item 1'},
            {'id': 2, 'name': 'Item 2 Modified'},
            {'id': 4, 'name': 'Item 4 New'},
        ]

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')

        # Deleted ID 3
        self.assertEqual(conflicts[0]['type'], 'deleted')
        self.assertEqual(conflicts[0]['ids'], [3])

        # Added ID 4
        self.assertEqual(conflicts[1]['type'], 'added')
        self.assertEqual(conflicts[1]['ids'], [4])

        # Modified ID 2
        self.assertEqual(len(conflicts), 3)
        self.assertEqual(conflicts[2]['type'], 'modified')
        self.assertEqual(conflicts[2]['id'], 2)
        self.assertEqual(conflicts[2]['original'], {'id': 2, 'name': 'Item 2'})
        self.assertEqual(conflicts[2]['collected'], {'id': 2, 'name': 'Item 2 Modified'})

    def test_detect_conflicts_with_none_pk(self):
        original = [{'id': None, 'name': 'Corrupted'}]
        collected = [{'id': None, 'name': 'New Unsaved'}]

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')
        self.assertEqual(conflicts[0]['ids'], [])
        self.assertEqual(conflicts[1]['ids'], [])

    def test_detect_conflicts_performance_benchmark(self):
        N = 2000
        original = [{'id': i, 'val': f'orig_{i}', 'status': 'active'} for i in range(N)]
        collected = [{'id': i, 'val': f'orig_{i}' if i % 2 == 0 else f'mod_{i}', 'status': 'active'} for i in range(N)]

        t0 = time.perf_counter()
        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')
        t1 = time.perf_counter()

        elapsed = t1 - t0
        print(f"\n[Benchmark] detect_conflicts for N={N} executed in {elapsed:.6f} seconds.")
        # O(N+M) complexity ensures 2000 items finish well within 0.1s (typically < 0.01s)
        self.assertLess(elapsed, 0.1)


if __name__ == '__main__':
    unittest.main()
