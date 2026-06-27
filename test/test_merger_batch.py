import unittest
from unittest.mock import MagicMock, patch
from mergin_workflow_manager import MerginDataMerger

class TestMergerBatch(unittest.TestCase):
    def setUp(self):
        self.mock_postgrest = MagicMock()
        self.merger = MerginDataMerger(self.mock_postgrest)

    def test_merge_batch_upsert_and_delete(self):
        # Data setup
        original = [
            {'id': '1', 'val': 'a'},
            {'id': '2', 'val': 'b'},
            {'id': '3', 'val': 'c'}
        ]
        collected = [
            {'id': '1', 'val': 'a_mod'}, # Modified
            {'id': '2', 'val': 'b'},     # Unchanged
            {'id': '4', 'val': 'new'}    # Added
            # id '3' is deleted
        ]

        table = "test_table"

        # Execute merge
        results = self.merger.merge(table, original, collected, strategy='merge', pk_field='id')

        # Verify batch UPSERT (id 1 and 4)
        # We expect one call to insert with upsert=True
        self.mock_postgrest.insert.assert_called_once()
        args, kwargs = self.mock_postgrest.insert.call_args
        self.assertEqual(args[0], table)
        self.assertEqual(len(args[1]), 2)
        self.assertTrue(kwargs.get('upsert'))

        # Verify batch DELETE (id 3)
        self.mock_postgrest.delete.assert_called_once_with(table, {'id': 'in.("3")'})

        # Verify actions report
        action_types = [a['type'] for a in results['actions']]
        self.assertIn('updated', action_types)
        self.assertIn('inserted', action_types)
        self.assertIn('deleted', action_types)

    def test_merge_batch_delete_multiple(self):
        original = [{'id': '1'}, {'id': '2'}, {'id': '3'}]
        collected = [] # All deleted

        self.merger.merge("table", original, collected, strategy='merge', pk_field='id')

        # Check if they are combined in a single delete call
        # Order of IDs in set might vary, so we check content of the 'in.' string
        self.mock_postgrest.delete.assert_called_once()
        args, kwargs = self.mock_postgrest.delete.call_args
        filters = args[1]
        self.assertTrue(filters['id'].startswith('in.('))
        self.assertIn('"1"', filters['id'])
        self.assertIn('"2"', filters['id'])
        self.assertIn('"3"', filters['id'])

if __name__ == '__main__':
    unittest.main()
