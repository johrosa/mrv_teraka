
import time
import sys
import os

# Ensure we can import from the current directory
sys.path.append(os.getcwd())

from mergin_workflow_manager import MerginDataMerger

class MockPostgrest:
    def insert(self, *args, **kwargs): pass
    def update(self, *args, **kwargs): pass
    def delete(self, *args, **kwargs): pass

def benchmark_conflict_detection(size=2000):
    merger = MerginDataMerger(MockPostgrest())

    # Prepare data
    # half same, half modified
    original = [{'id': i, 'val': f"value_{i}"} for i in range(size)]
    collected = [{'id': i, 'val': f"value_{i}" if i % 2 == 0 else f"modified_{i}"} for i in range(size)]

    print(f"--- Benchmarking detect_conflicts with {size} items ---")
    start = time.time()
    conflicts = merger.detect_conflicts(original, collected)
    end = time.time()

    duration = end - start
    print(f"Duration: {duration:.4f}s")

    # Sanity check
    modified_count = sum(1 for c in conflicts if c['type'] == 'modified')
    print(f"Modified count detected: {modified_count} (Expected: {size // 2})")
    return duration

if __name__ == "__main__":
    benchmark_conflict_detection(2000)
    benchmark_conflict_detection(5000)
