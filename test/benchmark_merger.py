import time
import random
import sys
import os

# Add current directory to path so we can import mergin_workflow_manager
sys.path.append(os.getcwd())

from mergin_workflow_manager import MerginDataMerger

class MockPostgrest:
    def insert(self, *args, **kwargs): pass
    def update(self, *args, **kwargs): pass
    def delete(self, *args, **kwargs): pass

def generate_data(size, modifications=0.1, additions=0.1, deletions=0.1):
    original = []
    for i in range(size):
        original.append({
            'id': i,
            'name': f'Name {i}',
            'value': random.randint(0, 1000)
        })

    collected = []
    # Keep most, but some deleted
    for item in original:
        if random.random() > deletions:
            # Modify some
            new_item = item.copy()
            if random.random() < modifications / (1 - deletions):
                new_item['value'] = random.randint(1001, 2000)
            collected.append(new_item)

    # Add new ones
    current_max_id = size
    for i in range(int(size * additions)):
        collected.append({
            'id': current_max_id + i,
            'name': f'New Name {i}',
            'value': random.randint(0, 1000)
        })

    return original, collected

def benchmark():
    merger = MerginDataMerger(MockPostgrest())

    sizes = [100, 500, 1000, 2000]
    for size in sizes:
        original, collected = generate_data(size)

        start_time = time.time()
        conflicts = merger.detect_conflicts(original, collected)
        end_time = time.time()

        print(f"Size: {size}, Time: {end_time - start_time:.4f}s, Conflicts: {len(conflicts)}")

if __name__ == "__main__":
    benchmark()
