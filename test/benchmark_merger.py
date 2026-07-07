
import time
import random
import string
from mergin_workflow_manager import MerginDataMerger

def generate_data(count):
    data = []
    for i in range(count):
        data.append({
            'id': i,
            'name': ''.join(random.choices(string.ascii_letters, k=10)),
            'value': random.randint(0, 1000)
        })
    return data

def run_benchmark(n):
    original = generate_data(n)
    collected = generate_data(n)

    # Introduce some modifications
    for i in range(0, n, 10):
        collected[i]['value'] = 9999

    merger = MerginDataMerger(None)

    start_time = time.time()
    conflicts = merger.detect_conflicts(original, collected)
    end_time = time.time()

    print(f"Benchmark with {n} records:")
    print(f"Time taken: {end_time - start_time:.4f} seconds")
    print(f"Conflicts detected: {len(conflicts)}")

if __name__ == "__main__":
    run_benchmark(1000)
    run_benchmark(5000)
