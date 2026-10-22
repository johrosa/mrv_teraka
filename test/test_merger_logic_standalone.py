# -*- coding: utf-8 -*-
"""
Tests unitaires standalone pour MerginDataMerger.detect_conflicts
Ne nécessite pas PyQGIS.
"""

import unittest
import time
from mergin_workflow_manager import MerginDataMerger


class TestMerginDataMergerStandalone(unittest.TestCase):
    """Tests standalone de la logique de detection de conflits et benchmarks."""

    def setUp(self):
        self.merger = MerginDataMerger(postgrest_client=None)

    def test_detect_conflicts_empty(self):
        """Vérifie le comportement avec des jeux de données vides."""
        conflicts = self.merger.detect_conflicts([], [], pk_field='id')
        self.assertEqual(len(conflicts), 2)
        self.assertEqual(conflicts[0]['type'], 'deleted')
        self.assertEqual(conflicts[0]['count'], 0)
        self.assertEqual(conflicts[1]['type'], 'added')
        self.assertEqual(conflicts[1]['count'], 0)

    def test_detect_conflicts_additions_deletions_modifications(self):
        """Vérifie la détection exacte d'ajouts, suppressions et modifications."""
        original = [
            {'id': 1, 'name': 'Alpha'},
            {'id': 2, 'name': 'Beta'},
            {'id': 3, 'name': 'Gamma'},
        ]
        collected = [
            {'id': 2, 'name': 'Beta Modified'},  # Modifié
            {'id': 3, 'name': 'Gamma'},          # Identique
            {'id': 4, 'name': 'Delta'},          # Ajouté
        ]

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')

        # Supprimés: ID 1
        deleted_conflict = next(c for c in conflicts if c['type'] == 'deleted')
        self.assertEqual(deleted_conflict['count'], 1)
        self.assertEqual(deleted_conflict['ids'], [1])

        # Ajoutés: ID 4
        added_conflict = next(c for c in conflicts if c['type'] == 'added')
        self.assertEqual(added_conflict['count'], 1)
        self.assertEqual(added_conflict['ids'], [4])

        # Modifiés: ID 2
        modified_conflicts = [c for c in conflicts if c['type'] == 'modified']
        self.assertEqual(len(modified_conflicts), 1)
        self.assertEqual(modified_conflicts[0]['id'], 2)
        self.assertEqual(modified_conflicts[0]['collected']['name'], 'Beta Modified')

    def test_detect_conflicts_none_primary_key(self):
        """Vérifie le filtrage des clés primaires None."""
        original = [{'id': None, 'name': 'Invalid'}, {'id': 1, 'name': 'Valid'}]
        collected = [{'id': 1, 'name': 'Valid'}, {'id': None, 'name': 'New Invalid'}]

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')
        deleted_conflict = next(c for c in conflicts if c['type'] == 'deleted')
        added_conflict = next(c for c in conflicts if c['type'] == 'added')

        self.assertEqual(deleted_conflict['count'], 0)
        self.assertEqual(added_conflict['count'], 0)

    def test_performance_detect_conflicts(self):
        """Benchmark de performance pour verifier la complexité O(N+M)."""
        N = 3000
        original = [{'id': i, 'value': f'val_{i}'} for i in range(N)]
        collected = [{'id': i, 'value': f'val_{i}' if i % 2 == 0 else f'mod_{i}'} for i in range(N - 100)]
        collected.extend([{'id': N + j, 'value': f'new_{j}'} for j in range(100)])

        start_time = time.perf_counter()
        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')
        elapsed_time = time.perf_counter() - start_time

        # Verifier les résultats
        deleted_conflict = next(c for c in conflicts if c['type'] == 'deleted')
        added_conflict = next(c for c in conflicts if c['type'] == 'added')
        modified_conflicts = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(deleted_conflict['count'], 100)
        self.assertEqual(added_conflict['count'], 100)
        self.assertEqual(len(modified_conflicts), 1450)

        # L'exécution O(N+M) pour 3000 éléments doit prendre nettement moins de 50ms (typiquement ~5ms)
        self.assertLess(elapsed_time, 0.05, f"detect_conflicts trop lent: {elapsed_time:.4f}s")


if __name__ == '__main__':
    unittest.main()
