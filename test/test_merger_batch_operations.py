
import unittest
from unittest.mock import MagicMock, call
from mergin_workflow_manager import MerginDataMerger

class TestMergerBatchOperations(unittest.TestCase):
    def setUp(self):
        self.mock_postgrest = MagicMock()
        self.merger = MerginDataMerger(self.mock_postgrest)

    def test_merge_calls_batch_upsert_and_delete(self):
        table = "test_table"
        pk_field = "id"

        # Original data: [1, 2, 3]
        original = [
            {"id": 1, "val": "a"},
            {"id": 2, "val": "b"},
            {"id": 3, "val": "c"}
        ]

        # Collected data:
        # - 1: modified
        # - 2: kept
        # - 3: deleted (missing)
        # - 4: added
        collected = [
            {"id": 1, "val": "a_mod"},
            {"id": 2, "val": "b"},
            {"id": 4, "val": "d"}
        ]

        results = self.merger.merge(table, original, collected, strategy='merge', pk_field=pk_field)

        # Verify batch UPSERT: should include ID 1 (modified) and ID 4 (added)
        self.mock_postgrest.insert.assert_called_once()
        args, kwargs = self.mock_postgrest.insert.call_args
        self.assertEqual(args[0], table)
        upserted_items = args[1]
        self.assertEqual(len(upserted_items), 2)
        upserted_ids = {item['id'] for item in upserted_items}
        self.assertEqual(upserted_ids, {1, 4})
        self.assertTrue(kwargs.get('upsert'))

        # Verify batch DELETE: should include ID 3
        self.mock_postgrest.delete.assert_called_once_with(table, {pk_field: "in.(3)"})

        # Verify result actions
        actions = results['actions']
        action_types = [a['type'] for a in actions]
        self.assertIn('updated', action_types)
        self.assertIn('inserted', action_types)
        self.assertIn('deleted', action_types)

    def test_merge_chunked_delete(self):
        table = "test_table"
        pk_field = "id"

        # Generate 250 original items, collect 0 (all deleted)
        original = [{"id": i} for i in range(250)]
        collected = []

        self.merger.merge(table, original, collected, strategy='merge', pk_field=pk_field)

        # Should call delete twice (chunk size 200)
        self.assertEqual(self.mock_postgrest.delete.call_count, 2)

        # Check first chunk
        chunk1_ids = ",".join(map(str, range(200)))
        self.mock_postgrest.delete.assert_any_call(table, {pk_field: f"in.({chunk1_ids})"})

        # Check second chunk
        chunk2_ids = ",".join(map(str, range(200, 250)))
        self.mock_postgrest.delete.assert_any_call(table, {pk_field: f"in.({chunk2_ids})"})

if __name__ == "__main__":
    unittest.main()
