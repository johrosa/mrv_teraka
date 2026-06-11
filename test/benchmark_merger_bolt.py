# -*- coding: utf-8 -*-
import time
import unittest
from unittest.mock import MagicMock
import sys
import os

# Add the plugin directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mergin_workflow_manager import MerginDataMerger

class BenchmarkMerger(unittest.TestCase):
    def setUp(self):
        self.mock_postgrest = MagicMock()
        self.merger = MerginDataMerger(self.mock_postgrest)
        self.num_records = 1000

        # Original data
        self.original = [
            {'id': i, 'name': f'item_{i}', 'value': i * 10}
            for i in range(self.num_records)
        ]

        # Collected data:
        # - keep 800 (unchanged)
        # - modify 100
        # - add 100
        # - delete 100 (by not including them)

        self.collected = []
        # Unchanged (0 to 799)
        for i in range(800):
            self.collected.append(self.original[i].copy())

        # Modified (800 to 899)
        for i in range(800, 900):
            item = self.original[i].copy()
            item['value'] = item['value'] + 1
            self.collected.append(item)

        # Added (1000 to 1099)
        for i in range(self.num_records, self.num_records + 100):
            self.collected.append({'id': i, 'name': f'item_{i}', 'value': i * 10})

        # 900 to 999 are deleted (not in collected)

    def test_benchmark_detect_conflicts(self):
        print(f"\nBenchmarking detect_conflicts with {self.num_records} records...")
        start_time = time.time()
        conflicts = self.merger.detect_conflicts(self.original, self.collected)
        end_time = time.time()
        duration = end_time - start_time
        print(f"detect_conflicts took {duration:.4f} seconds")

        # Basic validation of results
        counts = {'added': 0, 'deleted': 0, 'modified': 0}
        for c in conflicts:
            if c['type'] == 'modified':
                counts['modified'] += 1
            else:
                counts[c['type']] = c['count']

        self.assertEqual(counts['added'], 100)
        self.assertEqual(counts['deleted'], 100)
        self.assertEqual(counts['modified'], 100)

    def test_benchmark_merge(self):
        print(f"\nBenchmarking merge with {self.num_records} records...")
        start_time = time.time()
        # Mocking prompt return value
        import qgis.PyQt.QtWidgets
        original_msgbox = qgis.PyQt.QtWidgets.QMessageBox.question
        qgis.PyQt.QtWidgets.QMessageBox.question = MagicMock(return_value=qgis.PyQt.QtWidgets.QMessageBox.Yes)

        # Mocking information msgbox
        original_info = qgis.PyQt.QtWidgets.QMessageBox.information
        qgis.PyQt.QtWidgets.QMessageBox.information = MagicMock()

        try:
            results = self.merger.merge('test_table', self.original, self.collected)
        finally:
            qgis.PyQt.QtWidgets.QMessageBox.question = original_msgbox
            qgis.PyQt.QtWidgets.QMessageBox.information = original_info

        end_time = time.time()
        duration = end_time - start_time
        print(f"merge took {duration:.4f} seconds")

        # Count API calls
        insert_calls = [c for c in self.mock_postgrest.method_calls if c[0] == 'insert']
        update_calls = [c for c in self.mock_postgrest.method_calls if c[0] == 'update']
        delete_calls = [c for c in self.mock_postgrest.method_calls if c[0] == 'delete']

        print(f"API calls: insert={len(insert_calls)}, update={len(update_calls)}, delete={len(delete_calls)}")

if __name__ == '__main__':
    unittest.main()
