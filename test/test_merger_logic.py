# -*- coding: utf-8 -*-
import unittest
from mergin_workflow_manager import MerginDataMerger

class MockPostgREST:
    def __init__(self):
        self.upserts = []
        self.deletes = []
    def insert(self, table, data, upsert=False):
        if upsert:
            self.upserts.append((table, data))
    def delete(self, table, filters):
        self.deletes.append((table, filters))

class TestMergerLogic(unittest.TestCase):
    def setUp(self):
        self.client = MockPostgREST()
        self.merger = MerginDataMerger(self.client)

    def test_detect_conflicts(self):
        original = [
            {'id': 1, 'v': 'a'},
            {'id': 2, 'v': 'b'},
            {'id': 3, 'v': 'c'}
        ]
        collected = [
            {'id': 1, 'v': 'a_mod'}, # Modified
            {'id': 2, 'v': 'b'},     # Unchanged
            {'id': 4, 'v': 'new'}      # Added
            # id 3 is deleted
        ]
        conflicts = self.merger.detect_conflicts(original, collected)

        types = [c['type'] for c in conflicts]
        self.assertIn('deleted', types)
        self.assertIn('added', types)
        self.assertIn('modified', types)

        mod = next(c for c in conflicts if c['type'] == 'modified')
        self.assertEqual(mod['id'], 1)

        dele = next(c for c in conflicts if c['type'] == 'deleted')
        self.assertEqual(dele['ids'], [3])

        added = next(c for c in conflicts if c['type'] == 'added')
        self.assertEqual(added['ids'], [4])

    def test_merge_strategy_merge(self):
        original = [{'id': 1, 'v': 'a'}, {'id': 2, 'v': 'b'}]
        collected = [{'id': 1, 'v': 'a_mod'}, {'id': 3, 'v': 'new'}]

        self.merger.merge('table', original, collected, strategy='merge')

        # Batch UPSERT check (id 1 and 3)
        self.assertEqual(len(self.client.upserts), 1)
        self.assertEqual(len(self.client.upserts[0][1]), 2)

        # Batch DELETE check (id 2)
        self.assertEqual(len(self.client.deletes), 1)
        self.assertEqual(self.client.deletes[0][1], {'id': 'in.(2)'})

if __name__ == '__main__':
    unittest.main()
