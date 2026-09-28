# -*- coding: utf-8 -*-
import unittest
import time
from mergin_workflow_manager import MerginDataMerger


class MockPostgREST:
    """Mock minimal client PostgREST pour tests unitaires."""
    pass


class TestMergerLogicOptimized(unittest.TestCase):
    """Tests unitaires et benchmarks pour la logique d'optimisation de MerginDataMerger."""

    def setUp(self):
        self.merger = MerginDataMerger(MockPostgREST())

    def test_detect_conflicts_correctness(self):
        """Vérifie la justesse de détection des conflits dans divers scénarios."""
        original = [
            {'id': 1, 'name': 'Alpha', 'status': 'old'},
            {'id': 2, 'name': 'Beta', 'status': 'old'},
            {'id': 3, 'name': 'Gamma', 'status': 'old'},
            {'id': None, 'name': 'Invalid'},
        ]
        collected = [
            {'id': 1, 'name': 'Alpha', 'status': 'old'},        # Inchangé
            {'id': 2, 'name': 'Beta', 'status': 'updated'},    # Modifié
            {'id': 4, 'name': 'Delta', 'status': 'new'},        # Ajouté
            {'id': None, 'name': 'Invalid_new'},
        ]

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')

        # Extraire les conflits par type
        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        added = next(c for c in conflicts if c['type'] == 'added')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(deleted['count'], 1)
        self.assertIn(3, deleted['ids'])

        self.assertEqual(added['count'], 1)
        self.assertIn(4, added['ids'])

        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 2)
        self.assertEqual(modified[0]['original']['status'], 'old')
        self.assertEqual(modified[0]['collected']['status'], 'updated')

    def test_detect_conflicts_custom_pk(self):
        """Vérifie le fonctionnement avec un nom de champ clé primaire personnalisé."""
        original = [{'uuid': 'a1', 'val': 10}, {'uuid': 'a2', 'val': 20}]
        collected = [{'uuid': 'a1', 'val': 15}]

        conflicts = self.merger.detect_conflicts(original, collected, pk_field='uuid')

        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(deleted['ids'], ['a2'])
        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 'a1')

    def test_detect_conflicts_empty_data(self):
        """Vérifie la gestion de jeux de données vides."""
        conflicts = self.merger.detect_conflicts([], [], pk_field='id')
        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        added = next(c for c in conflicts if c['type'] == 'added')

        self.assertEqual(deleted['count'], 0)
        self.assertEqual(added['count'], 0)
        self.assertEqual(len([c for c in conflicts if c['type'] == 'modified']), 0)

    def test_detect_conflicts_performance_benchmark(self):
        """Benchmark de performance pour vérifier la complexité O(N+M)."""
        n_records = 2000
        original = [{'id': i, 'val': f'orig_{i}'} for i in range(n_records)]
        collected = [{'id': i, 'val': f'orig_{i}' if i % 2 == 0 else f'mod_{i}'} for i in range(n_records)]
        collected.extend([{'id': n_records + i, 'val': f'new_{i}'} for i in range(200)])
        collected = collected[200:]

        t0 = time.perf_counter()
        conflicts = self.merger.detect_conflicts(original, collected, pk_field='id')
        t1 = time.perf_counter()

        elapsed = t1 - t0
        print(f"\n[BENCHMARK] Temps d'exécution detect_conflicts pour {n_records} enregistrements: {elapsed:.6f}s")
        # Doit s'exécuter en moins de 0.1s grâce à la table de hachage O(N+M) (anciennement ~0.2s-0.8s)
        self.assertLess(elapsed, 0.1)


if __name__ == '__main__':
    unittest.main()
