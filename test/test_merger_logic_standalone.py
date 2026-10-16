# -*- coding: utf-8 -*-
"""
Standalone unit tests and benchmarks for MerginDataMerger.detect_conflicts
Does not depend on PyQGIS.
"""

import unittest
import time
from mergin_workflow_manager import MerginDataMerger


class TestMergerLogicStandalone(unittest.TestCase):

    def setUp(self):
        self.merger = MerginDataMerger(postgrest_client=None)

    def test_empty_datasets(self):
        conflicts = self.merger.detect_conflicts([], [])
        self.assertEqual(conflicts[0], {'type': 'deleted', 'count': 0, 'ids': []})
        self.assertEqual(conflicts[1], {'type': 'added', 'count': 0, 'ids': []})

    def test_identical_datasets(self):
        data = [{'id': 1, 'name': 'A'}, {'id': 2, 'name': 'B'}]
        conflicts = self.merger.detect_conflicts(data, data)
        self.assertEqual(conflicts[0], {'type': 'deleted', 'count': 0, 'ids': []})
        self.assertEqual(conflicts[1], {'type': 'added', 'count': 0, 'ids': []})
        self.assertEqual(len(conflicts), 2)  # No modified entries

    def test_additions_deletions_modifications(self):
        original = [
            {'id': 1, 'name': 'KeptSame'},
            {'id': 2, 'name': 'ToModify'},
            {'id': 3, 'name': 'ToDelete'}
        ]
        collected = [
            {'id': 1, 'name': 'KeptSame'},
            {'id': 2, 'name': 'ModifiedValue'},
            {'id': 4, 'name': 'NewlyAdded'},
            {'id': None, 'name': 'NewNoId'}
        ]

        conflicts = self.merger.detect_conflicts(original, collected)

        # Deletions
        del_conflict = conflicts[0]
        self.assertEqual(del_conflict['type'], 'deleted')
        self.assertEqual(del_conflict['count'], 1)
        self.assertIn(3, del_conflict['ids'])

        # Additions
        add_conflict = conflicts[1]
        self.assertEqual(add_conflict['type'], 'added')
        self.assertEqual(add_conflict['count'], 2)
        self.assertIn(4, add_conflict['ids'])
        self.assertIn(None, add_conflict['ids'])

        # Modifications
        mod_conflicts = [c for c in conflicts if c.get('type') == 'modified']
        self.assertEqual(len(mod_conflicts), 1)
        self.assertEqual(mod_conflicts[0]['id'], 2)
        self.assertEqual(mod_conflicts[0]['original'], {'id': 2, 'name': 'ToModify'})
        self.assertEqual(mod_conflicts[0]['collected'], {'id': 2, 'name': 'ModifiedValue'})

    def test_benchmark_performance(self):
        n = 3000
        original = [{'id': i, 'val': f'orig_{i}'} for i in range(n)]
        collected = [{'id': i, 'val': f'orig_{i}' if i % 10 != 0 else f'mod_{i}'} for i in range(200, n + 100)]

        t0 = time.perf_counter()
        conflicts = self.merger.detect_conflicts(original, collected)
        t1 = time.perf_counter()

        elapsed = t1 - t0
        print(f"\n⚡ Benchmark detect_conflicts ({n} records): {elapsed:.5f}s")
        # Ensure it runs fast (under 0.05 seconds for 3000 records)
        self.assertLess(elapsed, 0.05)


if __name__ == '__main__':
    unittest.main()
