# -*- coding: utf-8 -*-
import unittest
import time
from unittest.mock import MagicMock
from mergin_workflow_manager import MerginDataMerger


class TestMerginDataMergerOptimized(unittest.TestCase):
    def setUp(self):
        self.mock_postgrest = MagicMock()
        self.merger = MerginDataMerger(self.mock_postgrest)

    def test_detect_conflicts_correctness(self):
        original = [
            {'id': 1, 'name': 'Item 1', 'value': 100},
            {'id': 2, 'name': 'Item 2', 'value': 200},
            {'id': 3, 'name': 'Item 3', 'value': 300},
            {'id': None, 'name': 'Invalid'}
        ]
        collected = [
            {'id': 1, 'name': 'Item 1', 'value': 100},          # Unchanged
            {'id': 2, 'name': 'Item 2 Modified', 'value': 250}, # Modified
            {'id': 4, 'name': 'Item 4 New', 'value': 400},      # Added
            {'id': None, 'name': 'Invalid New'}
        ]
        # Item 3 is deleted

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')

        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        added = next(c for c in conflicts if c['type'] == 'added')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(deleted['count'], 1)
        self.assertEqual(deleted['ids'], [3])

        self.assertEqual(added['count'], 1)
        self.assertEqual(added['ids'], [4])

        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 2)
        self.assertEqual(modified[0]['collected']['name'], 'Item 2 Modified')

    def test_detect_conflicts_performance(self):
        n = 2000
        original = [{'id': i, 'val': f'val_{i}'} for i in range(n)]
        collected = [{'id': i, 'val': f'val_{i}' if i % 10 != 0 else f'mod_{i}'} for i in range(n)]

        t0 = time.perf_counter()
        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')
        t1 = time.perf_counter()

        elapsed = t1 - t0
        # O(N) lookup should process 2000 items in well under 0.05 seconds
        self.assertLess(elapsed, 0.05)

        modified_count = len([c for c in conflicts if c['type'] == 'modified'])
        self.assertEqual(modified_count, n // 10)


if __name__ == '__main__':
    unittest.main()
