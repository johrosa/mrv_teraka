"""Configuration et utilisation des paramètres, sans runtime QGIS ni réseau."""

import ast
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from plugin_config import PluginConfig, load_config
from config_postgrest import normalize_layer_mapping
from test_connection_session import client_module


ROOT = Path(__file__).resolve().parents[1]


def migration_methods(config):
    tree = ast.parse((ROOT / 'mrv_teraka.py').read_text(encoding='utf-8'))
    plugin = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'MrvTeraka')
    names = {
        '_do_migration_task', '_insert_rows_with_diagnostics', '_prepare_api_write_rows',
        '_migration_error_signature', '_is_probably_row_level_postgrest_error',
        '_prepare_migration_rows', 'conflict_field_for_mapping', 'mapping_columns',
    }
    plugin.body = [node for node in plugin.body if isinstance(node, ast.FunctionDef) and node.name in names]
    namespace = {'CONFIG': config, 'PostgRESTError': client_module.PostgRESTError, 're': re}
    exec(compile(ast.Module(body=[plugin], type_ignores=[]), str(ROOT / 'mrv_teraka.py'), 'exec'), namespace)
    return namespace['MrvTeraka']


class PluginConfigTests(unittest.TestCase):
    def load_text(self, content):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'config.ini'
            path.write_text(content, encoding='utf-8')
            return load_config(path)

    def test_missing_file_and_partial_config_use_defaults(self):
        with TemporaryDirectory() as directory:
            self.assertEqual(load_config(Path(directory) / 'missing.ini'), PluginConfig())
        self.assertEqual(self.load_text('[migration]\nbatch_size = 200\n'),
                         PluginConfig(migration_batch_size=200))

    def test_invalid_numbers_fall_back_without_losing_valid_settings(self):
        for value in ('0', '-1', 'abc', '1.5', 'true', ''):
            with self.subTest(value=value), self.assertLogs('plugin_config', level='WARNING'):
                config = self.load_text(
                    f'[migration]\nbatch_size = {value}\n[postgrest]\nrequest_timeout = 45\n'
                )
                self.assertEqual(config, PluginConfig(request_timeout=45))

    def test_malformed_file_uses_defaults(self):
        with self.assertLogs('plugin_config', level='WARNING'):
            self.assertEqual(self.load_text('invalid ini'), PluginConfig())

    def test_all_settings_can_be_overridden(self):
        config = self.load_text(
            '[migration]\nbatch_size=2\nrepeated_error_limit=3\n'
            '[postgrest]\npage_size=4\nrequest_timeout=45\nconnection_timeout=6\n'
            'auth_timeout=25\nconnection_check_interval=90\n'
        )
        self.assertEqual(config, PluginConfig(2, 3, 4, 45, 6, 25, 90))

    def test_migration_sends_all_rows_in_configured_batches(self):
        plugin = migration_methods(PluginConfig(migration_batch_size=2))
        task = Mock()
        task.isCanceled.return_value = False
        client = Mock()
        rows = [{'id': value} for value in range(5)]
        result = plugin._do_migration_task(task, [('Test', 'test', 'id', rows)], client)
        batches = [call.args[1] for call in client.insert.call_args_list]
        self.assertEqual([len(batch) for batch in batches], [2, 2, 1])
        self.assertEqual([row for batch in batches for row in batch], rows)
        self.assertEqual(result['errors_count'], 0)
        self.assertEqual(result['status'], 'completed')

    def test_configured_error_threshold_limits_recursive_diagnostics(self):
        plugin = migration_methods(PluginConfig(migration_repeated_error_limit=1))
        plugin._format_postgrest_error = Mock(return_value='invalid row')
        client = Mock()
        client.insert.side_effect = client_module.PostgRESTError(
            400, 'Bad Request', '', 'POST', 'test', '', {'code': '23502', 'message': 'required'},
        )
        results = []
        self.assertEqual(plugin._insert_rows_with_diagnostics(
            client, 'test', [{'id': value} for value in range(4)], 'id', 'Test', 0, results,
        ), (0, 4))
        self.assertEqual(client.insert.call_count, 5)
        self.assertTrue(any('diagnostic limité' in line for line in results))

    def test_commune_uses_unique_code_without_changing_primary_key(self):
        plugin = migration_methods(PluginConfig())()
        for endpoint in ('commune', 'communes'):
            with self.subTest(endpoint=endpoint):
                mapping = normalize_layer_mapping('Limite_Commune', {
                    'endpoint': endpoint, 'pk_field': 'id',
                    'columns': ['id', 'uuid_com', 'c_com', 'geom'],
                })
                self.assertEqual(mapping['pk_field'], 'id')
                self.assertEqual(plugin.conflict_field_for_mapping(mapping), 'c_com')
        self.assertEqual(plugin.conflict_field_for_mapping({
            'endpoint': 'membre', 'columns': ['id', 'uuid_membre', 'c_com'],
        }), 'uuid_membre')
        self.assertEqual(plugin.conflict_field_for_mapping({
            'endpoint': 'other', 'columns': ['id', 'c_com'],
        }), 'id')

    def test_explicit_conflict_field_survives_mapping_normalization(self):
        plugin = migration_methods(PluginConfig())()
        mapping = normalize_layer_mapping('Limite_Commune', {
            'endpoint': 'commune', 'columns': ['id', 'c_com'], 'conflict_field': 'id',
        })
        self.assertEqual(plugin.conflict_field_for_mapping(mapping), 'id')

    def test_commune_migration_preserves_server_identity(self):
        plugin = migration_methods(PluginConfig(migration_batch_size=2))
        task = Mock()
        task.isCanceled.return_value = False
        client = Mock()
        client.select.return_value = [{'c_com': 515301, 'uuid_com': 'server-uuid'}]
        rows = [
            {'id': 1, 'c_com': 515301, 'uuid_com': 'local-uuid', 'commune': 'Updated'},
            {'id': 2, 'c_com': 515302, 'uuid_com': 'new-uuid', 'commune': 'New'},
        ]
        result = plugin._do_migration_task(task, [('Limite_Commune', 'commune', 'c_com', rows)], client)
        sent = client.insert.call_args.args[1]
        self.assertEqual(sent, [
            {'c_com': 515301, 'uuid_com': 'server-uuid', 'commune': 'Updated'},
            {'c_com': 515302, 'uuid_com': 'new-uuid', 'commune': 'New'},
        ])
        self.assertEqual(client.insert.call_args.kwargs['on_conflict'], 'c_com')
        self.assertTrue(client.insert.call_args.kwargs['upsert'])
        self.assertEqual(result['errors_count'], 0)
        self.assertEqual(rows[0]['uuid_com'], 'local-uuid')
        self.assertEqual(rows[0]['id'], 1)

    def test_no_write_when_server_identity_lookup_fails(self):
        plugin = migration_methods(PluginConfig())
        task = Mock()
        task.isCanceled.return_value = False
        client = Mock()
        client.select.side_effect = RuntimeError('Read timed out')
        result = plugin._do_migration_task(task, [
            ('Commune', 'commune', 'c_com', [{'id': 1, 'c_com': 515301, 'uuid_com': 'local'}]),
        ], client)
        client.insert.assert_not_called()
        self.assertEqual(result['errors_count'], 1)

    def test_unique_conflict_does_not_discard_other_valid_rows(self):
        plugin = migration_methods(PluginConfig())
        plugin._format_postgrest_error = Mock(return_value='duplicate code')
        client = Mock()
        successful = []

        def insert(endpoint, rows, **kwargs):
            if any(row['id'] == 2 for row in rows):
                raise client_module.PostgRESTError(
                    409, 'Conflict', '', 'POST', endpoint, '',
                    {'code': '23505', 'message': 'duplicate code'},
                )
            successful.extend(row['id'] for row in rows)

        client.insert.side_effect = insert
        self.assertEqual(plugin._insert_rows_with_diagnostics(
            client, 'test', [{'id': value} for value in range(1, 5)], 'id', 'Test', 0, [],
        ), (3, 1))
        self.assertEqual(successful, [1, 3, 4])

    def test_error_counter_counts_failed_requests_instead_of_rows(self):
        plugin = migration_methods(PluginConfig(migration_repeated_error_limit=2))
        plugin._format_postgrest_error = Mock(return_value='permission denied')
        client = Mock()
        client.insert.side_effect = client_module.PostgRESTError(
            403, 'Forbidden', '', 'POST', 'test', '', {'code': '42501', 'message': 'permission denied'},
        )
        state, results = {}, []
        for _ in range(3):
            plugin._insert_rows_with_diagnostics(
                client, 'test', [{'id': value} for value in range(100)], 'id', 'Test', 0, results,
                error_state=state,
            )
        self.assertEqual(list(state.values()), [3])
        self.assertIn('3 requêtes rejetées', results[-1])

    def test_network_timeout_is_unconfirmed_without_retry_or_row_diagnosis(self):
        plugin = migration_methods(PluginConfig())
        task = Mock()
        task.isCanceled.return_value = False
        client = Mock()
        client.insert.side_effect = RuntimeError('Read timed out')
        result = plugin._do_migration_task(task, [
            ('Test', 'test', 'id', [{'id': value} for value in range(100)]),
        ], client)
        client.insert.assert_called_once()
        self.assertEqual(result['errors_count'], 100)
        self.assertIn('0 ligne(s) non publiée(s)', result['results'][-1])
        self.assertIn('100 ligne(s) au résultat non confirmé', result['results'][-1])
        self.assertFalse(any('erreur(s) de données' in line for line in result['results']))

    def test_uuid_upsert_excludes_local_id_but_composite_id_key_preserves_it(self):
        plugin = migration_methods(PluginConfig())
        row = {'id': 1, 'uuid_membre': 'local-uuid'}
        self.assertEqual(plugin._prepare_api_write_rows([row], 'uuid_membre'), [{'uuid_membre': 'local-uuid'}])
        self.assertEqual(plugin._prepare_api_write_rows([row], 'id,uuid_membre'), [row])

    def test_select_uses_configured_page_size_and_explicit_override(self):
        client = client_module.PostgREST('http://localhost')
        with patch.object(client_module, 'CONFIG', PluginConfig(page_size=2)):
            with patch.object(client, '_make_request', side_effect=[[{'id': 1}, {'id': 2}], [{'id': 3}]]) as request:
                self.assertEqual(len(client.select('test')), 3)
                self.assertEqual([call.kwargs['params']['limit'] for call in request.call_args_list], ['2', '2'])
                self.assertEqual(request.call_args.kwargs['params']['offset'], '2')
            with patch.object(client, '_make_request', return_value=[]) as request:
                client.select('test', page_size=7)
                self.assertEqual(request.call_args.kwargs['params']['limit'], '7')

    def test_request_and_probe_use_configured_timeouts(self):
        client = client_module.PostgREST('http://localhost')
        client.set_auth_token('test')
        utils = SimpleNamespace(Utils=Mock())
        response = Mock(status_code=200, text='[]')
        with patch.object(client_module, 'CONFIG', PluginConfig(request_timeout=45, connection_timeout=8)):
            with patch.dict(sys.modules, {'_connection_test_plugin.utils': utils}):
                with patch.object(client.session, 'request', return_value=response) as request:
                    client._make_request('GET', 'test')
                    self.assertEqual(request.call_args.kwargs['timeout'], 45)
                    client._make_request('GET', 'test', timeout=12)
                    self.assertEqual(request.call_args.kwargs['timeout'], 12)
                    client.check_connection()
                    self.assertEqual(request.call_args.kwargs['timeout'], 8)


if __name__ == '__main__':
    unittest.main()
