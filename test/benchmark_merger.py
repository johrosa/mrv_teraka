
import time
import json
import os
import sys

# Mocking PostgREST client for the benchmark
class MockPostgREST:
    def __init__(self):
        self.call_counts = {'insert': 0, 'update': 0, 'delete': 0}

    def insert(self, table, data, upsert=False):
        self.call_counts['insert'] += 1
    def update(self, table, data, filters):
        self.call_counts['update'] += 1
    def delete(self, table, filters):
        self.call_counts['delete'] += 1

# Add current dir to path to import the manager
sys.path.append(os.path.abspath('.'))
from mergin_workflow_manager import MerginDataMerger

def run_benchmark(n_records=1000):
    print(f"--- Benchmark with {n_records} records ---")

    # Create synthetic data
    original = [{'id': i, 'val': f'original_{i}', 'other': 'data'} for i in range(n_records)]

    collected = []
    # 10% Same
    for i in range(int(n_records * 0.1)):
        collected.append(original[i].copy())

    # 40% Modified
    for i in range(int(n_records * 0.1), int(n_records * 0.5)):
        item = original[i].copy()
        item['val'] = f'modified_{i}'
        collected.append(item)

    # 10% Added
    for i in range(n_records, n_records + int(n_records * 0.1)):
        collected.append({'id': i, 'val': f'new_{i}', 'other': 'data'})

    mock_api = MockPostgREST()
    merger = MerginDataMerger(mock_api)

    # Measure detect_conflicts
    start = time.time()
    conflicts = merger.detect_conflicts(original, collected)
    end = time.time()

    detect_time = end - start
    print(f"detect_conflicts time: {detect_time:.4f}s")

    # Measure merge (API calls)
    start = time.time()
    results = merger.merge('test_table', original, collected, strategy='merge')
    end = time.time()

    merge_time = end - start
    print(f"merge time (local): {merge_time:.4f}s")
    print(f"API calls: {mock_api.call_counts}")

    return detect_time, merge_time, mock_api.call_counts

if __name__ == "__main__":
    run_benchmark(10000)
