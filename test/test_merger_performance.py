# -*- coding: utf-8 -*-
"""
Tests unitaires et benchmarks pour MerginDataMerger (sans dépendance QGIS)
"""

import unittest
import time
from mergin_workflow_manager import MerginDataMerger


class TestMerginDataMergerPerformance(unittest.TestCase):

    def setUp(self):
        self.merger = MerginDataMerger(postgrest_client=None)

    def test_detect_conflicts_correctness(self):
        """Vérifie la justesse de la détection de conflits (ajouts, suppressions, modifications, Nones)."""
        original = [
            {'id': 1, 'name': 'Alpha', 'val': 10},
            {'id': 2, 'name': 'Beta', 'val': 20},
            {'id': 3, 'name': 'Gamma', 'val': 30},
            {'id': None, 'name': 'InvalidOrig', 'val': 0}
        ]
        collected = [
            {'id': 2, 'name': 'Beta Modified', 'val': 20},  # Modifié
            {'id': 3, 'name': 'Gamma', 'val': 30},           # Inchangé
            {'id': 4, 'name': 'Delta', 'val': 40},           # Ajouté
            {'id': None, 'name': 'InvalidColl', 'val': 0}
        ]

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')

        # Extraire par type
        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        added = next(c for c in conflicts if c['type'] == 'added')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(deleted['count'], 1)
        self.assertIn(1, deleted['ids'])

        self.assertEqual(added['count'], 1)
        self.assertIn(4, added['ids'])

        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 2)
        self.assertEqual(modified[0]['collected']['name'], 'Beta Modified')

    def test_detect_conflicts_empty_data(self):
        """Vérifie le comportement avec des listes vides."""
        conflicts = self.merger.detect_conflicts([], [], pk_field='id')

        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        added = next(c for c in conflicts if c['type'] == 'added')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(deleted['count'], 0)
        self.assertEqual(added['count'], 0)
        self.assertEqual(len(modified), 0)

    def test_detect_conflicts_benchmark(self):
        """Mesure les performances sur un jeu de données de 2000 éléments."""
        original = [{'id': i, 'name': f'Name_{i}', 'val': i * 10} for i in range(2000)]
        collected = [{'id': i, 'name': f'Name_{i}_mod' if i % 2 == 0 else f'Name_{i}', 'val': i * 10} for i in range(500, 2500)]

        t0 = time.perf_counter()
        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')
        elapsed = time.perf_counter() - t0

        modified_count = sum(1 for c in conflicts if c['type'] == 'modified')
        self.assertEqual(modified_count, 750)

        # L'exécution doit prendre beaucoup moins de 0.1s (typiquement ~0.003s)
        self.assertLess(elapsed, 0.05, f"detect_conflicts trop lent: {elapsed:.4f}s")
        print(f"\n[BENCHMARK] detect_conflicts pour 2000 items terminé en {elapsed:.4f}s")


if __name__ == '__main__':
    unittest.main()
