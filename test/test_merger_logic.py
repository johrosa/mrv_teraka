import unittest
from unittest.mock import MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from mergin_workflow_manager import MerginDataMerger

class TestMerginDataMerger(unittest.TestCase):
    def setUp(self):
        self.mock_postgrest = MagicMock()
        self.merger = MerginDataMerger(self.mock_postgrest)

    def test_detect_conflicts(self):
        original = [
            {'id': 1, 'name': 'A'},
            {'id': 2, 'name': 'B'},
            {'id': 3, 'name': 'C'}
        ]
        collected = [
            {'id': 1, 'name': 'A_mod'}, # Modified
            {'id': 3, 'name': 'C'},     # Unchanged
            {'id': 4, 'name': 'D'}      # Added
            # id 2 is Deleted
        ]

        conflicts = self.merger.detect_conflicts(original, collected)

        # Verify findings
        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        self.assertEqual(deleted['ids'], [2])

        added = next(c for c in conflicts if c['type'] == 'added')
        self.assertEqual(added['ids'], [4])

        modified = [c for c in conflicts if c['type'] == 'modified']
        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 1)
        self.assertEqual(modified[0]['collected']['name'], 'A_mod')

    def test_merge_batching(self):
        original = [{'id': 1, 'name': 'A'}, {'id': 2, 'name': 'B'}]
        collected = [{'id': 1, 'name': 'A_mod'}, {'id': 3, 'name': 'C'}] # 1 mod, 2 del, 3 add

        self.merger.merge('test_table', original, collected)

        # Verify PostgREST calls
        # 1. Batch UPSERT (added + modified)
        self.mock_postgrest.insert.assert_called_once()
        args, kwargs = self.mock_postgrest.insert.call_args
        self.assertEqual(args[0], 'test_table')
        self.assertEqual(len(args[1]), 2) # id 1 and id 3
        self.assertTrue(kwargs.get('upsert'))

        # 2. Batch DELETE (deleted)
        self.mock_postgrest.delete.assert_called_once()
        args, kwargs = self.mock_postgrest.delete.call_args
        self.assertEqual(args[0], 'test_table')
        self.assertEqual(args[1], {'id': 'in.(2)'})

if __name__ == '__main__':
    unittest.main()
