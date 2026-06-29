import unittest
from unittest.mock import MagicMock
import sys
import os

# Add root to path
sys.path.append(os.getcwd())

from mergin_workflow_manager import MerginDataMerger

class TestMergerLogic(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()
        self.merger = MerginDataMerger(self.mock_client)

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
            # id 3 is deleted
        ]

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')

        # Verify deleted
        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        self.assertEqual(deleted['count'], 1)
        self.assertEqual(deleted['ids'], [3])

        # Verify added
        added = next(c for c in conflicts if c['type'] == 'added')
        self.assertEqual(added['count'], 1)
        self.assertEqual(added['ids'], [4])

        # Verify modified
        modified = [c for c in conflicts if c['type'] == 'modified']
        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 2)
        self.assertEqual(modified[0]['original'], {'id': 2, 'name': 'B'})
        self.assertEqual(modified[0]['collected'], {'id': 2, 'name': 'B_mod'})

    def test_merge_strategy_merge(self):
        original = [{'id': 1, 'name': 'A'}, {'id': 2, 'name': 'B'}]
        collected = [{'id': 2, 'name': 'B_mod'}, {'id': 3, 'name': 'C'}]

        results = self.merger.merge('test_table', original, collected, strategy='merge', pk_field='id')

        # Check mock calls
        # 1. UPSERT for id 2 and 3
        items_to_upsert = [{'id': 2, 'name': 'B_mod'}, {'id': 3, 'name': 'C'}]
        self.mock_client.insert.assert_called_with('test_table', items_to_upsert, upsert=True)

        # 2. Batch Delete for id 1
        self.mock_client.delete.assert_called_with('test_table', {'id': 'in.(1)'})

    def test_merge_strategy_replace(self):
        original = [{'id': 1, 'name': 'A'}]
        collected = [{'id': 2, 'name': 'B'}]

        results = self.merger.merge('test_table', original, collected, strategy='replace', pk_field='id')

        # Check mock calls
        self.mock_client.delete.assert_called_with('test_table', {'id': 'in.(1)'})
        self.mock_client.insert.assert_called_with('test_table', collected)

if __name__ == '__main__':
    unittest.main()
