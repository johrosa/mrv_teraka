# -*- coding: utf-8 -*-
"""
Tests unitaires et benchmark pour la détection de conflits optimisée dans MerginDataMerger.
"""

import unittest
import time
from mergin_workflow_manager import MerginDataMerger


class TestMerginDataMergerOptimized(unittest.TestCase):

    def setUp(self):
        self.merger = MerginDataMerger(postgrest_client=None)

    def test_detect_conflicts_correctness(self):
        original = [
            {'id': 1, 'name': 'Item 1', 'val': 'A'},
            {'id': 2, 'name': 'Item 2', 'val': 'B'},
            {'id': 3, 'name': 'Item 3', 'val': 'C'},
        ]
        collected = [
            {'id': 1, 'name': 'Item 1', 'val': 'A'},           # Inchangé
            {'id': 2, 'name': 'Item 2', 'val': 'B_modified'},  # Modifié
            {'id': 4, 'name': 'Item 4', 'val': 'D'},           # Ajouté
        ]
        # Item 3 est Supprimé

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

    def test_detect_conflicts_custom_pk(self):
        original = [
            {'code': 'A1', 'status': 'ok'},
            {'code': 'A2', 'status': 'ok'},
        ]
        collected = [
            {'code': 'A1', 'status': 'modified'},
            {'code': 'A3', 'status': 'new'},
        ]

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='code')

        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        added = next(c for c in conflicts if c['type'] == 'added')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertIn('A2', deleted['ids'])
        self.assertIn('A3', added['ids'])
        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 'A1')

    def test_detect_conflicts_performance_benchmark(self):
        # Générer 2000 entrées pour tester la performance du dictionnaire O(N+M)
        n_items = 2000
        original = [{'id': i, 'val': f'val_{i}'} for i in range(n_items)]
        collected = [{'id': i, 'val': f'val_{i}' if i % 10 != 0 else f'mod_{i}'} for i in range(50, n_items + 50)]

        start_time = time.perf_counter()
        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')
        elapsed_time = time.perf_counter() - start_time

        # Vérifier que le traitement est ultra-rapide (< 50 ms pour 2000 items)
        print(f"\n[Benchmark] detect_conflicts sur {n_items} items: {elapsed_time:.4f} sec")
        self.assertLess(elapsed_time, 0.05, f"La détection de conflits a pris trop de temps: {elapsed_time:.4f}s")


if __name__ == '__main__':
    unittest.main()
