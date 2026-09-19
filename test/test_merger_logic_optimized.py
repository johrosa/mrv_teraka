# -*- coding: utf-8 -*-
import unittest
from mergin_workflow_manager import MerginDataMerger


class TestMergerLogicOptimized(unittest.TestCase):
    """
    Tests de vérification pour la logique optimisée de MerginDataMerger.detect_conflicts.
    Ce test s'exécute sans dépendance QGIS.
    """

    def setUp(self):
        self.merger = MerginDataMerger(postgrest_client=None)

    def test_detect_conflicts_basic(self):
        original = [
            {'id': 1, 'name': 'Alpha'},
            {'id': 2, 'name': 'Beta'},
            {'id': 3, 'name': 'Gamma'}
        ]
        collected = [
            {'id': 2, 'name': 'Beta_Modified'},  # Modified
            {'id': 3, 'name': 'Gamma'},          # Unchanged
            {'id': 4, 'name': 'Delta'}           # Added
        ]
        # Deleted: 1

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')

        # Extract conflict types
        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        added = next(c for c in conflicts if c['type'] == 'added')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(deleted['count'], 1)
        self.assertEqual(set(deleted['ids']), {1})

        self.assertEqual(added['count'], 1)
        self.assertEqual(set(added['ids']), {4})

        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 2)
        self.assertEqual(modified[0]['original']['name'], 'Beta')
        self.assertEqual(modified[0]['collected']['name'], 'Beta_Modified')

    def test_custom_pk_field(self):
        original = [{'code': 'A1', 'val': 100}, {'code': 'B2', 'val': 200}]
        collected = [{'code': 'A1', 'val': 150}, {'code': 'C3', 'val': 300}]

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='code')

        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        added = next(c for c in conflicts if c['type'] == 'added')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(set(deleted['ids']), {'B2'})
        self.assertEqual(set(added['ids']), {'C3'})
        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 'A1')

    def test_edge_case_none_pk(self):
        original = [{'id': None, 'val': 10}, {'id': 1, 'val': 20}]
        collected = [{'id': None, 'val': 30}, {'id': 1, 'val': 20}]

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')
        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        added = next(c for c in conflicts if c['type'] == 'added')

        self.assertEqual(deleted['count'], 0)
        self.assertEqual(added['count'], 0)


if __name__ == '__main__':
    unittest.main()
