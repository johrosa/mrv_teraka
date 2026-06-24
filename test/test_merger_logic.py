
import unittest
from unittest.mock import MagicMock
import sys

# Add current directory to sys.path
sys.path.append('.')

from mergin_workflow_manager import MerginDataMerger

class TestMergerLogic(unittest.TestCase):
    def setUp(self):
        self.mock_postgrest = MagicMock()
        self.merger = MerginDataMerger(self.mock_postgrest)

    def test_detect_conflicts_added(self):
        original = [{'id': 1, 'name': 'A'}]
        collected = [{'id': 1, 'name': 'A'}, {'id': 2, 'name': 'B'}]
        conflicts = self.merger.detect_conflicts(original, collected)

        added = next(c for c in conflicts if c['type'] == 'added')
        self.assertEqual(added['count'], 1)
        self.assertIn(2, added['ids'])

    def test_detect_conflicts_deleted(self):
        original = [{'id': 1, 'name': 'A'}, {'id': 2, 'name': 'B'}]
        collected = [{'id': 1, 'name': 'A'}]
        conflicts = self.merger.detect_conflicts(original, collected)

        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        self.assertEqual(deleted['count'], 1)
        self.assertIn(2, deleted['ids'])

    def test_detect_conflicts_modified(self):
        original = [{'id': 1, 'name': 'A'}]
        collected = [{'id': 1, 'name': 'A_mod'}]
        conflicts = self.merger.detect_conflicts(original, collected)

        modified = [c for c in conflicts if c['type'] == 'modified']
        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 1)
        self.assertEqual(modified[0]['original']['name'], 'A')
        self.assertEqual(modified[0]['collected']['name'], 'A_mod')

    def test_merge_batching(self):
        original = [{'id': 1, 'name': 'A'}, {'id': 2, 'name': 'B'}]
        collected = [{'id': 1, 'name': 'A_mod'}, {'id': 3, 'name': 'C'}]
        # 1 modified (id 1), 1 added (id 3), 1 deleted (id 2)

        results = self.merger.merge('test_table', original, collected)

        # Verify UPSERT call
        self.mock_postgrest.insert.assert_called_once()
        args, kwargs = self.mock_postgrest.insert.call_args
        self.assertEqual(args[0], 'test_table')
        self.assertEqual(len(args[1]), 2) # id 1 and id 3
        self.assertTrue(kwargs.get('upsert'))

        # Verify DELETE call
        self.mock_postgrest.delete.assert_called_once()
        args, kwargs = self.mock_postgrest.delete.call_args
        self.assertEqual(args[0], 'test_table')
        self.assertEqual(args[1]['id'], 'in.(2)')

    def test_merge_no_changes(self):
        original = [{'id': 1, 'name': 'A'}]
        collected = [{'id': 1, 'name': 'A'}]

        results = self.merger.merge('test_table', original, collected)

        self.mock_postgrest.insert.assert_not_called()
        self.mock_postgrest.delete.assert_not_called()
        self.assertEqual(len(results['actions']), 0)

if __name__ == '__main__':
    unittest.main()
