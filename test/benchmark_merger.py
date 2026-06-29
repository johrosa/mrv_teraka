import time
import random
import sys
import os

# Add root to path
sys.path.append(os.getcwd())

from mergin_workflow_manager import MerginDataMerger

def benchmark_detect_conflicts(n_records):
    # Mock postgrest client
    merger = MerginDataMerger(None)

    # Generate data
    original = []
    for i in range(n_records):
        original.append({
            'id': i,
            'name': f'Name {i}',
            'value': random.random(),
            'geometry': {'type': 'Point', 'coordinates': [random.random(), random.random()]}
        })

    # Collected: some added, some modified, some deleted
    collected = []
    # Keep 80% (some modified)
    for i in range(int(n_records * 0.8)):
        item = original[i].copy()
        if random.random() < 0.2: # 20% modified
            item['value'] = random.random()
        collected.append(item)

    # Add 10% new
    for i in range(n_records, n_records + int(n_records * 0.1)):
        collected.append({
            'id': i,
            'name': f'New Name {i}',
            'value': random.random(),
            'geometry': {'type': 'Point', 'coordinates': [random.random(), random.random()]}
        })

    start_time = time.time()
    conflicts = merger.detect_conflicts(original, collected, pk_field='id')
    end_time = time.time()

    duration = end_time - start_time
    print(f"n_records: {n_records}")
    print(f"Time taken: {duration:.4f} seconds")
    # print(f"Conflicts found: {len(conflicts)}")
    return duration

if __name__ == "__main__":
    print("Benchmarking detect_conflicts (Current O(N*M) implementation)")
    benchmark_detect_conflicts(1000)
    benchmark_detect_conflicts(2000)
    benchmark_detect_conflicts(5000)
