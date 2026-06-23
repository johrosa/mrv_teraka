# -*- coding: utf-8 -*-
import unittest
from unittest.mock import MagicMock
import sys
import os

# Add current directory to sys.path to import mergin_workflow_manager
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mergin_workflow_manager import MerginDataMerger

class TestMergerLogic(unittest.TestCase):
    def setUp(self):
        self.mock_api = MagicMock()
        self.merger = MerginDataMerger(self.mock_api)

    def test_detect_conflicts(self):
        original = [
            {'id': 1, 'name': 'A'},
            {'id': 2, 'name': 'B'},
            {'id': 3, 'name': 'C'}
        ]
        collected = [
            {'id': 1, 'name': 'A'},          # Unchanged
            {'id': 2, 'name': 'B_mod'},      # Modified
            {'id': 4, 'name': 'D'}           # Added
            # id 3 is deleted
        ]

        conflicts = self.merger.detect_conflicts(original, collected)

        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        self.assertEqual(deleted['count'], 1)
        self.assertEqual(deleted['ids'], [3])

        added = next(c for c in conflicts if c['type'] == 'added')
        self.assertEqual(added['count'], 1)
        self.assertEqual(added['ids'], [4])

        modified = next(c for c in conflicts if c['type'] == 'modified')
        self.assertEqual(modified['id'], 2)
        self.assertEqual(modified['original']['name'], 'B')
        self.assertEqual(modified['collected']['name'], 'B_mod')

    def test_merge_strategy_merge_optimized(self):
        original = [
            {'id': 1, 'name': 'A'},
            {'id': 2, 'name': 'B'},
            {'id': 3, 'name': 'C'}
        ]
        collected = [
            {'id': 1, 'name': 'A'},
            {'id': 2, 'name': 'B_mod'},
            {'id': 4, 'name': 'D'}
        ]

        results = self.merger.merge('test_table', original, collected, strategy='merge')

        # Verify optimized API calls
        # 1. UPSERT for item 2 (modified) and item 4 (added)
        self.mock_api.insert.assert_called_once()
        args, kwargs = self.mock_api.insert.call_args
        self.assertEqual(args[0], 'test_table')
        self.assertEqual(len(args[1]), 2)  # items 2 and 4
        self.assertTrue(kwargs.get('upsert'))

        # 2. No individual updates
        self.mock_api.update.assert_not_called()

        # 3. Batch DELETE for item 3
        self.mock_api.delete.assert_called_once()
        args, kwargs = self.mock_api.delete.call_args
        self.assertEqual(args[0], 'test_table')
        self.assertEqual(args[1], {'id': 'in.(3)'})

if __name__ == "__main__":
    unittest.main()
