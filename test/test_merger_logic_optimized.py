# -*- coding: utf-8 -*-
"""
Tests unitaires et benchmarks de performance pour MerginDataMerger.detect_conflicts.
Ne nécessite pas PyQGIS.
"""

import unittest
import time
from mergin_workflow_manager import MerginDataMerger


class TestMergerLogicOptimized(unittest.TestCase):

    def setUp(self):
        self.merger = MerginDataMerger(postgrest_client=None)

    def test_detect_conflicts_additions(self):
        original = [{'id': 1, 'val': 'a'}, {'id': 2, 'val': 'b'}]
        collected = [{'id': 1, 'val': 'a'}, {'id': 2, 'val': 'b'}, {'id': 3, 'val': 'c'}]

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')
        added = next(c for c in conflicts if c['type'] == 'added')
        self.assertEqual(added['count'], 1)
        self.assertIn(3, added['ids'])

    def test_detect_conflicts_deletions(self):
        original = [{'id': 1, 'val': 'a'}, {'id': 2, 'val': 'b'}]
        collected = [{'id': 1, 'val': 'a'}]

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')
        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        self.assertEqual(deleted['count'], 1)
        self.assertIn(2, deleted['ids'])

    def test_detect_conflicts_modifications(self):
        original = [{'id': 1, 'val': 'a'}, {'id': 2, 'val': 'b'}]
        collected = [{'id': 1, 'val': 'a'}, {'id': 2, 'val': 'modified_b'}]

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')
        modified = [c for c in conflicts if c['type'] == 'modified']
        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 2)
        self.assertEqual(modified[0]['collected']['val'], 'modified_b')

    def test_detect_conflicts_empty_datasets(self):
        conflicts = self.merger.detect_conflicts([], [], pk_field='id')
        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        added = next(c for c in conflicts if c['type'] == 'added')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(deleted['count'], 0)
        self.assertEqual(added['count'], 0)
        self.assertEqual(len(modified), 0)

    def test_detect_conflicts_none_primary_key(self):
        original = [{'id': None, 'val': 'invalid'}, {'id': 1, 'val': 'a'}]
        collected = [{'id': None, 'val': 'invalid'}, {'id': 1, 'val': 'a_updated'}]

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')
        modified = [c for c in conflicts if c['type'] == 'modified']
        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 1)

    def test_benchmark_detect_conflicts_performance(self):
        # Generate 2000 records to measure performance speedup
        num_records = 2000
        original = [{'id': i, 'val': f'value_{i}'} for i in range(num_records)]
        collected = [{'id': i, 'val': f'value_{i}' if i % 10 != 0 else f'mod_{i}'} for i in range(500, num_records + 500)]

        start_time = time.perf_counter()
        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')
        duration = time.perf_counter() - start_time

        # Ensure result is correct
        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        added = next(c for c in conflicts if c['type'] == 'added')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(deleted['count'], 500)
        self.assertEqual(added['count'], 500)
        self.assertGreater(len(modified), 0)

        # Performance assertion: 2000 items should complete in < 0.05 seconds with dictionary lookups
        self.assertLess(duration, 0.05, f"detect_conflicts took too long: {duration:.4f}s")
        print(f"\n[BENCHMARK] detect_conflicts for {num_records} items completed in {duration:.5f} seconds")


if __name__ == '__main__':
    unittest.main()
