
import time
import sys
import os

# Add current directory to sys.path to import local modules
sys.path.append(os.getcwd())

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

def benchmark_all():
    pk_field = 'id'
    num_records = 5000

    print(f"--- Benchmarking with {num_records} records ---")

    # Create original data
    original = [{'id': i, 'val': f'orig_{i}'} for i in range(num_records)]

    # Create collected data
    collected = []
    # 2000 modified
    for i in range(2000):
        collected.append({'id': i, 'val': f'mod_{i}'})
    # 2000 unchanged
    for i in range(2000, 4000):
        collected.append({'id': i, 'val': f'orig_{i}'})
    # 1000 deleted (from 4000 to 5000)
    # 500 added
    for i in range(5000, 5500):
        collected.append({'id': i, 'val': f'new_{i}'})

    mock_api = MockPostgrest()
    merger = MerginDataMerger(mock_api)

    # Benchmark detect_conflicts
    start_time = time.time()
    conflicts = merger.detect_conflicts(original, collected, pk_field)
    end_time = time.time()

    detect_duration = end_time - start_time
    print(f"detect_conflicts took {detect_duration:.4f} seconds.")

    # Benchmark merge
    mock_api.request_count = 0
    start_time = time.time()
    merger.merge("test_table", original, collected, strategy='merge', pk_field=pk_field)
    end_time = time.time()

    merge_duration = end_time - start_time
    print(f"merge (API) took {merge_duration:.4f} seconds.")
    print(f"API requests made: {mock_api.request_count}")

    return detect_duration, mock_api.request_count

if __name__ == "__main__":
    benchmark_all()
