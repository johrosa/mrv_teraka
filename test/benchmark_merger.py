import sys
import os
import time
import json
from unittest.mock import MagicMock

# Add current directory to path to import local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mergin_workflow_manager import MerginDataMerger

def benchmark_detect_conflicts(n_records):
    print(f"\n--- Benchmarking detect_conflicts with {n_records} records ---")

    # Setup data
    original = [{"id": i, "val": f"orig_{i}"} for i in range(n_records)]
    collected = [{"id": i, "val": f"coll_{i}"} for i in range(n_records)]

    # All are modified
    merger = MerginDataMerger(MagicMock())

    start_time = time.time()
    conflicts = merger.detect_conflicts(original, collected)
    end_time = time.time()

    duration = end_time - start_time
    print(f"Duration: {duration:.4f}s")
    # In O(N*M), for 10k it should be slow.
    return duration

def benchmark_merge_api_calls(n_changes):
    print(f"\n--- Benchmarking merge API calls with {n_changes} changes ---")

    n_total = n_changes * 2
    original = [{"id": i, "val": "same"} for i in range(n_total)]

    # half modified, half deleted
    collected = [{"id": i, "val": "modified"} for i in range(n_changes)]
    # items from n_changes to n_total-1 are deleted (not in collected)

    mock_postgrest = MagicMock()
    merger = MerginDataMerger(mock_postgrest)

    start_time = time.time()
    merger.merge("test_table", original, collected, strategy='merge')
    end_time = time.time()

    # Count calls
    update_calls = mock_postgrest.update.call_count
    delete_calls = mock_postgrest.delete.call_count
    insert_calls = mock_postgrest.insert.call_count

    print(f"Update calls: {update_calls}")
    print(f"Delete calls: {delete_calls}")
    print(f"Insert calls: {insert_calls}")
    print(f"Total API calls: {update_calls + delete_calls + insert_calls}")
    print(f"Duration: {end_time - start_time:.4f}s")

    return update_calls + delete_calls + insert_calls

if __name__ == "__main__":
    benchmark_detect_conflicts(1000)
    benchmark_detect_conflicts(5000)
    # 10000 might be too slow if it's really O(N^2)
    # Let's try it anyway.
    benchmark_detect_conflicts(10000)

    benchmark_merge_api_calls(10)
    benchmark_merge_api_calls(100)
