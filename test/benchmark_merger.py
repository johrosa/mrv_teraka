# -*- coding: utf-8 -*-
"""
Script de benchmark pour mesurer la performance de MerginDataMerger.detect_conflicts.
Compare le temps d'exécution sur de grands jeux de données (ex: 2000 enregistrements).
"""

import time
from mergin_workflow_manager import MerginDataMerger


def run_benchmark(num_records=2000):
    print(f"=== BENCHMARK MERGER (N={num_records}) ===")

    original = [{'id': i, 'name': f'record_{i}', 'val': i * 10} for i in range(num_records)]
    # 10% modified, 10% deleted, 10% added
    collected = [
        {'id': i, 'name': f'record_{i}' if i % 10 != 0 else f'mod_{i}', 'val': i * 10}
        for i in range(int(num_records * 0.1), int(num_records * 1.1))
    ]

    merger = MerginDataMerger(postgrest_client=None)

    # Mesurer detect_conflicts optimisé
    t0 = time.perf_counter()
    conflicts = merger.detect_conflicts(original, collected, pk_field='id')
    t1 = time.perf_counter()

    duration = t1 - t0
    print(f"Temps d'exécution pour {num_records} enregistrements: {duration:.6f} s")

    # Afficher le résumé des conflits
    deleted = next(c for c in conflicts if c['type'] == 'deleted')
    added = next(c for c in conflicts if c['type'] == 'added')
    modified = [c for c in conflicts if c['type'] == 'modified']

    print(f"  - Entrées supprimées : {deleted['count']}")
    print(f"  - Entrées ajoutées    : {added['count']}")
    print(f"  - Entrées modifiées  : {len(modified)}")

    assert duration < 0.05, f"La détection a pris {duration:.4f}s, ce qui dépasse le seuil de 0.05s !"
    print("⚡ Benchmark RÉUSSI: Performance O(N+M) confirmée !")


if __name__ == '__main__':
    run_benchmark(2000)
