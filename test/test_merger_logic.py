
import unittest
from unittest.mock import MagicMock
import sys
import os

# Add current directory to sys.path to import local modules
sys.path.append(os.getcwd())

from mergin_workflow_manager import MerginDataMerger

class TestMergerLogic(unittest.TestCase):
    def setUp(self):
        self.mock_postgrest = MagicMock()
        self.merger = MerginDataMerger(self.mock_postgrest)
        self.pk_field = 'id'

    def test_detect_conflicts_added(self):
        original = [{'id': 1, 'v': 'a'}]
        collected = [{'id': 1, 'v': 'a'}, {'id': 2, 'v': 'b'}]
        conflicts = self.merger.detect_conflicts(original, collected, self.pk_field)

        added = [c for c in conflicts if c['type'] == 'added']
        self.assertEqual(len(added), 1)
        self.assertEqual(added[0]['ids'], [2])

    def test_detect_conflicts_modified(self):
        original = [{'id': 1, 'v': 'a'}]
        collected = [{'id': 1, 'v': 'modified'}]
        conflicts = self.merger.detect_conflicts(original, collected, self.pk_field)

        modified = [c for c in conflicts if c['type'] == 'modified']
        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 1)

    def test_detect_conflicts_deleted(self):
        original = [{'id': 1, 'v': 'a'}, {'id': 2, 'v': 'b'}]
        collected = [{'id': 1, 'v': 'a'}]
        conflicts = self.merger.detect_conflicts(original, collected, self.pk_field)

        deleted = [c for c in conflicts if c['type'] == 'deleted']
        self.assertEqual(len(deleted), 1)
        self.assertEqual(deleted[0]['ids'], [2])

    def test_merge_batching(self):
        original = [{'id': 1, 'v': 'orig'}]
        collected = [
            {'id': 1, 'v': 'mod'}, # modified
            {'id': 2, 'v': 'new'}  # added
        ]
        # deleted: none

        self.merger.merge("table", original, collected, strategy='merge', pk_field='id')

        # Verify insert was called once with both records (UPSERT)
        self.mock_postgrest.insert.assert_called_once()
        args, kwargs = self.mock_postgrest.insert.call_args
        self.assertEqual(args[0], "table")
        self.assertEqual(len(args[1]), 2)
        self.assertTrue(kwargs.get('upsert'))

    def test_merge_delete_batching(self):
        original = [{'id': 1, 'v': 'a'}, {'id': 2, 'v': 'b'}]
        collected = [] # Both deleted

        self.merger.merge("table", original, collected, strategy='merge', pk_field='id')

        # Verify delete was called once with IN clause
        self.mock_postgrest.delete.assert_called_once()
        args, kwargs = self.mock_postgrest.delete.call_args
        self.assertEqual(args[1]['id'], 'in.(1,2)')

if __name__ == '__main__':
    unittest.main()
