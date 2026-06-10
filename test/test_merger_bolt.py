
import time
import random
import string
import sys
import os
import unittest

# Add current directory to sys.path to import mergin_workflow_manager
sys.path.append(os.getcwd())

from mergin_workflow_manager import MerginDataMerger

class MockPostgREST:
    def __init__(self):
        self.calls = {'insert': 0, 'update': 0, 'delete': 0}
        self.items_affected = {'insert': 0, 'update': 0, 'delete': 0}
        self.last_insert_upsert = None

    def insert(self, table, data, upsert=False):
        self.calls['insert'] += 1
        self.last_insert_upsert = upsert
        if isinstance(data, list):
            self.items_affected['insert'] += len(data)
        else:
            self.items_affected['insert'] += 1

    def update(self, table, data, filters):
        self.calls['update'] += 1
        self.items_affected['update'] += 1

    def delete(self, table, filters):
        self.calls['delete'] += 1
        # Extract count from 'in.' filter if possible
        filter_val = next(iter(filters.values()))
        if filter_val.startswith('in.'):
            ids = filter_val.split('(')[1].split(')')[0].split(',')
            if ids == ['']:
                pass
            else:
                self.items_affected['delete'] += len(ids)
        else:
            self.items_affected['delete'] += 1

def generate_data(n):
    return [{'id': i, 'name': ''.join(random.choices(string.ascii_letters, k=10))} for i in range(n)]

class TestMergerBolt(unittest.TestCase):
    def test_performance_and_correctness(self):
        n = 2000
        original = generate_data(n)
        collected = [dict(item) for item in original] # Deep copy dicts

        # Modify 200 items
        for i in range(0, 200):
            collected[i]['name'] += "_mod"

        # Add 200 items
        for i in range(n, n + 200):
            collected.append({'id': i, 'name': 'new'})

        # Original has 200 extra items that were "deleted" in collected
        # (original_extended has items -200 to n-1, collected has 0 to n+199)
        # So deleted are -200 to -1 (200 items)
        original_extended = [{'id': i, 'name': 'to_del'} for i in range(-200, 0)] + original

        mock_api = MockPostgREST()
        merger = MerginDataMerger(mock_api)

        # Measure detect_conflicts
        start = time.time()
        conflicts = merger.detect_conflicts(original_extended, collected)
        detect_time = time.time() - start

        # Verify conflicts
        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        added = next(c for c in conflicts if c['type'] == 'added')
        modified = [c for c in conflicts if c['type'] == 'modified']

        self.assertEqual(deleted['count'], 200)
        self.assertEqual(added['count'], 200)
        self.assertEqual(len(modified), 200)

        # Measure merge
        start = time.time()
        merger.merge("test_table", original_extended, collected)
        merge_time = time.time() - start

        # Verify API calls (Batching)
        self.assertEqual(mock_api.calls['insert'], 1)
        self.assertTrue(mock_api.last_insert_upsert)
        self.assertEqual(mock_api.calls['delete'], 1)
        self.assertEqual(mock_api.calls['update'], 0) # Should be 0 because of UPSERT

        # Verify affected items
        self.assertEqual(mock_api.items_affected['insert'], 400) # 200 added + 200 modified
        self.assertEqual(mock_api.items_affected['delete'], 200)

        print(f"\nOptimization Results (N={n}):")
        print(f"  detect_conflicts time: {detect_time:.4f}s")
        print(f"  merge time:            {merge_time:.4f}s")
        print(f"  API calls reduced from {200+200+1} to {mock_api.calls['insert'] + mock_api.calls['delete']}")

if __name__ == "__main__":
    unittest.main()
