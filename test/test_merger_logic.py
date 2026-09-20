# -*- coding: utf-8 -*-
"""
Tests unitaires pour la logique de détection de conflits de MerginDataMerger
"""

import unittest
from mergin_workflow_manager import MerginDataMerger


class TestMerginDataMergerLogic(unittest.TestCase):

    def setUp(self):
        self.merger = MerginDataMerger(postgrest_client=None)

    def test_detect_conflicts_no_changes(self):
        original = [{'id': 1, 'name': 'A'}, {'id': 2, 'name': 'B'}]
        collected = [{'id': 1, 'name': 'A'}, {'id': 2, 'name': 'B'}]

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')

        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        added = next(c for c in conflicts if c['type'] == 'added')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(deleted['count'], 0)
        self.assertEqual(added['count'], 0)
        self.assertEqual(len(modified), 0)

    def test_detect_conflicts_added(self):
        original = [{'id': 1, 'name': 'A'}]
        collected = [{'id': 1, 'name': 'A'}, {'id': 2, 'name': 'B'}]

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')

        added = next(c for c in conflicts if c['type'] == 'added')
        self.assertEqual(added['count'], 1)
        self.assertEqual(added['ids'], [2])

    def test_detect_conflicts_deleted(self):
        original = [{'id': 1, 'name': 'A'}, {'id': 2, 'name': 'B'}]
        collected = [{'id': 1, 'name': 'A'}]

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')

        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        self.assertEqual(deleted['count'], 1)
        self.assertEqual(deleted['ids'], [2])

    def test_detect_conflicts_modified(self):
        original = [{'id': 1, 'name': 'A'}, {'id': 2, 'name': 'B'}]
        collected = [{'id': 1, 'name': 'A'}, {'id': 2, 'name': 'B_updated'}]

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')

        modified = [c for c in conflicts if c['type'] == 'modified']
        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 2)
        self.assertEqual(modified[0]['original'], {'id': 2, 'name': 'B'})
        self.assertEqual(modified[0]['collected'], {'id': 2, 'name': 'B_updated'})

    def test_detect_conflicts_custom_pk_and_none(self):
        original = [{'code': 'C1', 'val': 10}, {'code': 'C2', 'val': 20}]
        collected = [{'code': 'C1', 'val': 10}, {'code': 'C2', 'val': 25}, {'code': None, 'val': 30}]

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='code')

        modified = [c for c in conflicts if c['type'] == 'modified']
        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 'C2')


if __name__ == '__main__':
    unittest.main()
