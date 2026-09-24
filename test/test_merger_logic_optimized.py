# -*- coding: utf-8 -*-
"""
Tests unitaires et benchmarks pour optimiser la détection de conflits dans MerginDataMerger.
"""

import unittest
import time
from mergin_workflow_manager import MerginDataMerger


class TestMergerLogicOptimized(unittest.TestCase):

    def setUp(self):
        self.merger = MerginDataMerger(postgrest_client=None)

    def test_detect_conflicts_correctness(self):
        """Vérifie l'exactitude de la détection de conflits (supprimés, ajoutés, modifiés)."""
        original = [
            {'id': 1, 'name': 'Item 1', 'val': 'A'},
            {'id': 2, 'name': 'Item 2', 'val': 'B'},
            {'id': 3, 'name': 'Item 3', 'val': 'C'}
        ]
        collected = [
            {'id': 1, 'name': 'Item 1', 'val': 'A'},           # Inchangé
            {'id': 2, 'name': 'Item 2', 'val': 'B_modified'},  # Modifié
            {'id': 4, 'name': 'Item 4', 'val': 'D'}            # Ajouté
            # Item 3 est Supprimé
        ]

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')

        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        added = next(c for c in conflicts if c['type'] == 'added')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(deleted['count'], 1)
        self.assertIn(3, deleted['ids'])

        self.assertEqual(added['count'], 1)
        self.assertIn(4, added['ids'])

        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 2)
        self.assertEqual(modified[0]['original']['val'], 'B')
        self.assertEqual(modified[0]['collected']['val'], 'B_modified')

    def test_detect_conflicts_performance(self):
        """Vérifie que la détection de conflits est rapide (< 0.05s pour 2000 éléments)."""
        N = 2000
        original = [{'id': i, 'val': f'v_{i}'} for i in range(N)]
        collected = [{'id': i, 'val': f'v_{i}' if i % 2 == 0 else f'v_{i}_mod'} for i in range(N)]

        t0 = time.perf_counter()
        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')
        elapsed = time.perf_counter() - t0

        modified_count = len([c for c in conflicts if c.get('type') == 'modified'])
        self.assertEqual(modified_count, N // 2)

        # L'ancienne implémentation O(N*M) prenait ~0.12s-0.35s; l'implémentation dictionnaire prend <0.01s.
        self.assertLess(elapsed, 0.05, f"Execution too slow: {elapsed:.4f}s")


if __name__ == '__main__':
    unittest.main()
