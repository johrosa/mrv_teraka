# -*- coding: utf-8 -*-
import time
import random
import sys
import os

# Add current directory to sys.path to import mergin_workflow_manager
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mergin_workflow_manager import MerginDataMerger

class MockPostgrest:
    def __init__(self):
        self.request_count = 0
    def insert(self, table, data, upsert=False):
        self.request_count += 1
    def update(self, table, data, filters):
        self.request_count += 1
    def delete(self, table, filters):
        self.request_count += 1

def generate_data(count):
    data = []
    for i in range(count):
        data.append({
            'id': i,
            'name': f'item_{i}',
            'value': random.random(),
            'status': 'active'
        })
    return data

def run_benchmark(n_original, n_collected):
    print(f"Benchmarking with {n_original} original and {n_collected} collected items...")

    original = generate_data(n_original)

    # Create collected data: some same, some modified, some new, some deleted
    collected = []
    # 70% same
    n_same = int(n_collected * 0.7)
    collected.extend(original[:n_same])

    # 20% modified
    n_modified = int(n_collected * 0.2)
    for i in range(n_same, n_same + n_modified):
        if i < n_original:
            item = original[i].copy()
            item['value'] = random.random()
            collected.append(item)

    # 10% new
    n_new = n_collected - len(collected)
    for i in range(n_new):
        collected.append({
            'id': n_original + i,
            'name': f'new_item_{i}',
            'value': random.random(),
            'status': 'new'
        })

    mock_api = MockPostgrest()
    merger = MerginDataMerger(mock_api)

    # Benchmark detect_conflicts
    start_time = time.time()
    conflicts = merger.detect_conflicts(original, collected)
    detect_time = time.time() - start_time
    print(f"detect_conflicts took: {detect_time:.4f} seconds")

    # Benchmark merge
    mock_api.request_count = 0
    start_time = time.time()
    merger.merge('test_table', original, collected)
    merge_time = time.time() - start_time
    print(f"merge logic took: {merge_time:.4f} seconds")
    print(f"API requests made: {mock_api.request_count}")

    return detect_time, merge_time, mock_api.request_count

if __name__ == "__main__":
    # Small test first
    run_benchmark(100, 100)
    print("-" * 30)
    # Larger test
    run_benchmark(2000, 2000)
