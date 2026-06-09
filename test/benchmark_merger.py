# -*- coding: utf-8 -*-
import time
import random
from mergin_workflow_manager import MerginDataMerger

class MockPostgREST:
    def __init__(self):
        self.calls = []
    def insert(self, table, data, upsert=False):
        self.calls.append(('insert', table, len(data) if isinstance(data, list) else 1, upsert))
    def delete(self, table, filters):
        self.calls.append(('delete', table, filters))
    def update(self, table, data, filters):
        self.calls.append(('update', table, filters))

def benchmark_detect_conflicts(num_records):
    original = [{'id': i, 'val': random.random()} for i in range(num_records)]
    collected = [{'id': i, 'val': random.random() if i % 10 == 0 else original[i]['val']} for i in range(num_records)]

    merger = MerginDataMerger(None)

    start_time = time.time()
    conflicts = merger.detect_conflicts(original, collected)
    end_time = time.time()

    print(f"Benchmark detect_conflicts with {num_records} records:")
    print(f"Time: {end_time - start_time:.4f} seconds")
    print(f"Conflicts found: {len(conflicts)}")
    return end_time - start_time

def test_batch_operations():
    client = MockPostgREST()
    merger = MerginDataMerger(client)

    original = [{'id': 1, 'val': 'a'}, {'id': 2, 'val': 'b'}, {'id': 3, 'val': 'c'}]
    collected = [{'id': 1, 'val': 'a_mod'}, {'id': 2, 'val': 'b'}, {'id': 4, 'val': 'new'}]
    # 1 modified (id:1), 1 kept (id:2), 1 deleted (id:3), 1 added (id:4)

    print("\nTesting batch operations aggregation:")
    merger.merge('test_table', original, collected, strategy='merge')

    for call in client.calls:
        print(f"API Call: {call}")

    # Expecting 1 batch UPSERT (id:1 and id:4) and 1 batch DELETE (id:3)
    # The current implementation aggregates added and modified into one insert(upsert=True)
    # and deleted into one delete(in.)

if __name__ == "__main__":
    benchmark_detect_conflicts(1000)
    benchmark_detect_conflicts(5000)
    test_batch_operations()
