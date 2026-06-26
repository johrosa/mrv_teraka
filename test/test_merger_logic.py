# -*- coding: utf-8 -*-
import unittest
from unittest.mock import MagicMock
import sys
import os

# Add current directory to path to import local modules
sys.path.append(os.getcwd())

from mergin_workflow_manager import MerginDataMerger

class TestMergerLogic(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()
        self.merger = MerginDataMerger(self.mock_client)
        self.pk = 'id'
        self.table = 'test_table'

    def test_detect_conflicts(self):
        original = [
            {'id': 1, 'val': 'a'},
            {'id': 2, 'val': 'b'}
        ]
        collected = [
            {'id': 1, 'val': 'a_mod'}, # Modified
            {'id': 3, 'val': 'c'}      # Added
            # id 2 is deleted
        ]

        conflicts = self.merger.detect_conflicts(original, collected, pk_field=self.pk)

        types = {c['type'] for c in conflicts}
        self.assertIn('deleted', types)
        self.assertIn('added', types)
        self.assertIn('modified', types)

        for c in conflicts:
            if c['type'] == 'deleted':
                self.assertEqual(c['ids'], [2])
            if c['type'] == 'added':
                self.assertEqual(c['ids'], [3])
            if c['type'] == 'modified':
                self.assertEqual(c['id'], 1)
                self.assertEqual(c['original']['val'], 'a')
                self.assertEqual(c['collected']['val'], 'a_mod')

    def test_merge_batch_calls(self):
        original = [{'id': 1, 'val': 'a'}, {'id': 2, 'val': 'b'}]
        collected = [
            {'id': 1, 'val': 'a_mod'}, # Modified
            {'id': 3, 'val': 'c'}      # Added
        ]

        results = self.merger.merge(self.table, original, collected, strategy='merge', pk_field=self.pk)

        # Verify batch UPSERT call
        # Should be called once with both id 1 and id 3
        self.mock_client.insert.assert_called_once()
        args, kwargs = self.mock_client.insert.call_args
        self.assertEqual(args[0], self.table)
        self.assertEqual(len(args[1]), 2)
        self.assertTrue(kwargs.get('upsert'))

        # Verify results maintain backward compatibility
        action_types = {a['type'] for a in results['actions']}
        self.assertIn('inserted', action_types)
        self.assertIn('updated', action_types)
        self.assertNotIn('upserted', action_types)

        # Verify batch DELETE call
        # Should be called once for id 2
        self.mock_client.delete.assert_called_once()
        args, kwargs = self.mock_client.delete.call_args
        self.assertEqual(args[0], self.table)
        self.assertIn('in.(2)', args[1][self.pk])

    def test_batch_delete_quoting(self):
        original = [{'id': 'uuid-1'}]
        collected = [] # Delete uuid-1

        self.merger.merge(self.table, original, collected, strategy='merge', pk_field=self.pk)

        self.mock_client.delete.assert_called_once()
        args, _ = self.mock_client.delete.call_args
        self.assertEqual(args[1][self.pk], 'in.("uuid-1")')

if __name__ == '__main__':
    unittest.main()
