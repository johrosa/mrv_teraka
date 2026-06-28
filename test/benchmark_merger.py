
import time
import random
import uuid
import sys
import os

# Add current directory to sys.path to import mergin_workflow_manager
sys.path.append(os.getcwd())

from mergin_workflow_manager import MerginDataMerger

class MockPostgREST:
    def insert(self, table, data, upsert=False): pass
    def update(self, table, data, filters): pass
    def delete(self, table, filters): pass

def generate_data(count):
    data = []
    for i in range(count):
        data.append({
            'id': str(uuid.uuid4()),
            'name': f'Name {i}',
            'value': random.randint(0, 1000),
            'last_sync': time.time()
        })
    return data

def benchmark():
    counts = [100, 500, 1000, 2000]
    merger = MerginDataMerger(MockPostgREST())

    print(f"{'Count':>10} | {'Detect Conflicts (s)':>20}")
    print("-" * 35)

    for count in counts:
        original = generate_data(count)
        collected = [dict(item) for item in original]

        # Modify 10%
        for i in range(count // 10):
            collected[i]['value'] = random.randint(1001, 2000)

        # Add 10%
        collected.extend(generate_data(count // 10))

        # Delete 10% (from original, so not in collected)
        collected = collected[count // 10:]

        start = time.time()
        merger.detect_conflicts(original, collected)
        end = time.time()

        print(f"{count:10} | {end - start:20.6f}")

if __name__ == "__main__":
    benchmark()
