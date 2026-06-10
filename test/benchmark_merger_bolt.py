
import time
import random
import string
import sys
import os

# Add current directory to sys.path to import mergin_workflow_manager
sys.path.append(os.getcwd())

from mergin_workflow_manager import MerginDataMerger

class MockPostgREST:
    def __init__(self):
        self.calls = {'insert': 0, 'update': 0, 'delete': 0}
        self.items_affected = {'insert': 0, 'update': 0, 'delete': 0}

    def insert(self, table, data, upsert=False):
        self.calls['insert'] += 1
        if isinstance(data, list):
            self.items_affected['insert'] += len(data)
        else:
            self.items_affected['insert'] += 1

    def update(self, table, data, filters):
        self.calls['update'] += 1
        self.items_affected['update'] += 1

    def delete(self, table, filters):
        self.calls['delete'] += 1
        # Extract count from 'in.' filter if possible
        filter_val = next(iter(filters.values()))
        if filter_val.startswith('in.'):
            ids = filter_val.split('(')[1].split(')')[0].split(',')
            self.items_affected['delete'] += len(ids)
        else:
            self.items_affected['delete'] += 1

def generate_data(n):
    return [{'id': i, 'name': ''.join(random.choices(string.ascii_letters, k=10))} for i in range(n)]

def benchmark(label="Baseline"):
    print(f"\n--- {label} ---")
    n = 2000
    original = generate_data(n)
    collected = [dict(item) for item in original] # Deep copy dicts

    # Modify 200 items
    for i in range(0, 200):
        collected[i]['name'] += "_mod"

    # Add 200 items
    for i in range(n, n + 200):
        collected.append({'id': i, 'name': 'new'})

    # Delete 200 items from collected (they stay in original)
    original_extended = original + [{'id': i, 'name': 'to_del'} for i in range(-200, 0)]

    mock_api = MockPostgREST()
    merger = MerginDataMerger(mock_api)

    # Measure detect_conflicts
    start = time.time()
    conflicts = merger.detect_conflicts(original_extended, collected)
    detect_time = time.time() - start
    print(f"detect_conflicts took: {detect_time:.4f}s")

    # Measure merge
    start = time.time()
    merger.merge("test_table", original_extended, collected)
    merge_time = time.time() - start
    print(f"merge took: {merge_time:.4f}s")
    print(f"API Calls: {mock_api.calls}")
    print(f"Items Affected: {mock_api.items_affected}")

    return detect_time, merge_time

if __name__ == "__main__":
    benchmark()
