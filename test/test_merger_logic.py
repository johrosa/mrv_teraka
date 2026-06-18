# -*- coding: utf-8 -*-
import unittest
from unittest.mock import MagicMock
from mergin_workflow_manager import MerginDataMerger

class TestMerginDataMerger(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()
        self.merger = MerginDataMerger(self.mock_client)

    def test_detect_conflicts_added(self):
        original = [{"id": 1, "name": "A"}]
        collected = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
        conflicts = self.merger.detect_conflicts(original, collected)

        added = [c for c in conflicts if c['type'] == 'added']
        self.assertEqual(len(added), 1)
        self.assertIn(2, added[0]['ids'])

    def test_detect_conflicts_deleted(self):
        original = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
        collected = [{"id": 1, "name": "A"}]
        conflicts = self.merger.detect_conflicts(original, collected)

        deleted = [c for c in conflicts if c['type'] == 'deleted']
        self.assertEqual(len(deleted), 1)
        self.assertIn(2, deleted[0]['ids'])

    def test_detect_conflicts_modified(self):
        original = [{"id": 1, "name": "A"}]
        collected = [{"id": 1, "name": "A_mod"}]
        conflicts = self.merger.detect_conflicts(original, collected)

        modified = [c for c in conflicts if c['type'] == 'modified']
        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 1)

    def test_merge_batch_calls(self):
        original = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
        collected = [{"id": 1, "name": "A_mod"}, {"id": 3, "name": "C"}]
        # Actions:
        # ID 1: update
        # ID 2: delete
        # ID 3: insert

        self.merger.merge("table", original, collected, strategy='merge')

        # Should call insert once for [ID 1, ID 3] (UPSERT)
        self.assertEqual(self.mock_client.insert.call_count, 1)
        args, kwargs = self.mock_client.insert.call_args
        self.assertEqual(len(args[1]), 2)
        self.assertTrue(kwargs.get('upsert'))

        # Should call delete once for ID 2
        self.assertEqual(self.mock_client.delete.call_count, 1)
        args, kwargs = self.mock_client.delete.call_args
        self.assertEqual(args[1]['id'], 'in.(2)')

if __name__ == "__main__":
    unittest.main()
