"""Connection regressions runnable without the QGIS Python runtime."""

import ast
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
package = ModuleType('_connection_test_plugin')
package.__path__ = [str(ROOT)]
sys.modules[package.__name__] = package
spec = importlib.util.spec_from_file_location(
    '_connection_test_plugin.postgrest_client', ROOT / 'postgrest_client.py',
)
client_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client_module)


def plugin_methods(namespace):
    """Load the real session methods without initializing QGIS widgets."""
    tree = ast.parse((ROOT / 'mrv_teraka.py').read_text(encoding='utf-8'))
    plugin = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'MrvTeraka')
    plugin.body = [node for node in plugin.body if isinstance(node, ast.FunctionDef) and node.name in {
        'load_saved_token', 'authenticate_with_credentials',
    }]
    module = ast.Module(body=[plugin], type_ignores=[])
    exec(compile(module, str(ROOT / 'mrv_teraka.py'), 'exec'), namespace)
    return namespace['MrvTeraka']


class ConnectionSessionTests(unittest.TestCase):
    def test_connection_probe_preserves_server_error(self):
        client = client_module.PostgREST('http://127.0.0.1:8051')
        client.set_auth_token('test-token')
        error = client_module.PostgRESTError(401, 'Unauthorized', '', 'HEAD', '', 'invalid JWT')
        with patch.object(client, '_make_request', side_effect=error):
            with self.assertRaises(client_module.PostgRESTError) as raised:
                client.check_connection()
            self.assertIs(raised.exception, error)
            self.assertFalse(client.verify_token())

    def test_saved_session_survives_server_outage_and_keeps_retry_client(self):
        client = Mock()
        client.check_connection.side_effect = RuntimeError('Connection refused')
        settings = Mock()
        settings.value.side_effect = lambda key, default=None: default
        plugin_type = plugin_methods({
            'PostgREST': Mock(return_value=client),
            'PostgRESTMode': client_module.PostgRESTMode,
            'QSettings': Mock(return_value=settings),
        })
        plugin = plugin_type()
        plugin.token_manager = Mock()
        plugin.token_manager.load_token.return_value = ('test-token', 'http://127.0.0.1:8051', 'django')
        plugin.conn_checker = Mock()
        plugin.update_auth_ui = Mock()
        plugin.load_saved_token()
        plugin.token_manager.clear_token.assert_not_called()
        plugin.conn_checker.set_client.assert_called_once_with(client)
        self.assertIs(plugin.postgrest, client)

    def test_remote_token_does_not_override_selected_local_server(self):
        settings = Mock()
        settings.value.return_value = 'http://127.0.0.1:8051'
        constructor = Mock()
        plugin_type = plugin_methods({
            'PostgREST': constructor,
            'PostgRESTMode': client_module.PostgRESTMode,
            'QSettings': Mock(return_value=settings),
        })
        plugin = plugin_type()
        plugin.token_manager = Mock()
        plugin.token_manager.load_token.return_value = ('remote-token', 'http://127.0.0.1:8050/', 'django')
        plugin.load_saved_token()
        constructor.assert_not_called()
        plugin.token_manager.clear_token.assert_not_called()

    def test_login_is_not_reported_as_success_when_data_api_rejects_token(self):
        candidate = Mock()
        candidate.check_connection.side_effect = RuntimeError('JWT rejected by PostgREST')
        authenticator = Mock()
        authenticator.authenticate.return_value = 'new-token'
        plugin_type = plugin_methods({
            'PostgREST': Mock(return_value=candidate),
            'PostgRESTMode': client_module.PostgRESTMode,
            'PostgRESTAuthenticator': Mock(return_value=authenticator),
        })
        plugin = plugin_type()
        old_client = Mock()
        plugin.postgrest = old_client
        plugin.api_base_url = 'http://old-server'
        plugin.postgrest_mode = client_module.PostgRESTMode.DJANGO
        plugin.token_manager = Mock()
        plugin.show_error = Mock(return_value=True)
        plugin.tr = lambda text: text
        result = plugin.authenticate_with_credentials({
            'username': 'local-user', 'password': 'test-password',
            'url': 'http://127.0.0.1:8051', 'mode': 'Django',
        })
        self.assertFalse(result)
        self.assertIs(plugin.postgrest, old_client)
        self.assertEqual(plugin.api_base_url, 'http://old-server')
        plugin.token_manager.save_token.assert_not_called()


if __name__ == '__main__':
    unittest.main()
