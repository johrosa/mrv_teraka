
import unittest
from unittest.mock import MagicMock, call
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from mergin_workflow_manager import MerginDataMerger

class TestMerginDataMergerOptimized(unittest.TestCase):
    def setUp(self):
        self.mock_postgrest = MagicMock()
        self.merger = MerginDataMerger(self.mock_postgrest)

    def test_detect_conflicts(self):
        original = [
            {'id': 1, 'name': 'Stay'},
            {'id': 2, 'name': 'Modify Me'},
            {'id': 3, 'name': 'Delete Me'}
        ]
        collected = [
            {'id': 1, 'name': 'Stay'},
            {'id': 2, 'name': 'I am modified'},
            {'id': 4, 'name': 'New Entry'}
        ]

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')

        # Check deleted
        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        self.assertEqual(deleted['count'], 1)
        self.assertIn(3, deleted['ids'])

        # Check added
        added = next(c for c in conflicts if c['type'] == 'added')
        self.assertEqual(added['count'], 1)
        self.assertIn(4, added['ids'])

        # Check modified
        modified = [c for c in conflicts if c['type'] == 'modified']
        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 2)
        self.assertEqual(modified[0]['collected']['name'], 'I am modified')

    def test_merge_strategy_merge(self):
        original = [
            {'id': 1, 'name': 'Stay'},
            {'id': 2, 'name': 'Modify Me'},
            {'id': 3, 'name': 'Delete Me'}
        ]
        collected = [
            {'id': 1, 'name': 'Stay'},
            {'id': 2, 'name': 'I am modified'},
            {'id': 4, 'name': 'New Entry'}
        ]

        results = self.merger.merge('my_table', original, collected, strategy='merge', pk_field='id')

        # Verify PostgREST calls
        # 1. Batch UPSERT for ID 2 (update) and ID 4 (insert)
        # We need to check if the mock was called with the correct data
        upsert_call = self.mock_postgrest.insert.call_args_list[0]
        self.assertEqual(upsert_call[0][0], 'my_table')
        upsert_data = upsert_call[0][1]
        self.assertEqual(len(upsert_data), 2)
        upsert_ids = {item['id'] for item in upsert_data}
        self.assertEqual(upsert_ids, {2, 4})
        self.assertEqual(upsert_call[1]['upsert'], True)

        # 2. Batch DELETE for ID 3
        self.mock_postgrest.delete.assert_called_once_with('my_table', {'id': 'in.(3)'})

        # Verify returned actions
        action_types = [a['type'] for a in results['actions']]
        self.assertIn('inserted', action_types)
        self.assertIn('updated', action_types)
        self.assertIn('deleted', action_types)
        self.assertEqual(len(results['actions']), 3)

    def test_merge_chunked_delete(self):
        # Create 250 original items and 0 collected items to trigger 2 chunks of DELETE
        original = [{'id': i, 'name': f'Item {i}'} for i in range(250)]
        collected = []

        results = self.merger.merge('my_table', original, collected, strategy='merge', pk_field='id')

        # Should have 2 delete calls (chunk size is 200)
        self.assertEqual(self.mock_postgrest.delete.call_count, 2)

        # Verify first chunk
        chunk1_ids = ",".join(map(str, range(200)))
        self.mock_postgrest.delete.assert_any_call('my_table', {'id': f'in.({chunk1_ids})'})

        # Verify second chunk
        chunk2_ids = ",".join(map(str, range(200, 250)))
        self.mock_postgrest.delete.assert_any_call('my_table', {'id': f'in.({chunk2_ids})'})

if __name__ == '__main__':
    unittest.main()
