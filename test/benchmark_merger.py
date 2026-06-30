import time
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from mergin_workflow_manager import MerginDataMerger

def benchmark():
    # Create large datasets
    num_records = 5000
    original = [{'id': i, 'val': f'original_{i}'} for i in range(num_records)]
    collected = [{'id': i, 'val': f'original_{i}'} for i in range(num_records)]

    # Introduce some modifications
    for i in range(0, num_records, 10):
        collected[i]['val'] = f'modified_{i}'

    merger = MerginDataMerger(None) # Mock client not needed for detect_conflicts

    start_time = time.time()
    conflicts = merger.detect_conflicts(original, collected)
    end_time = time.time()

    print(f"Time taken for {num_records} records: {end_time - start_time:.4f} seconds")

if __name__ == "__main__":
    benchmark()
