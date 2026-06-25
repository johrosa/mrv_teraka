import unittest
from unittest.mock import MagicMock
from mergin_workflow_manager import MerginDataMerger

class TestMergerLogic(unittest.TestCase):
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
            {'id': 1, 'name': 'A'},      # Unchanged
            {'id': 2, 'name': 'B_mod'},  # Modified
            {'id': 4, 'name': 'D'}       # Added
        ]
        # ID 3 is deleted

        conflicts = self.merger.detect_conflicts(original, collected)

        # Verify deletions
        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        self.assertEqual(deleted['count'], 1)
        self.assertIn(3, deleted['ids'])

        # Verify additions
        added = next(c for c in conflicts if c['type'] == 'added')
        self.assertEqual(added['count'], 1)
        self.assertIn(4, added['ids'])

        # Verify modifications
        modified = next(c for c in conflicts if c['type'] == 'modified')
        self.assertEqual(modified['id'], 2)
        self.assertEqual(modified['original']['name'], 'B')
        self.assertEqual(modified['collected']['name'], 'B_mod')

    def test_merge_batching(self):
        original = [{'id': 1, 'name': 'A'}, {'id': 2, 'name': 'B'}]
        collected = [{'id': 1, 'name': 'A_mod'}, {'id': 3, 'name': 'C'}]
        # ID 2 is deleted

        results = self.merger.merge("test_table", original, collected)

        # Verify postgrest.insert called once with batch of 2 (ID 1 mod and ID 3 add)
        self.mock_postgrest.insert.assert_called_once()
        args, kwargs = self.mock_postgrest.insert.call_args
        self.assertEqual(args[0], "test_table")
        self.assertEqual(len(args[1]), 2)
        self.assertTrue(kwargs.get('upsert'))

        # Verify postgrest.delete called once with batch 'in.'
        self.mock_postgrest.delete.assert_called_once_with("test_table", {'id': 'in.(2)'})

        # Verify results actions
        action_types = [a['type'] for a in results['actions']]
        self.assertIn('updated', action_types)
        self.assertIn('inserted', action_types)
        self.assertIn('deleted', action_types)

if __name__ == '__main__':
    unittest.main()
