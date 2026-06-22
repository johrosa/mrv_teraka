
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
            {'id': 1, 'name': 'A'},       # No change
            {'id': 2, 'name': 'B_mod'},   # Modified
            {'id': 4, 'name': 'D'}        # Added
            # id 3 is deleted
        ]

        conflicts = self.merger.detect_conflicts(original, collected)

        # Parse results
        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        added = next(c for c in conflicts if c['type'] == 'added')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(deleted['count'], 1)
        self.assertIn(3, deleted['ids'])

        self.assertEqual(added['count'], 1)
        self.assertIn(4, added['ids'])

        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 2)

    def test_merge_calls_batch_methods(self):
        original = [{'id': 1, 'name': 'A'}, {'id': 2, 'name': 'B'}]
        collected = [{'id': 1, 'name': 'A_mod'}, {'id': 3, 'name': 'C'}] # 1 mod, 3 added, 2 deleted

        results = self.merger.merge('test_table', original, collected)

        # Verify batch UPSERT
        # Should contain id 1 and 3
        self.mock_postgrest.insert.assert_called_once()
        args, kwargs = self.mock_postgrest.insert.call_args
        self.assertEqual(args[0], 'test_table')
        self.assertEqual(len(args[1]), 2)
        self.assertTrue(kwargs.get('upsert'))

        # Verify batch DELETE
        # Should contain id 2
        self.mock_postgrest.delete.assert_called_once()
        args, kwargs = self.mock_postgrest.delete.call_args
        self.assertEqual(args[0], 'test_table')
        self.assertEqual(args[1], {'id': 'in.(2)'})

if __name__ == "__main__":
    unittest.main()
