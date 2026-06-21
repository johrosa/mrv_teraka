# -*- coding: utf-8 -*-
import time
import unittest
from unittest.mock import MagicMock
from mergin_workflow_manager import MerginDataMerger

class BenchmarkMerger(unittest.TestCase):
    def setUp(self):
        self.mock_postgrest = MagicMock()
        self.merger = MerginDataMerger(self.mock_postgrest)

    def generate_data(self, count):
        original = [{'id': i, 'val': f'orig_{i}', 'other': 'const'} for i in range(count)]
        # Modify half, keep half
        collected = []
        for i in range(count):
            if i % 2 == 0:
                # Modify
                collected.append({'id': i, 'val': f'coll_{i}', 'other': 'const'})
            else:
                # Keep
                collected.append({'id': i, 'val': f'orig_{i}', 'other': 'const'})

        # Add some new ones
        for i in range(count, count + int(count * 0.1)):
            collected.append({'id': i, 'val': f'new_{i}', 'other': 'new'})

        return original, collected

    def test_benchmark_detect_conflicts(self):
        counts = [100, 1000, 5000]
        print("\nBenchmarking detect_conflicts:")
        for count in counts:
            original, collected = self.generate_data(count)
            start = time.time()
            conflicts = self.merger.detect_conflicts(original, collected)
            end = time.time()
            print(f"Count: {count}, Time: {end - start:.4f}s, Conflicts: {len(conflicts)}")

    def test_benchmark_merge(self):
        # Only testing logic, mock will handle API calls
        count = 1000
        original, collected = self.generate_data(count)

        print(f"\nBenchmarking merge (logic + mock calls) for {count} records:")
        start = time.time()
        self.merger.merge('test_table', original, collected)
        end = time.time()
        print(f"Time: {end - start:.4f}s")
        print(f"Insert calls: {self.mock_postgrest.insert.call_count}")
        print(f"Update calls: {self.mock_postgrest.update.call_count}")
        print(f"Delete calls: {self.mock_postgrest.delete.call_count}")

if __name__ == '__main__':
    unittest.main()
