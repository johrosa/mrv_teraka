# -*- coding: utf-8 -*-
import time
import unittest
from unittest.mock import MagicMock
from mergin_workflow_manager import MerginDataMerger

def generate_data(count):
    return [{"id": i, "name": f"item_{i}", "value": i * 10} for i in range(count)]

def run_benchmark():
    print("--- MerginDataMerger Performance Benchmark ---")

    # 1. Setup data (5,000 records)
    count = 5000
    original = generate_data(count)

    # Collected data:
    # - 1000 items unchanged
    # - 2000 items modified
    # - 1000 items deleted (IDs 3000 to 3999)
    # - 1000 items added (IDs 5000 to 5999)
    collected = []
    # Unchanged & Modified
    for i in range(3000):
        item = {"id": i, "name": f"item_{i}", "value": i * 10}
        if i >= 1000:
            item["value"] += 1  # modification
        collected.append(item)

    # Added
    for i in range(5000, 6000):
        collected.append({"id": i, "name": f"new_item_{i}", "value": i * 10})

    print(f"Dataset: {len(original)} original records, {len(collected)} collected records.")

    # 2. Benchmark detect_conflicts
    mock_client = MagicMock()
    merger = MerginDataMerger(mock_client)

    start_time = time.time()
    conflicts = merger.detect_conflicts(original, collected)
    end_time = time.time()

    detect_duration = end_time - start_time
    print(f"detect_conflicts duration: {detect_duration:.4f} seconds")

    # 3. Benchmark merge
    # Reset mock to count calls
    mock_client.reset_mock()

    start_time = time.time()
    results = merger.merge("test_table", original, collected, strategy='merge')
    end_time = time.time()

    merge_duration = end_time - start_time
    call_count = mock_client.insert.call_count + mock_client.update.call_count + mock_client.delete.call_count

    print(f"merge duration: {merge_duration:.4f} seconds")
    print(f"Total API calls made: {call_count}")

    return {
        "detect_duration": detect_duration,
        "merge_duration": merge_duration,
        "call_count": call_count
    }

if __name__ == "__main__":
    run_benchmark()
