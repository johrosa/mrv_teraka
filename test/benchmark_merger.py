# -*- coding: utf-8 -*-
import time
import uuid
import sys
import os

# Add current directory to path to import local modules
sys.path.append(os.getcwd())

from mergin_workflow_manager import MerginDataMerger

class MockPostgREST:
    def __init__(self):
        self.call_count = 0

    def insert(self, table, data, upsert=False):
        self.call_count += 1
        return {}

    def update(self, table, data, filters):
        self.call_count += 1
        return {}

    def delete(self, table, filters):
        self.call_count += 1
        return {}

def run_benchmark():
    print("--- MerginDataMerger Benchmark ---")

    # Generate data
    num_records = 5000
    original = []
    for i in range(num_records):
        original.append({
            'id': str(uuid.uuid4()),
            'name': f"Record {i}",
            'value': i
        })

    # Collected data with changes
    collected = []
    # Keep 50% records (no change)
    split1 = num_records // 2
    collected.extend(original[:split1])
    # Modify 20% records
    split2 = split1 + num_records // 5
    for i in range(split1, split2):
        item = original[i].copy()
        item['value'] = i * 2
        collected.append(item)
    # Delete 30% records - done by not adding them
    # Add 10% new records
    for i in range(num_records // 10):
        collected.append({
            'id': str(uuid.uuid4()),
            'name': f"New Record {i}",
            'value': 1000 + i
        })

    mock_client = MockPostgREST()
    merger = MerginDataMerger(mock_client)

    # Benchmark detect_conflicts
    start_time = time.time()
    conflicts = merger.detect_conflicts(original, collected)
    end_time = time.time()
    detect_duration = end_time - start_time
    print(f"detect_conflicts duration: {detect_duration:.4f}s")

    # Benchmark merge
    mock_client.call_count = 0
    start_time = time.time()
    results = merger.merge("test_table", original, collected, strategy='merge')
    end_time = time.time()
    merge_duration = end_time - start_time
    print(f"merge duration: {merge_duration:.4f}s")
    print(f"API calls count: {mock_client.call_count}")

    # Verification
    # Expected: 200 modified, 100 added, 300 deleted
    # Current implementation:
    # 1 batch insert for 100 added
    # 200 individual updates
    # 300 individual deletes
    # Total calls: 1 + 200 + 300 = 501

if __name__ == "__main__":
    run_benchmark()
