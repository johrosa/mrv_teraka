
import time
import random
import sys
import os

# Add current directory to path so we can import our modules
sys.path.append(os.getcwd())

from mergin_workflow_manager import MerginDataMerger

def generate_data(count, conflict_rate=0.1):
    original = []
    collected = []

    for i in range(count):
        item = {
            'id': i,
            'name': f'Item {i}',
            'value': random.random(),
            'attribute': f'Attr {i}'
        }
        original.append(item)

        # Decide if it stays, gets modified, or deleted
        r = random.random()
        if r < conflict_rate:
            # Modified
            mod_item = item.copy()
            mod_item['value'] = random.random()
            collected.append(mod_item)
        elif r < 1.0 - conflict_rate:
            # Stays the same
            collected.append(item.copy())
        # else: Deleted (not added to collected)

    # Add some new items
    for i in range(count, count + int(count * conflict_rate)):
        item = {
            'id': i,
            'name': f'New Item {i}',
            'value': random.random(),
            'attribute': f'Attr {i}'
        }
        collected.append(item)

    return original, collected

def benchmark():
    counts = [100, 500, 1000, 2000, 5000]
    merger = MerginDataMerger(None) # No client needed for detect_conflicts

    print(f"{'Count':>10} | {'Time (s)':>10}")
    print("-" * 25)

    for count in counts:
        original, collected = generate_data(count)

        start_time = time.time()
        merger.detect_conflicts(original, collected)
        end_time = time.time()

        duration = end_time - start_time
        print(f"{count:10} | {duration:10.4f}")

if __name__ == "__main__":
    benchmark()
