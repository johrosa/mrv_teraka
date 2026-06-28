
import unittest
import sys
import os

# Add current directory to sys.path to import mergin_workflow_manager
sys.path.append(os.getcwd())

from mergin_workflow_manager import MerginDataMerger

class TestMerginDataMerger(unittest.TestCase):
    def setUp(self):
        self.merger = MerginDataMerger(None)

    def test_detect_conflicts_empty(self):
        conflicts = self.merger.detect_conflicts([], [])
        self.assertEqual(len(conflicts), 2)  # deleted and added blocks
        self.assertEqual(conflicts[0]['count'], 0)
        self.assertEqual(conflicts[1]['count'], 0)

    def test_detect_conflicts_added(self):
        original = [{'id': 1, 'name': 'A'}]
        collected = [{'id': 1, 'name': 'A'}, {'id': 2, 'name': 'B'}]
        conflicts = self.merger.detect_conflicts(original, collected)

        added = next(c for c in conflicts if c['type'] == 'added')
        self.assertEqual(added['count'], 1)
        self.assertEqual(added['ids'], [2])

    def test_detect_conflicts_deleted(self):
        original = [{'id': 1, 'name': 'A'}, {'id': 2, 'name': 'B'}]
        collected = [{'id': 1, 'name': 'A'}]
        conflicts = self.merger.detect_conflicts(original, collected)

        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        self.assertEqual(deleted['count'], 1)
        self.assertEqual(deleted['ids'], [2])

    def test_detect_conflicts_modified(self):
        original = [{'id': 1, 'name': 'A', 'val': 10}]
        collected = [{'id': 1, 'name': 'A', 'val': 20}]
        conflicts = self.merger.detect_conflicts(original, collected)

        modified = [c for c in conflicts if c['type'] == 'modified']
        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 1)
        self.assertEqual(modified[0]['original']['val'], 10)
        self.assertEqual(modified[0]['collected']['val'], 20)

    def test_detect_conflicts_none_id(self):
        # Should handle None IDs gracefully (skip them for modified check)
        original = [{'id': None, 'name': 'A'}]
        collected = [{'id': None, 'name': 'A'}]
        conflicts = self.merger.detect_conflicts(original, collected)
        # 2 entries (deleted and added, both empty)
        self.assertEqual(len(conflicts), 2)
        self.assertEqual(conflicts[0]['count'], 0)
        self.assertEqual(conflicts[1]['count'], 0)

if __name__ == "__main__":
    unittest.main()
