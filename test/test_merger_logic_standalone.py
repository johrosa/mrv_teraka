# -*- coding: utf-8 -*-
import unittest
from mergin_workflow_manager import MerginDataMerger


class TestMergerLogicStandalone(unittest.TestCase):
    """Test standard de la logique MerginDataMerger.detect_conflicts sans PyQGIS."""

    def setUp(self):
        self.merger = MerginDataMerger(postgrest_client=None)

    def test_detect_conflicts_basic(self):
        original = [
            {'id': 1, 'name': 'Tree A', 'height': 10},
            {'id': 2, 'name': 'Tree B', 'height': 15},
            {'id': 3, 'name': 'Tree C', 'height': 20},
        ]
        collected = [
            {'id': 2, 'name': 'Tree B Modified', 'height': 16}, # Modified
            {'id': 3, 'name': 'Tree C', 'height': 20},          # Unchanged
            {'id': 4, 'name': 'Tree D', 'height': 8},           # Added
        ]

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')

        deleted_conflict = next(c for c in conflicts if c['type'] == 'deleted')
        self.assertEqual(deleted_conflict['count'], 1)
        self.assertIn(1, deleted_conflict['ids'])

        added_conflict = next(c for c in conflicts if c['type'] == 'added')
        self.assertEqual(added_conflict['count'], 1)
        self.assertIn(4, added_conflict['ids'])

        modified_conflicts = [c for c in conflicts if c['type'] == 'modified']
        self.assertEqual(len(modified_conflicts), 1)
        self.assertEqual(modified_conflicts[0]['id'], 2)
        self.assertEqual(modified_conflicts[0]['collected']['name'], 'Tree B Modified')

    def test_detect_conflicts_empty_and_none(self):
        original = [{'id': None, 'name': 'Invalid'}]
        collected = [{'id': None, 'name': 'Invalid New'}, {'id': 10, 'name': 'Valid'}]

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')

        added_conflict = next(c for c in conflicts if c['type'] == 'added')
        self.assertIn(10, added_conflict['ids'])

        modified_conflicts = [c for c in conflicts if c['type'] == 'modified']
        self.assertEqual(len(modified_conflicts), 0)


if __name__ == '__main__':
    unittest.main()
