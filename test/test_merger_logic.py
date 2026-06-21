# -*- coding: utf-8 -*-
import unittest
from unittest.mock import MagicMock, call
from mergin_workflow_manager import MerginDataMerger

class TestMergerLogic(unittest.TestCase):
    def setUp(self):
        self.mock_postgrest = MagicMock()
        self.merger = MerginDataMerger(self.mock_postgrest)

    def test_detect_conflicts_accuracy(self):
        # Case: 1 unchanged, 1 modified, 1 deleted, 1 added
        original = [
            {'id': 1, 'val': 'A'}, # Unchanged
            {'id': 2, 'val': 'B'}, # Modified
            {'id': 3, 'val': 'C'}, # Deleted
        ]
        collected = [
            {'id': 1, 'val': 'A'}, # Unchanged
            {'id': 2, 'val': 'B_mod'}, # Modified
            {'id': 4, 'val': 'D'}, # Added
        ]

        conflicts = self.merger.detect_conflicts(original, collected)

        # Check counts
        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        added = next(c for c in conflicts if c['type'] == 'added')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(deleted['count'], 1)
        self.assertEqual(deleted['ids'], [3])
        self.assertEqual(added['count'], 1)
        self.assertEqual(added['ids'], [4])
        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 2)

    def test_merge_batch_calls(self):
        original = [
            {'id': 1, 'val': 'A'},
            {'id': 2, 'val': 'B'},
            {'id': 3, 'val': 'C'},
        ]
        collected = [
            {'id': 1, 'val': 'A'}, # Unchanged
            {'id': 2, 'val': 'B_mod'}, # Modified
            {'id': 4, 'val': 'D'}, # Added
        ]

        results = self.merger.merge('test_table', original, collected)

        # Verify UPSERT call (Mod 2 + Add 4)
        self.mock_postgrest.insert.assert_called_once()
        args, kwargs = self.mock_postgrest.insert.call_args
        self.assertEqual(args[0], 'test_table')
        self.assertEqual(len(args[1]), 2)
        self.assertTrue(kwargs.get('upsert'))

        # Verify DELETE call (ID 3)
        self.mock_postgrest.delete.assert_called_once_with('test_table', {'id': 'in.(3)'})

        # Verify result actions
        actions = results['actions']
        self.assertTrue(any(a['type'] == 'inserted' and a['id'] == 4 for a in actions))
        self.assertTrue(any(a['type'] == 'updated' and a['id'] == 2 for a in actions))
        self.assertTrue(any(a['type'] == 'deleted' and a['id'] == 3 for a in actions))

if __name__ == '__main__':
    unittest.main()
