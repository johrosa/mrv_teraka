# -*- coding: utf-8 -*-
"""
Standalone unit tests for MerginDataMerger logic in mergin_workflow_manager.py.
Runs without PyQGIS dependencies.
"""

import unittest
from mergin_workflow_manager import MerginDataMerger


class DummyPostgREST:
    """Mock PostgREST client for testing merger logic."""
    pass


class TestMerginDataMerger(unittest.TestCase):

    def setUp(self):
        self.merger = MerginDataMerger(DummyPostgREST())

    def test_detect_conflicts_empty(self):
        original = []
        collected = []
        conflicts = self.merger.detect_conflicts(original, collected)

        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        added = next(c for c in conflicts if c['type'] == 'added')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(deleted['count'], 0)
        self.assertEqual(added['count'], 0)
        self.assertEqual(len(modified), 0)

    def test_detect_conflicts_added_and_deleted(self):
        original = [
            {'id': 1, 'name': 'Item 1'},
            {'id': 2, 'name': 'Item 2'},
        ]
        collected = [
            {'id': 2, 'name': 'Item 2'},
            {'id': 3, 'name': 'Item 3'},
        ]
        conflicts = self.merger.detect_conflicts(original, collected)

        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        added = next(c for c in conflicts if c['type'] == 'added')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(deleted['ids'], [1])
        self.assertEqual(added['ids'], [3])
        self.assertEqual(len(modified), 0)

    def test_detect_conflicts_modified(self):
        original = [
            {'id': 1, 'name': 'Item 1', 'value': 100},
            {'id': 2, 'name': 'Item 2', 'value': 200},
        ]
        collected = [
            {'id': 1, 'name': 'Item 1', 'value': 150},
            {'id': 2, 'name': 'Item 2', 'value': 200},
        ]
        conflicts = self.merger.detect_conflicts(original, collected)

        modified = [c for c in conflicts if c['type'] == 'modified']
        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 1)
        self.assertEqual(modified[0]['original'], {'id': 1, 'name': 'Item 1', 'value': 100})
        self.assertEqual(modified[0]['collected'], {'id': 1, 'name': 'Item 1', 'value': 150})

    def test_detect_conflicts_custom_pk(self):
        original = [
            {'code': 'A1', 'status': 'draft'},
        ]
        collected = [
            {'code': 'A1', 'status': 'published'},
            {'code': 'A2', 'status': 'draft'},
        ]
        conflicts = self.merger.detect_conflicts(original, collected, pk_field='code')

        added = next(c for c in conflicts if c['type'] == 'added')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(added['ids'], ['A2'])
        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 'A1')

    def test_detect_conflicts_missing_pk_none(self):
        original = [
            {'id': None, 'name': 'No PK'},
            {'id': 1, 'name': 'Valid PK'},
        ]
        collected = [
            {'id': 1, 'name': 'Valid PK'},
            {'id': None, 'name': 'Another No PK'},
        ]
        conflicts = self.merger.detect_conflicts(original, collected)

        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        added = next(c for c in conflicts if c['type'] == 'added')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(deleted['count'], 0)
        self.assertEqual(added['count'], 0)
        self.assertEqual(len(modified), 0)


if __name__ == '__main__':
    unittest.main()
