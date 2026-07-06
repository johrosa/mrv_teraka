
import unittest
import os
import sys

# Add current directory to sys.path
sys.path.append(os.getcwd())

from mergin_workflow_manager import MerginDataMerger

class TestMergerLogic(unittest.TestCase):
    def setUp(self):
        class MockPostgREST:
            def insert(self, table, data, upsert=False): pass
            def update(self, table, data, filters): pass
            def delete(self, table, filters): pass

        self.merger = MerginDataMerger(MockPostgREST())

    def test_detect_conflicts(self):
        original = [
            {'id': 1, 'name': 'Item 1', 'val': 10},
            {'id': 2, 'name': 'Item 2', 'val': 20},
            {'id': 3, 'name': 'Item 3', 'val': 30},
        ]

        collected = [
            {'id': 1, 'name': 'Item 1', 'val': 10},      # No change
            {'id': 2, 'name': 'Item 2', 'val': 25},      # Modified
            {'id': 4, 'name': 'Item 4', 'val': 40},      # New
        ]
        # Item 3 is deleted

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')

        # We expect 3 conflict entries: deleted, added, modified
        self.assertEqual(len(conflicts), 3)

        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        self.assertEqual(deleted['count'], 1)
        self.assertEqual(deleted['ids'], [3])

        added = next(c for c in conflicts if c['type'] == 'added')
        self.assertEqual(added['count'], 1)
        self.assertEqual(added['ids'], [4])

        modified = next(c for c in conflicts if c['type'] == 'modified')
        self.assertEqual(modified['id'], 2)
        self.assertEqual(modified['original']['val'], 20)
        self.assertEqual(modified['collected']['val'], 25)

    def test_detect_conflicts_with_none_ids(self):
        # Ensure we handle None IDs gracefully (skip them)
        original = [
            {'id': 1, 'name': 'Item 1'},
            {'id': None, 'name': 'Bad Item'},
        ]
        collected = [
            {'id': 1, 'name': 'Item 1'},
            {'id': 2, 'name': 'New Item'},
            {'id': None, 'name': 'Another Bad Item'},
        ]

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')

        added = next(c for c in conflicts if c['type'] == 'added')
        self.assertEqual(added['ids'], [2])

        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        self.assertEqual(deleted['ids'], [])

if __name__ == '__main__':
    unittest.main()
