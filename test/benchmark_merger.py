import time
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from mergin_workflow_manager import MerginDataMerger

def benchmark():
    size = 2000
    original = [{'id': i, 'val': f'orig_{i}'} for i in range(size)]
    collected = [{'id': i, 'val': f'orig_{i}'} for i in range(size)]
    # Modify some
    for i in range(0, size, 10):
        collected[i]['val'] = f'mod_{i}'

    # Add some
    for i in range(size, size + 100):
        collected.append({'id': i, 'val': f'new_{i}'})

    merger = MerginDataMerger(None)

    print(f"Benchmarking detect_conflicts with {size} items...")
    start = time.time()
    conflicts = merger.detect_conflicts(original, collected)
    end = time.time()
    print(f"Time taken: {end - start:.4f}s")
    print(f"Conflicts found: {len(conflicts)}")

if __name__ == "__main__":
    benchmark()
