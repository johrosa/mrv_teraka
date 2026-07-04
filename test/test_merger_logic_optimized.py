
import unittest
from mergin_workflow_manager import MerginDataMerger

class MockPostgrest:
    def insert(self, *args, **kwargs): pass
    def update(self, *args, **kwargs): pass
    def delete(self, *args, **kwargs): pass

class TestMergerLogic(unittest.TestCase):
    def setUp(self):
        self.merger = MerginDataMerger(MockPostgrest())

    def test_detect_conflicts_basic(self):
        original = [
            {'id': 1, 'name': 'A'},
            {'id': 2, 'name': 'B'},
            {'id': 3, 'name': 'C'}
        ]
        # 1 modified, 2 same, 3 deleted, 4 added
        collected = [
            {'id': 1, 'name': 'A_mod'},
            {'id': 2, 'name': 'B'},
            {'id': 4, 'name': 'D'}
        ]

        conflicts = self.merger.detect_conflicts(original, collected)

        # Verify counts
        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        added = next(c for c in conflicts if c['type'] == 'added')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(deleted['count'], 1)
        self.assertIn(3, deleted['ids'])

        self.assertEqual(added['count'], 1)
        self.assertIn(4, added['ids'])

        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 1)
        self.assertEqual(modified[0]['collected']['name'], 'A_mod')

    def test_detect_conflicts_no_pk(self):
        original = [{'id': None, 'name': 'A'}]
        collected = [{'id': None, 'name': 'A'}]
        conflicts = self.merger.detect_conflicts(original, collected)

        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        added = next(c for c in conflicts if c['type'] == 'added')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(deleted['count'], 0)
        self.assertEqual(added['count'], 0)
        self.assertEqual(len(modified), 0)

if __name__ == '__main__':
    unittest.main()
