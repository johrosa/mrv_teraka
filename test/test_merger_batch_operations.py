import unittest
from unittest.mock import MagicMock, call
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from mergin_workflow_manager import MerginDataMerger

class TestMergerBatchOperations(unittest.TestCase):
    def setUp(self):
        self.mock_postgrest = MagicMock()
        self.merger = MerginDataMerger(self.mock_postgrest)

    def test_merge_strategy_batch_upsert(self):
        original = [
            {'id': 1, 'name': 'A'},
            {'id': 2, 'name': 'B'}
        ]
        collected = [
            {'id': 1, 'name': 'A_mod'}, # Modified
            {'id': 3, 'name': 'C'}       # Added
            # id 2 is deleted
        ]

        results = self.merger.merge('test_table', original, collected, strategy='merge')

        # Verify UPSERT call
        # items 1 and 3 should be upserted
        expected_upsert = [
            {'id': 1, 'name': 'A_mod'},
            {'id': 3, 'name': 'C'}
        ]
        self.mock_postgrest.insert.assert_called_once_with('test_table', expected_upsert, upsert=True)

        # Verify DELETE call
        # item 2 should be deleted
        self.mock_postgrest.delete.assert_called_once_with('test_table', {'id': 'in.(2)'})

    def test_merge_strategy_chunked_delete(self):
        # Create many original items to trigger chunking (201 items)
        original = [{'id': i, 'name': f'N{i}'} for i in range(300)]
        collected = [] # All deleted

        self.merger.merge('test_table', original, collected, strategy='merge')

        # Should be 2 delete calls: one for 200 items, one for 100 items
        self.assertEqual(self.mock_postgrest.delete.call_count, 2)

        # Verify first chunk
        first_call_args = self.mock_postgrest.delete.call_args_list[0]
        id_list_1 = first_call_args[0][1]['id']
        self.assertTrue(id_list_1.startswith('in.(0,1,'))
        self.assertEqual(len(id_list_1.split(',')), 200)

    def test_replace_strategy_chunked_delete(self):
        original = [{'id': i, 'name': f'N{i}'} for i in range(250)]
        collected = [{'id': 999, 'name': 'New'}]

        self.merger.merge('test_table', original, collected, strategy='replace')

        # 2 delete calls for 200 + 50 items
        self.assertEqual(self.mock_postgrest.delete.call_count, 2)
        # 1 insert call for collected
        self.mock_postgrest.insert.assert_called_once_with('test_table', collected)

if __name__ == "__main__":
    unittest.main()
