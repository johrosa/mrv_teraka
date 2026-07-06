
import time
import random
import sys
import os

# Add current directory to sys.path to import mergin_workflow_manager
sys.path.append(os.getcwd())

from mergin_workflow_manager import MerginDataMerger

def benchmark_detect_conflicts():
    # Mock PostgREST client
    class MockPostgREST:
        pass

    merger = MerginDataMerger(MockPostgREST())

    # Generate data
    num_items = 5000
    original = []
    for i in range(num_items):
        original.append({
            'id': i,
            'name': f'Name {i}',
            'value': random.randint(1, 100)
        })

    # Collected: some same, some modified, some new, some deleted
    collected = []
    # 80% same or modified
    for i in range(int(num_items * 0.8)):
        item = original[i].copy()
        if random.random() < 0.2: # 20% modified
            item['value'] = item['value'] + 1
        collected.append(item)

    # 10% new
    for i in range(num_items, num_items + int(num_items * 0.1)):
        collected.append({
            'id': i,
            'name': f'New Name {i}',
            'value': random.randint(1, 100)
        })

    print(f"Benchmarking detect_conflicts with {len(original)} original items and {len(collected)} collected items...")

    start_time = time.time()
    merger.detect_conflicts(original, collected, pk_field='id')
    end_time = time.time()

    duration = end_time - start_time
    print(f"Duration: {duration:.4f} seconds")

    return duration

if __name__ == "__main__":
    benchmark_detect_conflicts()
