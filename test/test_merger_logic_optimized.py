
import unittest
import sys
import os

# Add current directory to sys.path
sys.path.append(os.getcwd())

from mergin_workflow_manager import MerginDataMerger

class TestMergerLogicOptimized(unittest.TestCase):
    def setUp(self):
        self.merger = MerginDataMerger(None)

    def test_detect_added(self):
        original = [{'id': 1, 'v': 'a'}]
        collected = [{'id': 1, 'v': 'a'}, {'id': 2, 'v': 'b'}]
        conflicts = self.merger.detect_conflicts(original, collected)

        added = next(c for c in conflicts if c['type'] == 'added')
        self.assertEqual(added['count'], 1)
        self.assertEqual(added['ids'], [2])

    def test_detect_deleted(self):
        original = [{'id': 1, 'v': 'a'}, {'id': 2, 'v': 'b'}]
        collected = [{'id': 1, 'v': 'a'}]
        conflicts = self.merger.detect_conflicts(original, collected)

        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        self.assertEqual(deleted['count'], 1)
        self.assertEqual(deleted['ids'], [2])

    def test_detect_modified(self):
        original = [{'id': 1, 'v': 'a'}]
        collected = [{'id': 1, 'v': 'modified'}]
        conflicts = self.merger.detect_conflicts(original, collected)

        modified = [c for c in conflicts if c['type'] == 'modified']
        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 1)
        self.assertEqual(modified[0]['original']['v'], 'a')
        self.assertEqual(modified[0]['collected']['v'], 'modified')

    def test_no_changes(self):
        original = [{'id': 1, 'v': 'a'}]
        collected = [{'id': 1, 'v': 'a'}]
        conflicts = self.merger.detect_conflicts(original, collected)

        added = next(c for c in conflicts if c['type'] == 'added')
        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(added['count'], 0)
        self.assertEqual(deleted['count'], 0)
        self.assertEqual(len(modified), 0)

    def test_empty_lists(self):
        original = []
        collected = []
        conflicts = self.merger.detect_conflicts(original, collected)

        added = next(c for c in conflicts if c['type'] == 'added')
        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(added['count'], 0)
        self.assertEqual(deleted['count'], 0)
        self.assertEqual(len(modified), 0)

    def test_mixed_changes(self):
        original = [
            {'id': 1, 'v': 'same'},
            {'id': 2, 'v': 'to_mod'},
            {'id': 3, 'v': 'to_del'}
        ]
        collected = [
            {'id': 1, 'v': 'same'},
            {'id': 2, 'v': 'modded'},
            {'id': 4, 'v': 'new'}
        ]
        conflicts = self.merger.detect_conflicts(original, collected)

        added = next(c for c in conflicts if c['type'] == 'added')
        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(added['ids'], [4])
        self.assertEqual(deleted['ids'], [3])
        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 2)

    def test_none_pk_handling(self):
        # Items with None PK should be ignored in modification detection to avoid crashes
        original = [{'id': None, 'v': 'a'}]
        collected = [{'id': None, 'v': 'b'}]
        conflicts = self.merger.detect_conflicts(original, collected)

        modified = [c for c in conflicts if c['type'] == 'modified']
        self.assertEqual(len(modified), 0)

if __name__ == "__main__":
    unittest.main()
