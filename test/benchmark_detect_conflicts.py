import time
import random
import uuid
from mergin_workflow_manager import MerginDataMerger

class MockPostgrest:
    def insert(self, table, data, upsert=False): pass
    def update(self, table, data, filters): pass
    def delete(self, table, filters): pass

def generate_data(count, modified_count=100, deleted_count=50, added_count=50):
    original = []
    for i in range(count):
        item_id = str(uuid.uuid4())
        original.append({'id': item_id, 'name': f'item_{i}', 'value': random.random()})

    collected = [dict(item) for item in original]

    # Modifications
    for i in range(min(modified_count, count)):
        collected[i]['value'] = random.random()

    # Deletions (remove from collected)
    for _ in range(min(deleted_count, len(collected))):
        collected.pop()

    # Additions
    for i in range(added_count):
        collected.append({'id': str(uuid.uuid4()), 'name': f'new_{i}', 'value': random.random()})

    return original, collected

def benchmark():
    counts = [100, 500, 1000, 2000]
    merger = MerginDataMerger(MockPostgrest())

    print(f"{'Count':<10} | {'Time (s)':<10}")
    print("-" * 25)

    for count in counts:
        original, collected = generate_data(count,
                                          modified_count=count//10,
                                          deleted_count=count//20,
                                          added_count=count//20)

        start = time.time()
        merger.detect_conflicts(original, collected)
        end = time.time()

        print(f"{count:<10} | {end - start:.6f}")

if __name__ == "__main__":
    benchmark()
