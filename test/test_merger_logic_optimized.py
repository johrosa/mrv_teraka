import unittest
from unittest.mock import MagicMock, patch, call
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from mergin_workflow_manager import MerginDataMerger

class TestMergerLogicOptimized(unittest.TestCase):
    def setUp(self):
        self.mock_postgrest = MagicMock()
        self.merger = MerginDataMerger(self.mock_postgrest)

    def test_detect_conflicts_accuracy(self):
        original = [
            {'id': 1, 'name': 'A'},
            {'id': 2, 'name': 'B'},
            {'id': 3, 'name': 'C'}
        ]
        collected = [
            {'id': 1, 'name': 'A'},       # Unchanged
            {'id': 2, 'name': 'B_mod'},   # Modified
            {'id': 4, 'name': 'D'}        # Added
        ]
        # ID 3 is deleted

        conflicts = self.merger.detect_conflicts(original, collected)

        # Check counts
        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        added = next(c for c in conflicts if c['type'] == 'added')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(deleted['count'], 1)
        self.assertIn(3, deleted['ids'])

        self.assertEqual(added['count'], 1)
        self.assertIn(4, added['ids'])

        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 2)
        self.assertEqual(modified[0]['collected']['name'], 'B_mod')

    def test_merge_batching_logic(self):
        original = [{'id': 1, 'name': 'A'}, {'id': 2, 'name': 'B'}]
        collected = [{'id': 1, 'name': 'A_mod'}, {'id': 3, 'name': 'C'}]
        # ID 2 is deleted

        results = self.merger.merge('test_table', original, collected)

        # Verify batch UPSERT was called once for both 1 and 3
        self.mock_postgrest.insert.assert_called_once_with(
            'test_table',
            [{'id': 1, 'name': 'A_mod'}, {'id': 3, 'name': 'C'}],
            upsert=True
        )

        # Verify batch DELETE was called for ID 2
        self.mock_postgrest.delete.assert_called_once_with(
            'test_table',
            {'id': 'in.(2)'}
        )

        # Verify actions list is correctly populated for UI
        action_types = [a['type'] for a in results['actions']]
        self.assertIn('updated', action_types)
        self.assertIn('inserted', action_types)
        self.assertIn('deleted', action_types)

    def test_chunked_delete(self):
        # Create 250 deletions to test chunking (chunk size is 200)
        original = [{'id': i} for i in range(250)]
        collected = []

        self.merger.merge('test_table', original, collected)

        # Should be 2 calls to delete
        self.assertEqual(self.mock_postgrest.delete.call_count, 2)

        # First call should have 200 IDs
        args1 = self.mock_postgrest.delete.call_args_list[0]
        id_list1 = args1[0][1]['id']
        self.assertEqual(len(id_list1.split(',')), 200)

        # Second call should have 50 IDs
        args2 = self.mock_postgrest.delete.call_args_list[1]
        id_list2 = args2[0][1]['id']
        self.assertEqual(len(id_list2.split(',')), 50)

if __name__ == "__main__":
    unittest.main()
