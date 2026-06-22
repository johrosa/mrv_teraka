
import time
import random
import sys
import os

# Add current directory to sys.path to import mergin_workflow_manager
sys.path.append(os.getcwd())

from mergin_workflow_manager import MerginDataMerger

class MockPostgrest:
    def insert(self, *args, **kwargs): pass
    def update(self, *args, **kwargs): pass
    def delete(self, *args, **kwargs): pass

def generate_data(count, changes_ratio=0.1, additions_ratio=0.05, deletions_ratio=0.05):
    original = []
    for i in range(count):
        original.append({
            'id': i,
            'name': f'Name {i}',
            'value': random.random(),
            'status': 'active'
        })

    collected = []
    # Keep some, modify some
    for item in original:
        if random.random() > deletions_ratio:
            new_item = item.copy()
            if random.random() < changes_ratio:
                new_item['value'] = random.random()
                new_item['name'] = f"Modified {item['id']}"
            collected.append(new_item)

    # Add some
    for i in range(count, count + int(count * additions_ratio)):
        collected.append({
            'id': i,
            'name': f'New Name {i}',
            'value': random.random(),
            'status': 'new'
        })

    return original, collected

def benchmark():
    counts = [100, 500, 1000, 2000, 5000]
    merger = MerginDataMerger(MockPostgrest())

    print(f"{'Count':>10} | {'Time (s)':>10}")
    print("-" * 25)

    for count in counts:
        original, collected = generate_data(count)

        start_time = time.time()
        conflicts = merger.detect_conflicts(original, collected)
        end_time = time.time()

        print(f"{count:10} | {end_time - start_time:10.4f}")

if __name__ == "__main__":
    benchmark()
