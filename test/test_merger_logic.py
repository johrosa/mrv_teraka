import unittest
from unittest.mock import MagicMock
import datetime

from mergin_workflow_manager import MerginDataMerger

class TestMergerLogic(unittest.TestCase):
    def setUp(self):
        self.mock_postgrest = MagicMock()
        self.merger = MerginDataMerger(self.mock_postgrest)

    def test_detect_conflicts_added(self):
        original = [{"id": 1, "name": "A"}]
        collected = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
        conflicts = self.merger.detect_conflicts(original, collected)

        added = next(c for c in conflicts if c['type'] == 'added')
        self.assertEqual(added['count'], 1)
        self.assertEqual(added['ids'], ["2"])

    def test_detect_conflicts_deleted(self):
        original = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
        collected = [{"id": 1, "name": "A"}]
        conflicts = self.merger.detect_conflicts(original, collected)

        deleted = next(c for c in conflicts if c['type'] == 'deleted')
        self.assertEqual(deleted['count'], 1)
        self.assertEqual(deleted['ids'], ["2"])

    def test_detect_conflicts_modified(self):
        original = [{"id": 1, "name": "A"}]
        collected = [{"id": 1, "name": "A_mod"}]
        conflicts = self.merger.detect_conflicts(original, collected)

        modified = [c for c in conflicts if c['type'] == 'modified']
        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]['id'], 1)
        self.assertEqual(modified[0]['collected']['name'], "A_mod")

    def test_merge_calls_batch_upsert(self):
        original = [{"id": 1, "name": "A"}]
        collected = [{"id": 1, "name": "A_mod"}, {"id": 2, "name": "B"}]

        self.merger.merge("table", original, collected)

        # Check that insert was called once with both items
        self.assertEqual(self.mock_postgrest.insert.call_count, 1)
        args, kwargs = self.mock_postgrest.insert.call_args
        self.assertEqual(args[0], "table")
        self.assertEqual(len(args[1]), 2)
        self.assertTrue(kwargs.get('upsert'))

    def test_merge_calls_batch_delete(self):
        original = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
        collected = []

        self.merger.merge("table", original, collected)

        # Check that delete was called once with in. operator
        self.assertEqual(self.mock_postgrest.delete.call_count, 1)
        args, kwargs = self.mock_postgrest.delete.call_args
        self.assertEqual(args[0], "table")
        filters = args[1]
        self.assertIn("id", filters)
        self.assertTrue(filters["id"].startswith("in.("))
        self.assertIn("1", filters["id"])
        self.assertIn("2", filters["id"])

if __name__ == '__main__':
    unittest.main()
