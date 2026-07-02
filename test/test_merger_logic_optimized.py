import unittest
from unittest.mock import Mock, call
import sys
import os

sys.path.append(os.getcwd())
from mergin_workflow_manager import MerginDataMerger

class TestMerginDataMergerOptimized(unittest.TestCase):
    def setUp(self):
        self.mock_postgrest = Mock()
        self.merger = MerginDataMerger(self.mock_postgrest)

    def test_detect_conflicts_optimized(self):
        original = [{'id': 1, 'val': 'a'}, {'id': 2, 'val': 'b'}]
        collected = [{'id': 1, 'val': 'a_mod'}, {'id': 3, 'val': 'c'}]

        conflicts = self.merger.detect_conflicts(original, collected)

        # Expect: 1 deleted (id 2), 1 added (id 3), 1 modified (id 1)
        conflict_types = [c['type'] for c in conflicts]
        self.assertIn('deleted', conflict_types)
        self.assertIn('added', conflict_types)
        self.assertIn('modified', conflict_types)

        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        self.assertEqual(deleted['ids'], [2])

        added = next(c for c in conflicts if c['type'] == 'added')
        self.assertEqual(added['ids'], [3])

        modified = next(c for c in conflicts if c['type'] == 'modified')
        self.assertEqual(modified['id'], 1)

    def test_merge_batch_operations(self):
        original = [{'id': 1, 'val': 'a'}, {'id': 2, 'val': 'b'}]
        collected = [{'id': 1, 'val': 'a_mod'}, {'id': 3, 'val': 'c'}]

        results = self.merger.merge('test_table', original, collected, strategy='merge')

        # Verify UPSERT call for id 1 (mod) and id 3 (add)
        self.mock_postgrest.insert.assert_called_once()
        args, kwargs = self.mock_postgrest.insert.call_args
        self.assertEqual(args[0], 'test_table')
        self.assertEqual(len(args[1]), 2) # id 1 and 3
        self.assertTrue(kwargs.get('upsert'))

        # Verify DELETE call for id 2
        self.mock_postgrest.delete.assert_called_once_with('test_table', {'id': 'in.(2)'})

if __name__ == '__main__':
    unittest.main()
