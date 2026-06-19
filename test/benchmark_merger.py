import time
import sys
import os

# Mock postgrest_client to avoid dependencies
class MockPostgrest:
    def insert(self, table, data, upsert=False): pass
    def update(self, table, data, filters): pass
    def delete(self, table, filters): pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from mergin_workflow_manager import MerginDataMerger

def benchmark(n=5000):
    original = [{'id': i, 'val': f'val_{i}', 'other': 'data'} for i in range(n)]
    collected = [{'id': i, 'val': f'val_{i}', 'other': 'data'} for i in range(n)]

    # Add some changes
    for i in range(0, n, 10):
        collected[i]['val'] = f'changed_{i}'

    # Add some additions
    for i in range(n, n + 10):
        collected.append({'id': i, 'val': f'new_{i}', 'other': 'data'})

    # Remove some
    original.append({'id': -1, 'val': 'gone', 'other': 'data'})

    merger = MerginDataMerger(MockPostgrest())

    start = time.time()
    merger.detect_conflicts(original, collected)
    end = time.time()
    print(f"detect_conflicts with {n} records: {end - start:.4f}s")

if __name__ == "__main__":
    benchmark(1000)
    benchmark(5000)
