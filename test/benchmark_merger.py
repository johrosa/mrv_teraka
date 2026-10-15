# -*- coding: utf-8 -*-
import time
from mergin_workflow_manager import MerginDataMerger


def benchmark():
    merger = MerginDataMerger(postgrest_client=None)

    for N in [500, 2000, 5000]:
        original = [{'id': i, 'val': f'a_{i}'} for i in range(N)]
        collected = [{'id': i, 'val': f'a_{i}' if i % 2 == 0 else f'b_{i}'} for i in range(N)]

        t0 = time.perf_counter()
        conflicts = merger.detect_conflicts(original, collected, pk_field='id')
        t1 = time.perf_counter()

        print(f"N={N}: detect_conflicts executed in {t1 - t0:.6f} seconds ({len(conflicts)} conflict records)")


if __name__ == '__main__':
    benchmark()
