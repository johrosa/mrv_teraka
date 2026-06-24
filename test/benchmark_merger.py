
import sys
import time
import unittest
from unittest.mock import MagicMock

# Add current directory to sys.path to import mergin_workflow_manager
sys.path.append('.')

from mergin_workflow_manager import MerginDataMerger

class BenchmarkMerger(unittest.TestCase):
    def setUp(self):
        self.mock_postgrest = MagicMock()
        self.merger = MerginDataMerger(self.mock_postgrest)

    def test_detect_conflicts_performance(self):
        # Create 2000 records
        count = 2000
        original = [{'id': i, 'val': f'val_{i}', 'other': 'data'} for i in range(count)]
        collected = [{'id': i, 'val': f'val_{i}', 'other': 'data'} for i in range(count)]

        # Modify some
        for i in range(0, count, 10):
            collected[i]['val'] = f'modified_{i}'

        start_time = time.time()
        conflicts = self.merger.detect_conflicts(original, collected)
        end_time = time.time()

        duration = end_time - start_time
        print(f"\nDetect conflicts (2000 items) took: {duration:.4f} seconds")

    def test_merge_performance_batching(self):
        # Create 1000 records
        count = 1000
        original = [{'id': i, 'val': f'val_{i}'} for i in range(count)]
        # Add 100, modify 100, delete 100
        collected = [{'id': i, 'val': f'val_{i}'} for i in range(100, 1000)] # deleted 0-99
        for i in range(100, 200): # modified 100-199
            collected[i-100]['val'] = f'mod_{i}'
        for i in range(count, count + 100): # added 1000-1099
            collected.append({'id': i, 'val': f'new_{i}'})

        # Reset mock
        self.mock_postgrest.reset_mock()

        start_time = time.time()
        results = self.merger.merge('test_table', original, collected)
        end_time = time.time()

        # Count API calls
        insert_calls = [c for c in self.mock_postgrest.method_calls if c[0] == 'insert']
        update_calls = [c for c in self.mock_postgrest.method_calls if c[0] == 'update']
        delete_calls = [c for c in self.mock_postgrest.method_calls if c[0] == 'delete']

        print(f"Merge API calls:")
        print(f"  Insert calls: {len(insert_calls)}")
        print(f"  Update calls: {len(update_calls)}")
        print(f"  Delete calls: {len(delete_calls)}")
        print(f"  Total calls: {len(self.mock_postgrest.method_calls)}")
        print(f"Merge duration: {end_time - start_time:.4f} seconds")

if __name__ == '__main__':
    unittest.main()
