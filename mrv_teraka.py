# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MrvTeraka
                                 A QGIS plugin for the mrv team in iTeraka
 ***************************************************************************/
"""
import json
import os
import os.path
import re
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt, QVariant
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QInputDialog, QLineEdit, QListWidgetItem

from .resources import *

from qgis.core import QgsProject, QgsVectorLayer, QgsMapLayer, QgsTask, QgsApplication, QgsMapLayerStyle, QgsEditorWidgetSetup, QgsFeature, QgsWkbTypes, QgsRasterLayer, QgsDefaultValue
from .mrv_teraka_dockwidget import MrvTerakaDockWidget
from .layer_utils import is_geojson, create_vector_layer, layer_to_list_of_dicts
from .utils import Utils

from .postgrest_client import PostgREST, PostgRESTAuthenticator, PostgRESTMode, PostgRESTError
from .config_postgrest import load_layer_mapping
from .auth_dialog import AuthDialog
from .token_manager import TokenManager
from .mergin_workflow_manager import MerginWorkflowManager, MerginDataMerger
from .validation_dialog import DataValidationDialog
from .project_action_dialog import MissionConfirmationDialog
from .connection_checker import ConnectionChecker
from .project_analyzer import ProjectAnalyzer
from .business_rules import BusinessRulesEngine
from .mergin_api_client import MerginAPIClient
from .mergin_plugin_bridge import MerginPluginBridge


class MrvTeraka:
    """Implémentation du Plugin QGIS MrvTeraka."""

    SYSTEM_ENDPOINTS = {'spatial_ref_sys', 'geometry_columns', 'geography_columns'}
    EMPTY_FILTER_MARKER = '__mrv_empty_filter__'

    def __init__(self, iface):
        self.iface = iface

        self.postgrest_mode = PostgRESTMode.DJANGO
        self.api_base_url = None

        self.postgrest = None
        self.token_manager = TokenManager()
        self.current_username = None
        self.auth_action = None

        self.mergin_manager = None
        self.mergin_bridge = MerginPluginBridge()
        self.current_project_id = None

        self.conn_checker = ConnectionChecker(interval=60)
        self.conn_checker.connection_status_changed.connect(self.on_connection_status_changed)
        self.mergin_validation_ready = False
        self.current_collected_data = None
        self.current_original_data = None
        self.current_data_mapping = None
        self.current_validated_data = None
        self._geo_filter_cache = {}

        self.plugin_dir = os.path.dirname(__file__)
        self.default_project_file = os.path.join(self.plugin_dir, 'Q_v17_7_7_ITASY2026_WP.qgz')

        self.mergin_manager = MerginWorkflowManager(self.plugin_dir)

        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(self.plugin_dir, 'i18n', f'MrvTeraka_{locale}.qm')

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        self.actions = []
        self.menu = self.tr(u'&MRV Teraka')
        self.toolbar = self.iface.addToolBar(u'MrvTeraka')
        self.toolbar.setObjectName(u'MrvTeraka')

        self.auto_open_default_project = False
        self.auto_update_sources = False

        self.pluginIsActive = False
        self.dockwidget = None

    # ─────────────────────────────────────────────────────────────────────
    # UTILITAIRES
    # ─────────────────────────────────────────────────────────────────────

    def _apply_field_map(self, data, field_map):
        """
        Renomme ou exclut les clés d'une liste de dicts selon le field_map.
          field_map = { 'qgis_field': 'api_column' }
          - clé absente du map  → conservée telle quelle
          - valeur vide ('')    → nom identique (conservé)
          - valeur False/None   → champ exclu
        """
        if not field_map:
            return data
        result = []
        for row in data:
            new_row = {}
            for qgis_col, value in row.items():
                if qgis_col not in field_map:
                    new_row[qgis_col] = value
                    continue

                api_col = field_map[qgis_col]
                if api_col is False or api_col is None:
                    continue

                new_row[api_col if api_col else qgis_col] = value
            result.append(new_row)
        return result

    def _extract_endpoint_and_field_map(self, mapping_result):
        """
        Supporte l'ancien format {lid: endpoint} et le nouveau {lid: {endpoint, field_map}}.
        Retourne (endpoint, field_map).
        """
        if isinstance(mapping_result, dict):
            return mapping_result.get('endpoint'), mapping_result.get('field_map', {})
        return mapping_result, {}

    # ─────────────────────────────────────────────────────────────────────
    # ERREURS ET MESSAGES
    # ─────────────────────────────────────────────────────────────────────

    def show_api_error_view(self, exc):
        """Affiche une erreur Django/PostgREST structurée si possible."""
        try:
            from .django_error_viewer import show_django_error
        except ImportError:
            return False

        if isinstance(exc, PostgRESTError):
            body = exc.error_body or exc.user_message()
            headers = {}
            if exc.error_json:
                body = json.dumps(exc.error_json, indent=2, ensure_ascii=False)
                headers['Content-Type'] = 'application/json'

            try:
                show_django_error(
                    parent=self.iface.mainWindow(),
                    error_code=exc.status_code,
                    error_reason=exc.reason,
                    html_content='',
                    error_message=MrvTeraka._format_postgrest_error(
                        exc, "Requête API", exc.endpoint, 0, 0, []
                    ),
                    url=exc.url,
                    method=exc.method,
                    headers=headers,
                    text_content=body
                )
                return True
            except Exception:
                return False

        error_text = str(exc)
        if not error_text:
            return False

        status_code = 500
        reason = 'Erreur serveur'
        body = error_text.strip()

        match = re.match(r"PostgREST HTTP (\d+) : ([^\n]+)\n(.*)$", error_text, re.S)
        if match:
            status_code = int(match.group(1))
            reason = match.group(2).strip()
            body = match.group(3).strip()
        else:
            auth_match = re.match(r"Authentification échouée: (\d+) ([^\n]+)\n(.*)$", error_text, re.S)
            if auth_match:
                status_code = int(auth_match.group(1))
                reason = auth_match.group(2).strip()
                body = auth_match.group(3).strip()

        if not body:
            return False

        is_html = 'text/html' in body.lower() or bool(re.search(r'<(?:!doctype|html|head|body|div|span|p|h1|h2|h3)', body, re.IGNORECASE))
        if not is_html:
            return False

        try:
            show_django_error(
                parent=self.iface.mainWindow(),
                error_code=status_code,
                error_reason=reason,
                html_content=body,
                error_message='',
                url='',
                method='GET',
                headers={},
                text_content=body
            )
            return True
        except Exception:
            return False

    def show_error(self, title, exc):
        """Affiche une erreur via le viewer HTML si possible, sinon en boîte critique."""
        if exc is not None and self.show_api_error_view(exc):
            return True
        self.show_message(title, str(exc), icon=QMessageBox.Critical)
        return False

    def show_warning(self, title, message):
        """Affiche un avertissement."""
        self.show_message(title, message, icon=QMessageBox.Warning)

    def show_info(self, title, message):
        """Affiche une information."""
        self.show_message(title, message, icon=QMessageBox.Information)

    def push_info(self, title, message, duration=3):
        """Pousse un message d'information dans la barre de message de QGIS."""
        self.iface.messageBar().pushMessage(title, message, level=0, duration=duration)

    def push_warning(self, title, message, duration=5):
        """Pousse un avertissement dans la barre de message de QGIS."""
        self.iface.messageBar().pushMessage(title, message, level=1, duration=duration)

    def push_error(self, title, message, duration=7):
        """Pousse une erreur dans la barre de message de QGIS."""
        self.iface.messageBar().pushMessage(title, message, level=2, duration=duration)

    def ask_confirmation(self, title, message):
        """Pose une question oui/non à l'utilisateur."""
        reply = QMessageBox.question(
            self.iface.mainWindow(),
            title,
            Utils.compact_dialog_message(message),
            QMessageBox.Yes | QMessageBox.No
        )
        return reply == QMessageBox.Yes

    def set_progress(self, value, message=None):
        """Met à jour la barre de progression et le message de statut."""
        if self.dockwidget:
            self.dockwidget.missionProgressBar.setValue(value)
            if message:
                color = "blue" if value < 100 else "green"
                self.dockwidget.set_status_message(message, color=color)

    def show_message(self, title, message, icon=QMessageBox.Information):
        """Affiche un message en texte brut ou HTML selon le contenu."""
        display_message = Utils.compact_dialog_message(message)
        detail_message = Utils.compact_dialog_detail(message)
        msg_box = QMessageBox(self.iface.mainWindow())
        msg_box.setWindowFlags(
            msg_box.windowFlags() |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        msg_box.setIcon(icon)
        msg_box.setWindowTitle(title)
        if self.is_html_content(display_message):
            msg_box.setTextFormat(Qt.RichText)
            msg_box.setText(display_message)
        else:
            msg_box.setTextFormat(Qt.PlainText)
            msg_box.setText(display_message)
        if detail_message != display_message:
            msg_box.setDetailedText(detail_message)
        msg_box.exec_()

    def is_html_content(self, text):
        if not text or not isinstance(text, str):
            return False
        return bool(re.search(r'<(?:!doctype|html|head|body|div|span|p|h[1-6]|br|strong|em|ul|ol|li|table|tr|td|th)', text, re.IGNORECASE))

    def tr(self, message):
        return QCoreApplication.translate('MrvTeraka', message)

    def add_action(self, icon_path, text, callback, enabled_flag=True,
                   add_to_menu=True, add_to_toolbar=True, status_tip=None,
                   whats_this=None, parent=None):
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)
        if status_tip: action.setStatusTip(status_tip)
        if whats_this: action.setWhatsThis(whats_this)
        if add_to_toolbar: self.toolbar.addAction(action)
        if add_to_menu: self.iface.addPluginToMenu(self.menu, action)
        self.actions.append(action)
        return action

    # ─────────────────────────────────────────────────────────────────────
    # INIT / UNLOAD
    # ─────────────────────────────────────────────────────────────────────

    def initGui(self):
        self.auth_action = self.add_action(
            ':/plugins/mrv_teraka/login_icon.svg',
            text=self.tr(u'Connexion'),
            callback=self.show_auth_dialog,
            parent=self.iface.mainWindow()
        )
        self.add_action(
            ':/plugins/mrv_teraka/icon.png',
            text=self.tr(u'iTeraka'),
            callback=self.run,
            parent=self.iface.mainWindow()
        )
        self.load_saved_token()
        self.conn_checker.start()
        if self.auto_open_default_project:
            self.open_default_qgis_project()

    def unload(self):
        if hasattr(self, 'conn_checker'):
            self.conn_checker.stop()
        for action in self.actions:
            self.iface.removePluginMenu(self.tr(u'&MRV Teraka'), action)
            self.iface.removeToolBarIcon(action)
        del self.toolbar

    def onClosePlugin(self):
        self.dockwidget.closingPlugin.disconnect(self.onClosePlugin)
        self.pluginIsActive = False

    # ─────────────────────────────────────────────────────────────────────
    # AUTHENTIFICATION
    # ─────────────────────────────────────────────────────────────────────

    def show_auth_dialog(self):
        auth_dialog = AuthDialog(
            parent=self.iface.mainWindow(),
            api_modes={
                'Django': PostgRESTMode.DJANGO,
                'PostgREST (Standalone)': PostgRESTMode.STANDALONE
            }
        )
        if auth_dialog.exec_() == AuthDialog.Accepted:
            credentials = auth_dialog.get_credentials()
            success = self.authenticate_with_credentials(credentials, auth_dialog)
            if success:
                auth_dialog.save_settings()

    def authenticate_with_credentials(self, credentials, dialog=None):
        username = credentials['username']
        password = credentials['password']
        self.api_base_url = credentials['url']

        if credentials['mode']:
            mode_map = {
                'Django': PostgRESTMode.DJANGO,
                'PostgREST (Standalone)': PostgRESTMode.STANDALONE
            }
            self.postgrest_mode = mode_map.get(credentials['mode'], PostgRESTMode.DJANGO)

        try:
            authenticator = PostgRESTAuthenticator(self.api_base_url, mode=self.postgrest_mode)
            token = authenticator.authenticate(username, password)

            self.postgrest = PostgREST(self.api_base_url, mode=self.postgrest_mode)
            self.postgrest.set_auth_token(token)

            if self.mergin_bridge.is_connected():
                if self.dockwidget:
                    self.dockwidget.merginResultsTextEdit.append(
                        "✓ {}".format(self.mergin_bridge.connection_label())
                    )
            elif credentials.get('mergin_username') and credentials.get('mergin_password'):
                self.mergin_api = MerginAPIClient()
                if self.mergin_api.login(credentials['mergin_username'], credentials['mergin_password']):
                    if self.dockwidget:
                        self.dockwidget.merginResultsTextEdit.append(f"✓ Connecté à Mergin Maps : {credentials['mergin_username']}")
                else:
                    if self.dockwidget:
                        self.dockwidget.merginResultsTextEdit.append("⚠️ Échec connexion Mergin Maps. Automatisation restreinte.")

            self.token_manager.save_token(token, self.api_base_url, self.postgrest_mode.value)
            self.current_username = username
            self.conn_checker.set_client(self.postgrest)

            # Note: La sauvegarde des identifiants (username, url, mergin_user) est désormais gérée
            # par auth_dialog.save_settings() dans show_auth_dialog() après succès.
            # On met à jour l'UI et on informe l'utilisateur.

            self.update_auth_ui()
            self.conn_checker.set_client(self.postgrest)

            if self.dockwidget:
                self.dockwidget.set_authenticated(username, self.api_base_url, role=self.token_manager.get_user_role())

            mode_label = "Django" if self.postgrest_mode == PostgRESTMode.DJANGO else "PostgREST"
            self.show_info(
                self.tr(u'Authentification réussie'),
                f"Connecté à {mode_label} en tant que {username}"
            )
            return True

        except Exception as exc:
            shown = self.show_error(self.tr(u"Erreur d'authentification"), exc)
            if dialog and not shown:
                dialog.show_error(str(exc))
            return False

    def load_saved_token(self):
        token, api_url, mode = self.token_manager.load_token()
        if token and api_url:
            self.postgrest = PostgREST(api_url, mode=PostgRESTMode[mode.upper()] if mode else PostgRESTMode.DJANGO)
            self.postgrest.set_auth_token(token)
            self.api_base_url = api_url
            self.conn_checker.set_client(self.postgrest)

            if not self.postgrest.verify_token():
                self.token_manager.clear_token()
                self.postgrest = None
                self.current_username = None
                self.conn_checker.set_client(None)
                return

            settings = QSettings('iTeraka', 'MrvTeraka')
            self.current_username = settings.value('auth/username', 'Utilisateur')
            self.update_auth_ui()

    def open_default_qgis_project(self):
        if os.path.exists(self.default_project_file):
            if not QgsProject.instance().read(self.default_project_file):
                self.show_warning(
                    self.tr(u'Ouverture du projet'),
                    self.tr(u'Impossible de charger le projet QGIS par défaut.')
                )
        else:
            self.show_warning(
                self.tr(u'Ouverture du projet'),
                self.tr(u'Fichier de projet QGIS introuvable : {path}').format(path=self.default_project_file)
            )

    def update_auth_ui(self):
        if self.auth_action:
            try:
                self.auth_action.triggered.disconnect()
            except Exception:
                pass
            self.auth_action.setText(self.tr(u'Déconnecter'))
            self.auth_action.triggered.connect(self.logout)

        if self.dockwidget:
            username = self.current_username or "Utilisateur"
            url = self.api_base_url or "API"
            role = self.token_manager.get_user_role()
            self.dockwidget.set_authenticated(username, url, role=role)

    def on_connection_status_changed(self, is_connected, message):
        if not is_connected and self.postgrest:
            if self.dockwidget:
                self.dockwidget.set_status_message(f"⚠️ {message}", color="orange")
        elif is_connected and self.dockwidget:
            role = self.token_manager.get_user_role()
            self.dockwidget.set_authenticated(self.current_username, self.api_base_url, role=role)

    def logout(self, confirm=True):
        if confirm:
            if not self.ask_confirmation(
                self.tr(u'Confirmation'),
                self.tr(u'Êtes-vous sûr de vouloir vous déconnecter ?')
            ):
                return

        self.token_manager.clear_token()
        self.postgrest = None
        self.current_username = None

        if hasattr(self, 'conn_checker'):
            self.conn_checker.set_client(None)

        if self.auth_action:
            try:
                self.auth_action.triggered.disconnect()
            except Exception:
                pass
            self.auth_action.setText(self.tr(u'Connexion'))
            self.auth_action.triggered.connect(self.show_auth_dialog)

        if self.dockwidget:
            self.dockwidget.set_unauthenticated()

        if confirm:
            self.show_info(
                self.tr(u'Déconnexion'),
                self.tr(u'Vous avez été déconnecté.')
            )

    def check_api_auth(self):
        if not self.postgrest or not self.token_manager.is_token_valid():
            self.show_warning(
                self.tr(u'Authentification requise'),
                self.tr(u'Veuillez vous authentifier avant de continuer.')
            )
            self.show_auth_dialog()
            return False
        return True

    # ─────────────────────────────────────────────────────────────────────
    # MAPPINGS
    # ─────────────────────────────────────────────────────────────────────

    def refresh_api_mappings(self, force_api=True):
        if not self.postgrest:
            return False
        try:
            schema = self.postgrest.fetch_schema()
            if schema and 'definitions' in schema:
                new_mappings = {}
                for table_name, definition in schema['definitions'].items():
                    if self.is_system_endpoint(table_name):
                        continue
                    geom_field = None
                    props = definition.get('properties', {})
                    for p_name, p_data in props.items():
                        if p_data.get('format') == 'geojson' or p_name in ['geom', 'geometry', 'the_geom']:
                            geom_field = p_name
                            break
                    new_mappings[table_name] = {
                        'endpoint': table_name,
                        'geom_field': geom_field,
                        'pk_field': 'id',
                        'columns': list(props.keys())
                    }
                self.layer_mappings = self.filter_system_mappings(new_mappings)
                self._geo_filter_cache.clear()
                mapping_path = os.path.join(self.plugin_dir, 'layer_table_mapping.json')
                # Sanitize mappings: don't store geom_field when it's None
                save_mappings = {}
                for name, cfg in self.layer_mappings.items():
                    cfg_to_save = {k: v for k, v in cfg.items() if not (k == 'geom_field' and v is None)}
                    save_mappings[name] = cfg_to_save
                with open(mapping_path, 'w', encoding='utf-8') as f:
                    json.dump({'mappings': save_mappings}, f, indent=4)
                return True
        except Exception as e:
            print(f"Erreur refresh mappings: {e}")
        return False

    def local_mapping_path(self):
        return os.path.join(self.plugin_dir, 'layer_table_mapping.json')

    def load_local_mapping_content(self):
        mapping_path = self.local_mapping_path()
        if not os.path.exists(mapping_path):
            return {'mappings': {}}
        try:
            with open(mapping_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
        except Exception:
            return {'mappings': {}}
        if not isinstance(content, dict):
            return {'mappings': {}}
        if not isinstance(content.get('mappings'), dict):
            content['mappings'] = {}
        return content

    def load_layer_mappings(self):
        if getattr(self, 'layer_mappings', None) is not None:
            self.layer_mappings = self.filter_system_mappings(self.layer_mappings)
            return self.layer_mappings

        if self.postgrest:
            try:
                schema = self.postgrest.fetch_schema()
                if schema and 'definitions' in schema:
                    mappings = {}
                    for table_name, definition in schema['definitions'].items():
                        if self.is_system_endpoint(table_name):
                            continue
                        geom_field = None
                        props = definition.get('properties', {})
                        for p_name, p_data in props.items():
                            if p_data.get('format') == 'geojson' or p_name in ['geom', 'geometry', 'the_geom']:
                                geom_field = p_name
                                break
                        mappings[table_name] = {
                            'endpoint': table_name,
                            'geom_field': geom_field,
                            'pk_field': 'id',
                            'columns': list(props.keys())
                        }
                    # Charger et fusionner avec les mappings du fichier JSON
                    # Important: le .update() va écraser avec les bonnes PK UUIDs inférées
                    json_mappings = load_layer_mapping(self.plugin_dir)
                    
                    # Pour chaque mapping du JSON, mettre à jour complètement (pas juste fusionner)
                    for table_name, json_mapping in json_mappings.items():
                        endpoint = json_mapping.get('endpoint', table_name) if isinstance(json_mapping, dict) else table_name
                        if self.is_system_endpoint(table_name) or self.is_system_endpoint(endpoint):
                            continue
                        if table_name in mappings:
                            # Fusionner intelligemment: garder columns du schema, utiliser pk du JSON
                            schema_columns = mappings[table_name].get('columns', [])
                            mappings[table_name].update(json_mapping)
                            # Ajouter les colonnes du schema si pas présentes dans JSON
                            if 'columns' not in json_mapping:
                                mappings[table_name]['columns'] = schema_columns
                        else:
                            # Mapping nouveau dans JSON
                            mappings[table_name] = json_mapping
                    
                    self.layer_mappings = self.filter_system_mappings(mappings)
                    return self.layer_mappings
            except Exception:
                pass

        self.layer_mappings = self.filter_system_mappings(load_layer_mapping(self.plugin_dir))
        return self.layer_mappings

    def filter_system_mappings(self, mappings):
        if not isinstance(mappings, dict):
            return {}
        return {
            name: mapping
            for name, mapping in mappings.items()
            if not self.is_system_endpoint(name)
            and not self.is_system_endpoint(mapping.get('endpoint') if isinstance(mapping, dict) else None)
        }

    @classmethod
    def is_system_endpoint(cls, name):
        return str(name or '').strip().lower() in cls.SYSTEM_ENDPOINTS

    def get_layer_mapping(self, layer_name):
        mappings = self.load_layer_mappings()
        if layer_name in mappings and mappings[layer_name].get('endpoint'):
            if self.is_system_endpoint(layer_name) or self.is_system_endpoint(mappings[layer_name].get('endpoint')):
                return None
            return mappings[layer_name]
        return None

    def update_local_layer_mapping(self, selected_mappings):
        if not selected_mappings:
            QMessageBox.warning(
                self.iface.mainWindow(),
                self.tr(u'Mapping'),
                self.tr(u'Aucune couche sélectionnée pour la mise à jour du mapping.')
            )
            return False

        reply = QMessageBox.question(
            self.iface.mainWindow(),
            self.tr(u'Confirmer la mise à jour du mapping'),
            self.tr(
                u'Les correspondances sélectionnées vont remplacer ou ajouter le mapping local '
                u'pour les couches du projet actuel.\n\nContinuer ?'
            ),
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return False

        content = self.load_local_mapping_content()
        mappings = content['mappings']
        updated_count = 0

        for layer_id, mapping_result in selected_mappings.items():
            endpoint, field_map = self._extract_endpoint_and_field_map(mapping_result)
            layer = QgsProject.instance().mapLayer(layer_id)
            if not layer or not endpoint:
                continue

            mapping = dict(self.get_mapping_for_endpoint(endpoint))
            mapping['endpoint'] = endpoint

            # ← Persister le field_map dans le fichier local
            if field_map:
                mapping['field_map'] = field_map

            layer_name = layer.name()
            mappings[layer_name] = mapping

            layer.setCustomProperty('postgrest:endpoint', endpoint)
            geom_prop = mapping.get('geom_field')
            if geom_prop:
                layer.setCustomProperty('postgrest:geom_field', geom_prop)
            else:
                try:
                    layer.removeCustomProperty('postgrest:geom_field')
                except Exception:
                    layer.setCustomProperty('postgrest:geom_field', '')
            layer.setCustomProperty('postgrest:pk_field', mapping.get('pk_field', 'id'))
            updated_count += 1

        if updated_count == 0:
            QMessageBox.warning(
                self.iface.mainWindow(),
                self.tr(u'Mapping'),
                self.tr(u'Aucun mapping valide à enregistrer.')
            )
            return False

        # Before saving, remove geom_field keys that are None so the file only contains
        # geom_field when the layer is spatial
        sanitized = {}
        for name, cfg in mappings.items():
            cfg_to_save = {k: v for k, v in cfg.items() if not (k == 'geom_field' and v is None)}
            sanitized[name] = cfg_to_save
        content['mappings'] = sanitized
        with open(self.local_mapping_path(), 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=4, ensure_ascii=False)

        self.layer_mappings = None
        self.load_layer_mappings()

        QMessageBox.information(
            self.iface.mainWindow(),
            self.tr(u'Mapping mis à jour'),
            self.tr(u'{0} correspondance(s) enregistrée(s) dans le mapping local.').format(updated_count)
        )
        if self.dockwidget:
            self.dockwidget.merginResultsTextEdit.append(
                self.tr(u'✅ {0} mapping(s) local(aux) mis à jour.').format(updated_count)
            )
        return True

    def get_project_layer_endpoints(self):
        endpoints = {}
        for layer in QgsProject.instance().mapLayers().values():
            if layer.type() != QgsMapLayer.VectorLayer:
                continue
            if layer.providerType() not in ('ogr', 'postgres', 'memory'):
                continue
            layer_name = layer.name()
            if not layer_name:
                continue
            mapping = self.get_layer_mapping(layer_name)
            if not mapping:
                endpoint = layer.customProperty('postgrest:endpoint')
                mapping = self.get_mapping_for_endpoint(endpoint, include_project=False, fallback=False) if endpoint else None
            if mapping and mapping.get('endpoint'):
                if self.is_system_endpoint(layer_name) or self.is_system_endpoint(mapping.get('endpoint')):
                    continue
                endpoints[layer_name] = mapping
        return endpoints

    def get_mapping_for_endpoint(self, endpoint, include_project=True, fallback=True):
        if not endpoint:
            return {'endpoint': endpoint, 'geom_field': None, 'pk_field': 'id'}

        mappings = self.load_layer_mappings()
        for m_name, m_data in mappings.items():
            if m_data.get('endpoint') == endpoint:
                return m_data

        if include_project:
            for mapping in self.get_project_layer_endpoints().values():
                if mapping.get('endpoint') == endpoint:
                    return mapping

        if fallback:
            return {'endpoint': endpoint, 'geom_field': 'geom', 'pk_field': 'id'}
        return None

    def mapping_columns(self, mapping):
        if not isinstance(mapping, dict):
            return set()
        return {str(col).lower() for col in mapping.get('columns', [])}

    def mapping_has_column(self, mapping, column):
        return str(column).lower() in self.mapping_columns(mapping)

    def conflict_field_for_mapping(self, mapping):
        """Préfère uuid_<endpoint> pour les upserts quand cette colonne existe."""
        if not isinstance(mapping, dict):
            return 'id'

        endpoint = str(mapping.get('endpoint') or '').strip().lower()
        columns = self.mapping_columns(mapping)
        pk_field = str(mapping.get('pk_field', 'id') or 'id').lower()

        candidates = []
        if endpoint:
            candidates.append(f'uuid_{endpoint}')
            if endpoint.endswith('s'):
                candidates.append(f'uuid_{endpoint[:-1]}')

        for candidate in candidates:
            if candidate in columns:
                return candidate

        return pk_field

    def is_current_user_validator(self):
        try:
            if self.token_manager.get_is_validator():
                return True
        except Exception:
            pass

        role = self.token_manager.get_user_role()
        if isinstance(role, (list, tuple, set)):
            role_text = " ".join(str(item) for item in role)
        else:
            role_text = str(role or "")
        role_text = role_text.lower()
        return any(
            value in role_text
            for value in ['validator', 'validateur', 'admin', 'superviseur', 'mrv_l3', 'mrv']
        )

    def current_user_uuid(self):
        try:
            return self.normalize_uuid_value(self.token_manager.get_user_id())
        except Exception:
            return None

    @staticmethod
    def normalize_uuid_value(value):
        if value is None:
            return None
        text = str(value).strip().replace('{', '').replace('}', '')
        if not text:
            return None
        if re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', text, re.IGNORECASE):
            return text.lower()
        return None

    @staticmethod
    def is_uuid_column(field_name):
        field = str(field_name or '').lower()
        return field.startswith('uuid') or field.endswith('_uuid')

    @staticmethod
    def today_iso_date():
        return __import__('datetime').date.today().isoformat()

    def normalize_backend_defaults(self, row, mapping, user_uuid=None):
        """Nettoie les valeurs connues avant PostgREST pour éviter les erreurs 23502/22P02."""
        if not isinstance(row, dict):
            return row

        prepared = dict(row)
        columns = self.mapping_columns(mapping)
        user_uuid = self.normalize_uuid_value(user_uuid) or self.current_user_uuid()

        if 'date_saisie' in columns and not prepared.get('date_saisie'):
            prepared['date_saisie'] = self.today_iso_date()

        for key in list(prepared.keys()):
            key_lower = str(key).lower()
            if not self.is_uuid_column(key_lower):
                continue
            value = prepared.get(key)
            if value in (None, ''):
                prepared[key] = None
                continue
            normalized = self.normalize_uuid_value(value)
            if normalized:
                prepared[key] = normalized
            elif key_lower in {'uuid_operateur', 'uuid_verificateur', 'uuid_validateur'} and user_uuid:
                prepared[key] = user_uuid
            else:
                prepared[key] = None

        if 'uuid_operateur' in columns and user_uuid and not prepared.get('uuid_operateur'):
            prepared['uuid_operateur'] = user_uuid
        if 'uuid_verificateur' in columns and user_uuid and not prepared.get('uuid_verificateur'):
            prepared['uuid_verificateur'] = user_uuid
        if 'uuid_validateur' in columns and user_uuid and not prepared.get('uuid_validateur'):
            prepared['uuid_validateur'] = user_uuid

        return prepared

    def field_index_by_name(self, layer, field_name):
        if not layer:
            return -1
        target = str(field_name).lower()
        fields = layer.fields()
        for idx in range(fields.count()):
            if fields.at(idx).name().lower() == target:
                return idx
        return -1

    def prepare_rows_for_mapping(self, rows, mapping, add_user_uuid=True, add_verifier_uuid=False):
        if not isinstance(rows, list):
            return rows

        allowed_columns = self.mapping_columns(mapping)
        prepared_rows = []
        user_uuid = self.current_user_uuid()
        should_stamp_operator = add_user_uuid and user_uuid and self.mapping_has_column(mapping, 'uuid_operateur')
        should_stamp_verifier = add_verifier_uuid and user_uuid and self.mapping_has_column(mapping, 'uuid_verificateur')

        for row in rows:
            if not isinstance(row, dict):
                prepared_rows.append(row)
                continue

            prepared = {
                key: value
                for key, value in row.items()
                if not allowed_columns or str(key).lower() in allowed_columns
            }
            if should_stamp_operator and not prepared.get('uuid_operateur'):
                prepared['uuid_operateur'] = user_uuid
            if should_stamp_verifier and not prepared.get('uuid_verificateur'):
                prepared['uuid_verificateur'] = user_uuid
            prepared = self.normalize_backend_defaults(prepared, mapping, user_uuid=user_uuid)
            prepared_rows.append(prepared)

        return prepared_rows

    # ─────────────────────────────────────────────────────────────────────
    # FILTRES COMMUNES / SECTEURS
    # ─────────────────────────────────────────────────────────────────────

    def get_selected_commune_codes(self):
        if not self.dockwidget or not hasattr(self.dockwidget, 'communesListWidget'):
            return []
        codes = []
        for i in range(self.dockwidget.communesListWidget.count()):
            item = self.dockwidget.communesListWidget.item(i)
            if item.checkState() == Qt.Checked:
                code = item.data(Qt.UserRole)
                if code:
                    codes.append(str(code))
        return codes

    def get_sector_filter_value(self):
        if not self.dockwidget:
            return ""
        if hasattr(self.dockwidget, 'districtComboBox'):
            text = self.dockwidget.districtComboBox.currentText()
            return text.strip() if text else ""
        return ""

    def sector_filter_column(self, mapping):
        columns = mapping.get('columns', []) if mapping else []
        for candidate in ('secteur', 'district', 'nom_secteur', 'nom_district', 'commune'):
            if candidate in columns:
                return candidate
        return None

    def build_commune_filters(self):
        c_com_values = self.get_selected_commune_codes()
        sector = self.get_sector_filter_value()

        if not c_com_values:
            if sector and self.postgrest:
                communes_mapping = self.get_mapping_for_endpoint('communes')
                column = self.sector_filter_column(communes_mapping)
                if column:
                    try:
                        rows = self.postgrest.select(
                            'communes',
                            select='c_com',
                            filters={column: f'eq.{sector}'},
                            auto_paginate=True
                        )
                        c_com_values = [str(r.get('c_com')) for r in rows if r.get('c_com')]
                    except Exception:
                        pass

        return {'sector': sector, 'c_com_values': c_com_values}

    def build_sector_filters(self, mapping, commune_context=None):
        endpoint = mapping.get('endpoint') if mapping else None
        c_com_values = (commune_context or {}).get('c_com_values', [])
        columns = mapping.get('columns', []) if mapping else []
        has_c_com = 'c_com' in columns

        if endpoint == 'communes':
            if c_com_values:
                return {'c_com': 'in.({})'.format(','.join(c_com_values))}
            sector = self.get_sector_filter_value()
            if sector:
                column = self.sector_filter_column(mapping)
                return {column: f'eq.{sector}'} if column else {}
            return {}

        if not has_c_com:
            return {}

        if c_com_values:
            return {'c_com': 'in.({})'.format(','.join(c_com_values))}

        return {self.EMPTY_FILTER_MARKER: True}

    def is_empty_filter(self, filters):
        return isinstance(filters, dict) and bool(filters.get(self.EMPTY_FILTER_MARKER))

    def fetch_unique_regions(self):
        if not self.postgrest:
            return []
        cache_key = ('regions',)
        if cache_key in self._geo_filter_cache:
            return self._geo_filter_cache[cache_key]
        try:
            rows = self.postgrest.select('communes', select='region', order='region.asc', auto_paginate=True)
            values = sorted(list(set(r.get('region') for r in rows if r.get('region'))))
            self._geo_filter_cache[cache_key] = values
            return values
        except Exception as e:
            print(f"Erreur fetch regions: {e}")
            return []

    def fetch_unique_districts(self, region_name=None):
        if not self.postgrest:
            return []
        cache_key = ('districts', region_name or '')
        if cache_key in self._geo_filter_cache:
            return self._geo_filter_cache[cache_key]
        filters = {'region': f'eq.{region_name}'} if region_name else None
        try:
            rows = self.postgrest.select('communes', select='district', filters=filters, order='district.asc', auto_paginate=True)
            values = sorted(list(set(d.get('district') for d in rows if d.get('district'))))
            self._geo_filter_cache[cache_key] = values
            return values
        except Exception as e:
            print(f"Erreur fetch districts: {e}")
            return []

    def fetch_communes_by_district(self, district_name=None):
        if not self.postgrest:
            return []
        cache_key = ('communes', district_name or '')
        if cache_key in self._geo_filter_cache:
            return self._geo_filter_cache[cache_key]
        filters = {'district': f'eq.{district_name}'} if district_name else None
        try:
            rows = self.postgrest.select('communes', select='commune,c_com', filters=filters, order='commune.asc', auto_paginate=True)
            values = [(r.get('commune'), r.get('c_com')) for r in rows if r.get('commune') and r.get('c_com')]
            self._geo_filter_cache[cache_key] = values
            return values
        except Exception as e:
            print(f"Erreur fetch communes: {e}")
            return []

    def fetch_sector_values(self):
        return self.fetch_unique_districts()

    # ─────────────────────────────────────────────────────────────────────
    # PROJET / MERGIN
    # ─────────────────────────────────────────────────────────────────────

    def save_current_project_configuration(self):
        if not self.check_api_auth():
            return

        name, ok = QInputDialog.getText(self.iface.mainWindow(), self.tr(u"Nouveau Projet Mergin"), self.tr(u"Nom du projet :"))
        if not ok or not name:
            return

        endpoints = self.get_project_layer_endpoints()
        if not endpoints:
            QMessageBox.warning(self.iface.mainWindow(), self.tr(u"Erreur"), self.tr(u"Aucune couche mappée trouvée dans le projet."))
            return

        tables = list(set([m['endpoint'] for m in endpoints.values()]))
        project_dir = None
        project_file = None
        full_mergin_name = None

        try:
            project_dir, safe_name = self.mergin_bridge.new_project_dir(name)
            project_file = os.path.join(project_dir, "{}.qgz".format(safe_name))

            project = QgsProject.instance()
            if not project.write(project_file):
                QMessageBox.warning(
                    self.iface.mainWindow(),
                    self.tr(u"Erreur"),
                    self.tr(u"Impossible d'ecrire le projet QGIS dans le dossier Mergin.")
                )
                return

            project_id = self.mergin_manager.create_project(safe_name, tables)
            self.current_project_id = project_id

            if self.mergin_bridge.is_connected():
                full_mergin_name = self.mergin_bridge.create_project_and_push(safe_name, project_dir)
                message = self.tr(
                    u"Projet Mergin '{0}' cree et envoye avec {1} couches."
                ).format(full_mergin_name, len(tables))
            else:
                message = self.tr(
                    u"Projet local cree dans :\n{0}\n\n"
                    u"ℹ️ {1}. Le projet n'a pas encore ete publie."
                ).format(project_dir, self.mergin_bridge.connection_label())
        except Exception as exc:
            self.show_error(self.tr(u"Erreur creation projet Mergin"), exc)
            return

        if self.dockwidget:
            self.dockwidget.populate_project_list()
            idx = self.dockwidget.projectComboBox.findData(project_file)
            if idx >= 0:
                self.dockwidget.projectComboBox.setCurrentIndex(idx)

        self.show_info(self.tr(u"Projet Mergin cree"), message)

    def load_project_by_id(self, project_id):
        if not self.check_api_auth():
            return

        info = self.mergin_manager.get_project_info(project_id)
        if not info:
            QMessageBox.critical(self.iface.mainWindow(), self.tr(u"Erreur"), self.tr(u"Informations du projet introuvables."))
            return

        self.current_project_id = project_id
        tables = info.get('source_tables', [])

        if not tables:
            QMessageBox.warning(self.iface.mainWindow(), self.tr(u"Projet vide"), self.tr(u"Ce projet ne contient aucune table."))
            return

        project = QgsProject.instance()
        layers_to_refresh = {}
        tables_to_load = []

        for table in tables:
            existing_layers = [l for l in project.mapLayers().values() if l.customProperty('postgrest:endpoint') == table]
            if existing_layers:
                layers_to_refresh[existing_layers[0].id()] = table
            else:
                tables_to_load.append(table)

        if layers_to_refresh:
            self.refresh_layers_from_api(layers_to_refresh)

        errors = []
        commune_context = self.build_commune_filters()

        for table in tables_to_load:
            try:
                mapping = self.get_mapping_for_endpoint(table)
                filters = self.build_sector_filters(mapping, commune_context)
                db_data = [] if self.is_empty_filter(filters) else self.postgrest.select(table, filters=filters)
                display_name = f"{table} (API)"
                geom_field = mapping.get('geom_field', 'geom')

                layer = create_vector_layer(db_data, display_name, geom_field)
                if layer and layer.isValid():
                    layer.setCustomProperty('postgrest:endpoint', table)
                    layer.setCustomProperty('postgrest:geom_field', geom_field)
                    layer.setCustomProperty('postgrest:pk_field', mapping.get('pk_field', 'id'))
                    project.addMapLayer(layer)
                else:
                    errors.append(table)
            except Exception as e:
                errors.append(f"{table} ({str(e)})")

        if errors:
            self.show_message(
                self.tr(u"Chargement partiel"),
                self.tr(u"Erreur lors du chargement des tables : {0}").format(", ".join(errors)),
                icon=QMessageBox.Warning
            )
        elif tables_to_load:
            QMessageBox.information(
                self.iface.mainWindow(),
                self.tr(u"Projet chargé"),
                self.tr(u"Le projet '{0}' a été chargé avec succès.").format(info.get('name'))
            )

    def set_validation_ready(self, ready: bool):
        self.mergin_validation_ready = ready
        if self.dockwidget and hasattr(self.dockwidget, 'autoValidateButton'):
            self.dockwidget.autoValidateButton.setEnabled(ready and self.is_current_user_validator())

    def set_sync_ready(self, ready: bool):
        if self.dockwidget and hasattr(self.dockwidget, 'autoSyncButton'):
            self.dockwidget.autoSyncButton.setEnabled(ready and self.is_current_user_validator())

    def refresh_data_via_api(self, selected_endpoints=None):
        if not self.dockwidget or not self.check_api_auth():
            return
        self.current_validated_data = None
        self.set_sync_ready(False)
        self.load_database_data(selected_endpoints=selected_endpoints, update_existing_only=True)
        self.set_validation_ready(False)

    def load_project_from_mergin(self):
        if not self.dockwidget or not self.check_api_auth():
            return

        imported_file = None
        if self.current_project_id:
            imported_file = os.path.join(
                self.mergin_manager.projects_dir,
                self.current_project_id,
                'imported_data.json'
            )

        if not imported_file or not os.path.exists(imported_file):
            layers = [l for l in QgsProject.instance().mapLayers().values() if l.type() == QgsMapLayer.VectorLayer]
            msg = self.tr(u"Aucune donnée Mergin trouvée.")
            if layers:
                msg += self.tr(
                    u"\nVoulez-vous traiter les couches actuellement chargées dans QGIS ?\n\n"
                    u"Cela lancera l'analyse du projet pour mapper vos données locales."
                )
                reply = QMessageBox.question(self.iface.mainWindow(), self.tr(u'Analyse Projet'), msg, QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    self.import_data_from_active_layers()
                    return
            else:
                QMessageBox.information(
                    self.iface.mainWindow(),
                    self.tr(u'Projet Vide'),
                    self.tr(u"Aucune donnée Mergin et aucune couche vectorielle QGIS détectée.")
                )
            return

        with open(imported_file, 'r', encoding='utf-8') as f:
            self.current_collected_data = json.load(f)

        if isinstance(self.current_collected_data, dict) and len(self.current_collected_data) == 1:
            endpoint_key = next(iter(self.current_collected_data.keys()))
            self.current_data_mapping = self.get_mapping_for_endpoint(endpoint_key)
            self.current_collected_data = self.current_collected_data[endpoint_key]
        else:
            self.current_data_mapping = None

        self.current_validated_data = None
        self.mergin_manager.import_collected_data(self.current_project_id, self.current_collected_data)
        self.set_validation_ready(True)
        self.set_sync_ready(False)
        if self.dockwidget and hasattr(self.dockwidget, 'merginResultsTextEdit'):
            self.dockwidget.merginResultsTextEdit.setPlainText(
                self.tr(u'Projet Mergin chargé. Données prêtes pour validation.')
            )

    def import_data_from_active_layers(self):
        """Importe les données directement depuis les couches QGIS actives."""
        analyzer = ProjectAnalyzer(self.load_layer_mappings())
        report = analyzer.analyze_active_project()

        from .project_action_dialog import ProjectActionDialog
        dialog = ProjectActionDialog(
            self.iface.mainWindow(),
            report['layers'],
            list(self.load_layer_mappings().keys())
        )

        if dialog.exec_() == ProjectActionDialog.Accepted:
            _, selected_mappings = dialog.get_results()
            if not selected_mappings:
                return

            collected_payload = {}
            original_payload = {}
            commune_context = self.build_commune_filters()
            self.dockwidget.merginResultsTextEdit.append("📂 Lecture des couches locales...")

            for lid, mapping_result in selected_mappings.items():
                endpoint, field_map = self._extract_endpoint_and_field_map(mapping_result)

                layer = QgsProject.instance().mapLayer(lid)
                if not layer:
                    continue

                mapping = self.get_mapping_for_endpoint(endpoint)
                layer.setCustomProperty('postgrest:endpoint', endpoint)
                geom_prop = mapping.get('geom_field')
                if geom_prop:
                    layer.setCustomProperty('postgrest:geom_field', geom_prop)
                else:
                    try:
                        layer.removeCustomProperty('postgrest:geom_field')
                    except Exception:
                        layer.setCustomProperty('postgrest:geom_field', '')

                # Extraire données locales
                local_data = layer_to_list_of_dicts(layer, geom_field=(mapping.get('geom_field') or 'geom'))

                # ← Appliquer le field_map : renommer les colonnes QGIS → API
                local_data = self._apply_field_map(local_data, field_map)

                collected_payload[endpoint] = local_data

                try:
                    filters = self.build_sector_filters(mapping, commune_context)
                    original_payload[endpoint] = [] if self.is_empty_filter(filters) else self.postgrest.select(endpoint, filters=filters)
                except Exception:
                    original_payload[endpoint] = []

            self.current_collected_data = collected_payload
            self.current_original_data = original_payload
            self.mergin_validation_ready = True
            self.set_validation_ready(True)

            self.dockwidget.merginResultsTextEdit.append(
                f"✅ {len(collected_payload)} tables prêtes pour validation."
            )
            self.open_validation_form(collected_payload, original_payload)

    def refresh_data_via_mergin(self):
        if not self.dockwidget or not self.check_api_auth():
            return
        self.load_project_from_mergin()

    def open_validation_form(self, collected_data=None, original_data=None):
        if not self.mergin_validation_ready and collected_data is None:
            QMessageBox.warning(
                self.iface.mainWindow(),
                self.tr(u'Validation non disponible'),
                self.tr(u"Veuillez importer des données (Mergin ou locales) avant de valider.")
            )
            return

        c_data = collected_data if collected_data is not None else self.current_collected_data
        o_data = original_data if original_data is not None else self.current_original_data
        self.load_collected_data(c_data, o_data)

    # ─────────────────────────────────────────────────────────────────────
    # ACTIONS SIG
    # ─────────────────────────────────────────────────────────────────────

    def migrate_project_layers_to_api(self):
        if not self.check_api_auth():
            return

        project_endpoints = self.get_project_layer_endpoints()
        if not project_endpoints:
            QMessageBox.information(
                self.iface.mainWindow(),
                self.tr(u'No API layers'),
                self.tr(u"Aucune couche mappée au format API n'a été trouvée dans le projet.")
            )
            return

        project = QgsProject.instance()
        new_layers = []
        errors = []
        commune_context = self.build_commune_filters()

        for layer_name, mapping in project_endpoints.items():
            try:
                filters = self.build_sector_filters(mapping, commune_context)
                db_data = [] if self.is_empty_filter(filters) else self.postgrest.select(mapping['endpoint'], filters=filters)
                layer = create_vector_layer(db_data, layer_name, mapping.get('geom_field'))
                if layer and layer.isValid():
                    layer.setCustomProperty('postgrest:endpoint', mapping['endpoint'])
                    geom_prop = mapping.get('geom_field')
                    if geom_prop:
                        layer.setCustomProperty('postgrest:geom_field', geom_prop)
                    else:
                        try:
                            layer.removeCustomProperty('postgrest:geom_field')
                        except Exception:
                            layer.setCustomProperty('postgrest:geom_field', '')
                    layer.setCustomProperty('postgrest:pk_field', mapping.get('pk_field', 'id'))
                    new_layers.append((layer_name, layer))
                else:
                    errors.append(self.tr(u'Impossible de créer la couche pour {name}').format(name=layer_name))
            except Exception as exc:
                if self.show_api_error_view(exc):
                    errors.append(self.tr(u'Erreur chargement API {name}: page d\'erreur affichée').format(name=layer_name))
                else:
                    errors.append(self.tr(u'Erreur chargement API {name}: {error}').format(name=layer_name, error=str(exc)))

        for layer_name, layer in new_layers:
            for existing in project.mapLayersByName(layer_name):
                project.removeMapLayer(existing.id())
            project.addMapLayer(layer)

        message = self.tr(u'Les couches du projet ont été mises à jour pour charger les données via l\'API.')
        if errors:
            message += '\n' + '\n'.join(errors)
        self.show_message(self.tr(u'Mise à jour des sources'), message, icon=QMessageBox.Information)

    def get_requested_endpoints(self, text_endpoint):
        if text_endpoint:
            return {text_endpoint: self.get_mapping_for_endpoint(text_endpoint)}
        endpoint_map = self.get_project_layer_endpoints()
        return endpoint_map if endpoint_map else {}

    def analyze_project_layers(self, apply_suggestions=False):
        analyzer = ProjectAnalyzer(self.load_layer_mappings())
        report = analyzer.analyze_active_project()

        updated_count = 0
        if apply_suggestions:
            for l_info in report['layers']:
                if l_info['status'] != 'suggested':
                    continue
                layer = QgsProject.instance().mapLayer(l_info['id'])
                if layer:
                    mapping = self.get_mapping_for_endpoint(l_info['mapping'])
                    layer.setCustomProperty('postgrest:endpoint', l_info['mapping'])
                    layer.setCustomProperty('postgrest:geom_field', mapping.get('geom_field', 'geom'))
                    updated_count += 1

        return report, updated_count

    def mapped_layers_from_report(self, report, include_suggestions=False):
        selected_mappings = {}
        for l_info in report.get('layers', []):
            if not l_info.get('mapping'):
                continue
            if not include_suggestions and l_info.get('status') != 'mapped':
                continue
            selected_mappings[l_info['id']] = l_info['mapping']
        return selected_mappings

    def confirm_project_mappings(self, report=None):
        if report is None:
            report, _ = self.analyze_project_layers()

        from .project_action_dialog import ProjectActionDialog
        dialog = ProjectActionDialog(
            self.iface.mainWindow(),
            report['layers'],
            list(self.load_layer_mappings().keys())
        )
        if dialog.exec_() != ProjectActionDialog.Accepted:
            return None, None
        return dialog.get_results()

    def get_or_confirm_terrain_mappings(self, selected_mappings=None):
        if selected_mappings:
            return selected_mappings

        report, _ = self.analyze_project_layers()
        selected_mappings = self.mapped_layers_from_report(report, include_suggestions=False)
        if selected_mappings:
            self.dockwidget.merginResultsTextEdit.append(
                f"✅ {len(selected_mappings)} couches déjà mappées réutilisées."
            )
            return selected_mappings

        _, selected_mappings = self.confirm_project_mappings(report)
        return selected_mappings

    def analyze_and_process_project(self):
        if not self.check_api_auth():
            return

        report, updated_count = self.analyze_project_layers(apply_suggestions=True)

        msg = f"Analyse terminée : {len(report['layers'])} couches détectées.\n"
        if updated_count > 0:
            msg += f"{updated_count} mappings automatiques appliqués."

        self.dockwidget.merginResultsTextEdit.setPlainText(msg)

        action, selected_mappings = self.confirm_project_mappings(report)
        if action is None:
            return
        if action == "migrate":
            self.push_project_data_to_backend(selected_mappings)
        elif action == "refresh":
            self.refresh_layers_from_api(selected_mappings)
        elif action == "update_mapping":
            self.update_local_layer_mapping(selected_mappings)
        else:
            self.auto_deploy_mission(selected_mappings)

    def refresh_layers_from_api(self, selected_mappings):
        """Met à jour les couches QGIS avec les dernières données du serveur."""
        if not self.check_api_auth():
            return

        self.dockwidget.merginResultsTextEdit.append("🔄 Rafraîchissement des couches depuis l'API...")
        commune_context = self.build_commune_filters()
        updated_count = 0
        error_count = 0

        for layer_id, mapping_result in selected_mappings.items():
            endpoint, field_map = self._extract_endpoint_and_field_map(mapping_result)

            layer = QgsProject.instance().mapLayer(layer_id)
            if not layer:
                continue

            try:
                mapping = self.get_mapping_for_endpoint(endpoint)
                filters = self.build_sector_filters(mapping, commune_context)
                db_data = [] if self.is_empty_filter(filters) else self.postgrest.select(endpoint, filters=filters)

                if not db_data:
                    layer.startEditing()
                    layer.deleteFeatures([f.id() for f in layer.getFeatures()])
                    layer.commitChanges()
                    updated_count += 1
                    continue

                new_layer = create_vector_layer(db_data, layer.name(), mapping.get('geom_field', 'geom'))
                if new_layer and new_layer.isValid():
                    pr = layer.dataProvider()
                    if pr:
                        layer.startEditing()
                        layer.deleteFeatures([f.id() for f in layer.getFeatures()])
                        layer.addFeatures(list(new_layer.getFeatures()))
                        layer.commitChanges()
                        updated_count += 1
                else:
                    error_count += 1
            except Exception as e:
                self.dockwidget.merginResultsTextEdit.append(f"❌ Erreur {endpoint} : {str(e)}")
                error_count += 1

        msg = f"Mise à jour terminée : {updated_count} couches rafraîchies."
        if error_count > 0:
            msg += f" ({error_count} erreurs)"

        self.dockwidget.merginResultsTextEdit.append(f"✅ {msg}")
        self.show_info("Mise à jour", msg)

    def auto_deploy_mission(self, selected_mappings=None):
        """Déploiement terrain automatisé (GPKG + API Mergin)."""
        if not self.check_api_auth():
            return

        self.set_progress(10, "🚀 Début du déploiement automatisé...")

        selected_mappings = self.get_or_confirm_terrain_mappings(selected_mappings)
        if selected_mappings is None:
            self.dockwidget.merginResultsTextEdit.append("⚠️ Déploiement annulé par l'utilisateur.")
            self.set_progress(0)
            return

        if not selected_mappings:
            self.show_error("Erreur", "Aucune couche mappée sélectionnée pour le déploiement.")
            return

        timestamp = __import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')
        district = self.get_sector_filter_value()
        district_slug = self.mergin_bridge.safe_project_name(district) if district else ""
        suggested_name = f"mission_{district_slug}_{timestamp}" if district_slug else f"mission_{timestamp}"

        # Dialogue de confirmation et renommage
        dialog = MissionConfirmationDialog(self.iface.mainWindow(), suggested_name, len(selected_mappings))
        if not dialog.exec_():
            self.dockwidget.merginResultsTextEdit.append("⚠️ Déploiement annulé par l'utilisateur.")
            self.set_progress(0)
            return

        project_name = dialog.get_project_name()
        if not project_name:
            self.show_error("Erreur", "Le nom du projet ne peut pas être vide.")
            self.set_progress(0)
            return

        # Normaliser selected_mappings vers {layer_id: endpoint} pour build_mission_layer_specs
        normalized_mappings = {}
        for lid, mapping_result in selected_mappings.items():
            endpoint, _ = self._extract_endpoint_and_field_map(mapping_result)
            normalized_mappings[lid] = endpoint

        project_id = self.mergin_manager.create_project(project_name, list(normalized_mappings.values()))
        self.current_project_id = project_id

        from .layer_utils import export_to_geopackage
        project_dir = os.path.join(self.mergin_manager.projects_dir, project_id)
        gpkg_path = os.path.join(project_dir, f"mission_data.gpkg")

        layer_specs = self.build_mission_layer_specs(normalized_mappings)
        layers_to_export = {gpkg_name: spec['layer'] for gpkg_name, spec in layer_specs.items()}

        success, err = export_to_geopackage(layers_to_export, gpkg_path)
        if not success:
            self.show_error("Erreur Export GPKG", err)
            return

        self.mergin_manager.save_exported_gpkg(project_id, gpkg_path)

        project_file = self.create_mergin_mission_project(project_name, project_dir, gpkg_path, layer_specs)
        if not project_file:
            return

        snapshot_data = {}
        for spec in layer_specs.values():
            ep = spec.get('endpoint')
            if not ep:
                continue
            layer = spec['layer']
            snapshot_data[ep] = layer_to_list_of_dicts(layer)
        self.mergin_manager.save_exported_data(project_id, snapshot_data)

        self.set_progress(50, f"📦 Projet QGIS + GeoPackage créés : {len(layers_to_export)} couches.")
        self.dockwidget.merginResultsTextEdit.append(
            f"📦 Projet QGIS + GeoPackage créés : {len(layers_to_export)} couches."
        )

        if self.mergin_bridge.is_connected():
            self.dockwidget.merginResultsTextEdit.append(
                f"☁️ Création du projet '{project_name}' via le plugin Mergin Maps connecté..."
            )
            try:
                full_project_name = self.mergin_bridge.create_project_and_push(project_name, project_dir)
                self.dockwidget.merginResultsTextEdit.append(
                    f"✅ Projet '{full_project_name}' prêt sur Mergin Maps !"
                )
            except Exception as e:
                self.dockwidget.merginResultsTextEdit.append(f"❌ Erreur plugin Mergin Maps : {str(e)}")
        elif hasattr(self, 'mergin_api') and self.mergin_api.token:
            self.dockwidget.merginResultsTextEdit.append(f"☁️ Création du projet '{project_name}' sur Mergin Maps...")
            try:
                namespace = self.mergin_api.username
                if self.mergin_api.create_project(namespace, project_name):
                    self.mergin_api.upload_file(namespace, project_name, gpkg_path, "mission_data.gpkg")
                    self.mergin_api.upload_file(namespace, project_name, project_file, os.path.basename(project_file))
                    self.dockwidget.merginResultsTextEdit.append(f"✅ Projet '{project_name}' prêt sur Mergin !")
                else:
                    self.dockwidget.merginResultsTextEdit.append("❌ Échec création projet Mergin.")
            except Exception as e:
                self.dockwidget.merginResultsTextEdit.append(f"❌ Erreur API Mergin : {str(e)}")
        else:
            self.dockwidget.merginResultsTextEdit.append(
                f"⚠️ {self.mergin_bridge.connection_label()}. Projet local uniquement."
            )

        self.set_progress(100, f"La mission '{project_name}' est prête.")
        self.show_info("Déploiement Réussi",
                                f"La mission '{project_name}' est prête.")

    def build_mission_layer_specs(self, selected_mappings):
        project = QgsProject.instance()
        layer_specs = {}
        used_names = set()
        selected_layer_ids = set(selected_mappings.keys())

        for lid, endpoint in selected_mappings.items():
            layer = project.mapLayer(lid)
            if not layer:
                continue
            gpkg_name = self.unique_gpkg_layer_name(endpoint, used_names)
            layer_specs[gpkg_name] = {'layer': layer, 'endpoint': endpoint, 'mapped': True}

        support_layer_ids = self.collect_form_support_layer_ids(selected_layer_ids)
        skipped_support_count = 0

        for layer in project.mapLayers().values():
            if layer.type() != QgsMapLayer.VectorLayer:
                continue
            if layer.id() in selected_layer_ids:
                continue
            if layer.id() not in support_layer_ids:
                skipped_support_count += 1
                continue
            if not layer.isValid():
                continue
            gpkg_name = self.unique_gpkg_layer_name(layer.name(), used_names)
            layer_specs[gpkg_name] = {'layer': layer, 'endpoint': None, 'mapped': False}

        support_count = sum(1 for spec in layer_specs.values() if not spec.get('mapped'))
        if support_count and self.dockwidget:
            self.dockwidget.merginResultsTextEdit.append(
                f"🔗 {support_count} couches support non mappées conservées pour les formulaires."
            )
        if skipped_support_count and self.dockwidget:
            self.dockwidget.merginResultsTextEdit.append(
                f"⚡ {skipped_support_count} couches non utilisées ignorées pour accélérer l'export terrain."
            )

        return layer_specs

    def collect_form_support_layer_ids(self, selected_layer_ids):
        """
        Retourne les couches non mappées réellement nécessaires aux formulaires.

        QGIS stocke les couches de widgets comme ValueRelation dans la config
        des champs, souvent sous une cle "Layer". Exporter seulement ces
        couches evite de copier tout le projet dans le GeoPackage terrain.
        """
        project = QgsProject.instance()
        support_ids = set()
        visited_ids = set()
        pending_ids = list(selected_layer_ids)

        while pending_ids:
            layer_id = pending_ids.pop()
            if layer_id in visited_ids:
                continue
            visited_ids.add(layer_id)

            layer = project.mapLayer(layer_id)
            if not layer or layer.type() != QgsMapLayer.VectorLayer:
                continue

            for ref_id in self.form_referenced_layer_ids(layer):
                if ref_id in visited_ids or not project.mapLayer(ref_id):
                    continue
                if ref_id not in selected_layer_ids:
                    support_ids.add(ref_id)
                pending_ids.append(ref_id)

        return support_ids

    def form_referenced_layer_ids(self, layer):
        referenced_ids = set()
        for idx in range(layer.fields().count()):
            try:
                setup = layer.editorWidgetSetup(idx)
                self.collect_layer_ids_from_value(setup.config(), referenced_ids)
            except Exception:
                continue
        return referenced_ids

    def collect_layer_ids_from_value(self, value, referenced_ids):
        project = QgsProject.instance()

        if isinstance(value, dict):
            for key, item in value.items():
                key_text = str(key).lower()
                if key_text in ('layer', 'layerid', 'layer_id'):
                    if isinstance(item, str):
                        ref_layer = project.mapLayer(item)
                        if ref_layer:
                            referenced_ids.add(ref_layer.id())
                    continue
                self.collect_layer_ids_from_value(item, referenced_ids)
            return

        if isinstance(value, (list, tuple)):
            for item in value:
                self.collect_layer_ids_from_value(item, referenced_ids)

    def unique_gpkg_layer_name(self, name, used_names):
        base_name = self.mergin_bridge.safe_project_name(name)
        candidate = base_name
        suffix = 2
        while candidate.lower() in used_names:
            candidate = "{}_{}".format(base_name, suffix)
            suffix += 1
        used_names.add(candidate.lower())
        return candidate

    def create_mergin_mission_project(self, project_name, project_dir, gpkg_path, layer_specs):
        project_file = os.path.join(project_dir, f"{project_name}.qgz")
        mission_project = QgsProject()
        current_project = QgsProject.instance()
        mission_project.setCrs(current_project.crs())
        mission_project.setTitle(project_name)

        # Ajouter Google Hybrid comme fond de carte SI présent dans le projet actuel
        # (XYZ Layer: https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z})
        google_hybrid_url = "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}"
        has_google_hybrid = False
        for lyr in current_project.mapLayers().values():
            if isinstance(lyr, QgsRasterLayer) and google_hybrid_url in lyr.source():
                has_google_hybrid = True
                break

        google_layer = None
        if has_google_hybrid:
            full_google_url = "type=xyz&url=" + google_hybrid_url
            google_layer = QgsRasterLayer(full_google_url, "Google Hybrid", "wms")
            if google_layer.isValid():
                mission_project.addMapLayer(google_layer)
                # On le met tout en bas de l'arbre des couches
                root = mission_project.layerTreeRoot()
                node = root.findLayer(google_layer.id())
                if node:
                    clone = node.clone()
                    root.insertChildNode(-1, clone)
                    root.removeChildNode(node)
            else:
                print("Failed to create Google Hybrid layer")
                google_layer = None

        added_layer_ids = {google_layer.id()} if google_layer and google_layer.isValid() else set()
        errors = []
        target_layers_by_source_id = {}
        for gpkg_name, spec in layer_specs.items():
            source_layer = spec['layer']
            uri = "{}|layername={}".format(gpkg_path, gpkg_name)
            layer = QgsVectorLayer(uri, source_layer.name(), "ogr")
            if not layer.isValid():
                errors.append(gpkg_name)
                continue

            endpoint = spec.get('endpoint')
            if endpoint:
                mapping = self.get_mapping_for_endpoint(endpoint)
                layer.setCustomProperty('postgrest:endpoint', endpoint)
                geom_prop = mapping.get('geom_field')
                if geom_prop:
                    layer.setCustomProperty('postgrest:geom_field', geom_prop)
                else:
                    try:
                        layer.removeCustomProperty('postgrest:geom_field')
                    except Exception:
                        layer.setCustomProperty('postgrest:geom_field', '')
                layer.setCustomProperty('postgrest:pk_field', mapping.get('pk_field', 'id'))
            self.copy_layer_style(source_layer, layer)
            self.copy_layer_form(source_layer, layer)
            if endpoint:
                self.configure_operator_capture_for_mergin_layer(layer, mapping)
            mission_project.addMapLayer(layer, False)
            target_layers_by_source_id[source_layer.id()] = layer

        self.remap_form_layer_references(target_layers_by_source_id)
        self.copy_layer_tree_structure(current_project, mission_project, target_layers_by_source_id, added_layer_ids)

        if errors:
            self.show_message(
                "Erreur Projet QGIS",
                "Impossible de créer les couches du projet Mergin : {}".format(", ".join(errors))
            )
            return None

        if not mission_project.write(project_file):
            self.show_message("Erreur Projet QGIS", "Impossible d'écrire le projet QGIS dans le dossier Mergin.")
            return None

        return project_file

    def configure_operator_capture_for_mergin_layer(self, layer, mapping):
        """Default uuid_operateur to the logged-in user for field edits in Mergin Maps."""
        user_uuid = self.current_user_uuid()
        if not user_uuid or not self.mapping_has_column(mapping, 'uuid_operateur'):
            return

        field_idx = self.field_index_by_name(layer, 'uuid_operateur')
        if field_idx < 0:
            return

        escaped_uuid = str(user_uuid).replace("'", "''")
        try:
            layer.setDefaultValueDefinition(field_idx, QgsDefaultValue("'{}'".format(escaped_uuid), True))
        except Exception:
            pass

    def copy_layer_style(self, source_layer, target_layer):
        try:
            style = QgsMapLayerStyle()
            style.readFromLayer(source_layer)
            style.writeToLayer(target_layer)
        except Exception:
            try:
                renderer = source_layer.renderer()
                if renderer:
                    target_layer.setRenderer(renderer.clone())
                labeling = source_layer.labeling()
                if labeling:
                    target_layer.setLabeling(labeling.clone())
                    target_layer.setLabelsEnabled(source_layer.labelsEnabled())
                target_layer.setOpacity(source_layer.opacity())
            except Exception:
                pass

    def copy_layer_form(self, source_layer, target_layer):
        try:
            target_layer.setEditFormConfig(source_layer.editFormConfig())
        except Exception:
            pass
        try:
            for idx in range(source_layer.fields().count()):
                target_layer.setEditorWidgetSetup(idx, source_layer.editorWidgetSetup(idx))
        except Exception:
            pass

    def remap_form_layer_references(self, target_layers_by_source_id):
        layer_id_map = {
            source_id: target_layer.id()
            for source_id, target_layer in target_layers_by_source_id.items()
        }
        if not layer_id_map:
            return

        def remap_value(value):
            if isinstance(value, str):
                return layer_id_map.get(value, value)
            if isinstance(value, list):
                return [remap_value(item) for item in value]
            if isinstance(value, tuple):
                return tuple(remap_value(item) for item in value)
            if isinstance(value, dict):
                return {key: remap_value(item) for key, item in value.items()}
            return value

        for target_layer in target_layers_by_source_id.values():
            for idx in range(target_layer.fields().count()):
                try:
                    setup = target_layer.editorWidgetSetup(idx)
                    config = dict(setup.config())
                    remapped_config = remap_value(config)
                    if remapped_config != config:
                        target_layer.setEditorWidgetSetup(
                            idx,
                            QgsEditorWidgetSetup(setup.type(), remapped_config)
                        )
                except Exception:
                    continue

    def copy_layer_tree_structure(self, source_project, target_project, target_layers_by_source_id, added_layer_ids):
        target_root = target_project.layerTreeRoot()
        source_root = source_project.layerTreeRoot()

        def set_visibility(source_node, target_node):
            try:
                target_node.setItemVisibilityChecked(source_node.itemVisibilityChecked())
            except Exception:
                pass
            try:
                target_node.setExpanded(source_node.isExpanded())
            except Exception:
                pass

        def copy_children(source_group, target_group):
            for source_node in source_group.children():
                if hasattr(source_node, "layerId"):
                    target_layer = target_layers_by_source_id.get(source_node.layerId())
                    if not target_layer:
                        continue
                    target_node = target_group.addLayer(target_layer)
                    set_visibility(source_node, target_node)
                    added_layer_ids.add(target_layer.id())
                    continue
                if not hasattr(source_node, "children"):
                    continue
                child_count_before = len(added_layer_ids)
                target_child_group = target_group.addGroup(source_node.name())
                set_visibility(source_node, target_child_group)
                copy_children(source_node, target_child_group)
                if len(added_layer_ids) == child_count_before:
                    target_group.removeChildNode(target_child_group)

        copy_children(source_root, target_root)

        # S'assurer que les couches cibles qui ne sont pas dans l'arbre (non groupées) sont ajoutées
        # mais on veut Google Hybrid en bas si possible.
        for target_layer in target_layers_by_source_id.values():
            if target_layer.id() not in added_layer_ids:
                # addLayer l'ajoute en haut par défaut. On l'insère à l'index 0 du root (en haut)
                # car Google Hybrid est déjà tout en bas (-1).
                target_root.insertChildNode(0, target_root.findLayer(target_layer.id()) or target_root.addLayer(target_layer))
                added_layer_ids.add(target_layer.id())

    def auto_import_mission(self, open_validation=False):
        self.dockwidget.merginResultsTextEdit.append("📥 Récupération des données terrain...")

        analyzer = ProjectAnalyzer(self.load_layer_mappings())
        report = analyzer.analyze_active_project()
        mapped_layers = [l for l in report['layers'] if l['mapping']]

        if not mapped_layers:
            self.show_warning("Importation", "Aucune couche mappée détectée dans le projet actif.")
            return

        self.set_progress(30, f"🔍 Analyse de {len(mapped_layers)} couches mappées...")
        self.dockwidget.merginResultsTextEdit.append(f"🔍 Analyse de {len(mapped_layers)} couches mappées...")

        collected_payload = {}
        original_payload = {}
        commune_context = self.build_commune_filters()

        for l_info in mapped_layers:
            layer = QgsProject.instance().mapLayer(l_info['id'])
            endpoint = l_info['mapping']
            mapping = self.get_mapping_for_endpoint(endpoint)

            # Récupérer le field_map depuis le mapping local s'il existe
            field_map = mapping.get('field_map', {})

            local_data = layer_to_list_of_dicts(layer, geom_field=mapping.get('geom_field', 'geom'))

            # ← Appliquer le field_map
            local_data = self._apply_field_map(local_data, field_map)

            collected_payload[endpoint] = local_data

            try:
                filters = self.build_sector_filters(mapping, commune_context)
                original_payload[endpoint] = [] if self.is_empty_filter(filters) else self.postgrest.select(endpoint, filters=filters)
            except Exception:
                original_payload[endpoint] = []

        self.current_collected_data = collected_payload
        self.current_original_data = original_payload
        self.mergin_validation_ready = True
        self.set_validation_ready(True)

        self.set_progress(100, f"✅ Analyse terminée. {len(collected_payload)} tables prêtes pour validation.")
        self.dockwidget.merginResultsTextEdit.append(
            f"✅ Analyse terminée. {len(collected_payload)} tables prêtes pour validation."
        )
        if open_validation:
            self.auto_validate_mission()

    def auto_validate_mission(self):
        if not self.check_api_auth():
            return

        if not self.is_current_user_validator():
            self.show_warning(
                self.tr(u'Accès refusé'),
                self.tr(u'Seul un validateur peut effectuer cette action.')
            )
            return

        if not self.mergin_validation_ready:
            self.auto_import_mission(open_validation=True)
            return
        self.open_validation_form(self.current_collected_data, self.current_original_data)

    def auto_finalize_mission(self):
        if not self.check_api_auth():
            return

        if not self.is_current_user_validator():
            self.show_warning(
                self.tr(u'Accès refusé'),
                self.tr(u'Seul un validateur peut finaliser et synchroniser la mission.')
            )
            return

        self.sync_validated_data_to_backend()
        self.set_progress(0)

    def push_project_data_to_backend(self, selected_mappings=None):
        """Pousse les données sélectionnées vers le backend API."""
        if not self.check_api_auth():
            return

        project_endpoints = {}
        if selected_mappings:
            for lid, mapping_result in selected_mappings.items():
                endpoint, field_map = self._extract_endpoint_and_field_map(mapping_result)
                layer = QgsProject.instance().mapLayer(lid)
                if layer and layer.name() not in ['spatial_ref_sys', 'geometry_columns']:
                    mapping = self.get_mapping_for_endpoint(endpoint)
                    mapping['_field_map'] = field_map  # transport interne
                    project_endpoints[layer.name()] = mapping
        else:
            for layer in QgsProject.instance().mapLayers().values():
                if layer.type() != QgsMapLayer.VectorLayer or layer.name() in ['spatial_ref_sys', 'geometry_columns']:
                    continue
                endpoint = layer.customProperty('postgrest:endpoint')
                if endpoint:
                    mapping = self.get_mapping_for_endpoint(endpoint)
                    mapping['_field_map'] = mapping.get('field_map', {})
                    project_endpoints[layer.name()] = mapping

        if not project_endpoints:
            self.show_info(
                self.tr(u'No mapped layers'),
                self.tr(u"Aucune couche mappée n'a été trouvée.")
            )
            return

        if QMessageBox.question(
            self.iface.mainWindow(),
            self.tr(u'Confirmer la migration'),
            self.tr(u"Voulez-vous pousser les données de {count} couches vers la base de données ?").format(count=len(project_endpoints)),
            QMessageBox.Yes | QMessageBox.No
        ) != QMessageBox.Yes:
            return

        EXECUTION_ORDER = ["communes", "pg_infos","pg_gps", "membre", "bosquet_gps", "arbre_gps", "arbre_baseline"]

        def get_priority(pair):
            name = pair[1].get('endpoint', '').lower()
            return EXECUTION_ORDER.index(name) if name in EXECUTION_ORDER else len(EXECUTION_ORDER)

        sorted_endpoints = sorted(project_endpoints.items(), key=get_priority)
        HARD_MAPPINGS = {}

        project = QgsProject.instance()
        migration_data = []
        if self.dockwidget:
            self.dockwidget.merginResultsTextEdit.setPlainText(
                self.tr(u"Préparation des données locales pour la migration initiale...")
            )
        user_uuid = self.current_user_uuid()

        for layer_name, mapping in sorted_endpoints:
            layers = project.mapLayersByName(layer_name)
            if not layers:
                continue

            raw_data = layer_to_list_of_dicts(layers[0], geom_field=(mapping.get('geom_field') or 'geom'))
            if not raw_data:
                continue

            # ← Appliquer le field_map avant le nettoyage strict
            field_map = mapping.get('_field_map', {})
            raw_data = self._apply_field_map(raw_data, field_map)

            api_columns = [str(col).lower() for col in mapping.get('columns', [])]
            endpoint_name = mapping['endpoint'].lower()
            layer_is_spatial = bool(layers[0].isSpatial())
            geom_field = Utils.resolve_postgrest_geom_field(mapping.get('geom_field'), layer_is_spatial)
            field_override = HARD_MAPPINGS.get(endpoint_name, {})
            pk_field = mapping.get('pk_field', 'id').lower()
            data_to_push = []

            for idx, row in enumerate(raw_data, start=1):
                raw_geom = None
                if geom_field:
                    raw_geom = row.get(geom_field) or row.get('geom') or row.get('geometry')
                geom_value = None
                if raw_geom is not None:
                    geom_value = raw_geom.asWkt() if hasattr(raw_geom, 'asWkt') else (
                        raw_geom if isinstance(raw_geom, (str, dict)) else str(raw_geom) if raw_geom else None
                    )

                row_mapped = {}
                for k, v in row.items():
                    k_str = str(k).lower()
                    if k_str in [geom_field, 'geom', 'geometry']:
                        continue
                    row_mapped[field_override.get(k_str, k_str)] = v

                filtered_row = {}
                for col in api_columns:
                    val = row_mapped.get(col)
                    filtered_row[col] = None if val == "" else val
                
                # Préserver les champs UUID/ID qui ont été mappés via field_map
                # Prendre la valeur du champ ORIGINAL (avant renommage) pour les UUID
                for original_field, mapped_field in field_map.items():
                    if mapped_field:  # Champ inclus dans le mapping
                        mapped_lower = mapped_field.lower()
                        # Vérifier si c'est un UUID ou un champ d'ID qui doit être préservé
                        is_special_field = (mapped_lower.startswith('uuid') or 
                                          mapped_lower == 'id' or 
                                          mapped_lower.endswith('_id') or
                                          mapped_lower.endswith('_uuid'))
                        
                        if is_special_field and mapped_lower in [c.lower() for c in api_columns]:
                            # Prendre la valeur du champ original dans row (pas row_mapped)
                            val = row.get(original_field)
                            if val is not None:
                                filtered_row[mapped_lower] = val

                # Ne pas remplir le pk_field si c'est un UUID explicitement mappé
                is_uuid_field = pk_field.startswith('uuid') or pk_field.endswith('_uuid')
                if pk_field in api_columns and not is_uuid_field and filtered_row.get(pk_field) is None:
                    fid_val = row_mapped.get('fid') or row_mapped.get('id_0') or row_mapped.get('gid')
                    filtered_row[pk_field] = fid_val if fid_val is not None else idx

                if geom_field:
                    filtered_row[geom_field] = geom_value

                if 'uuid_operateur' in api_columns and user_uuid and not filtered_row.get('uuid_operateur'):
                    filtered_row['uuid_operateur'] = user_uuid
                if 'uuid_verificateur' in api_columns and user_uuid and not filtered_row.get('uuid_verificateur'):
                    filtered_row['uuid_verificateur'] = user_uuid
                filtered_row = self.normalize_backend_defaults(filtered_row, mapping, user_uuid=user_uuid)

                # Ne jamais réécrire ni déplacer les colonnes UUID/PK vers d'autres champs.
                # Les valeurs de uuid_pg, uuid_membre, uuid_arbre_gps, etc. doivent rester
                # dans la colonne qui a été explicitement mappée dans le payload.
                for key in list(filtered_row.keys()):
                    key_lower = str(key).lower()
                    if key_lower == 'c_com':
                        continue
                    if key_lower in {'uuid_operateur', 'uuid_verificateur'}:
                        continue
                    if key_lower.startswith('uuid') or key_lower == 'id' or key_lower.endswith('_id'):
                        continue

                data_to_push.append(filtered_row)

            conflict_field = self.conflict_field_for_mapping(mapping)
            migration_data.append((layer_name, mapping['endpoint'], conflict_field, data_to_push))


        if not migration_data:
            self.show_message(self.tr(u'Migration'), self.tr(u"Aucune donnée valide à migrer."))
            return

        total_rows = sum(len(data) for _, _, _, data in migration_data)
        self.show_info(
            self.tr(u'Migration'),
            self.tr(
                u"Les données de {count} couche(s), soit {rows} ligne(s), vont être migrées vers la base de données."
            ).format(count=len(migration_data), rows=total_rows)
        )

        self.active_migration_task = QgsTask.fromFunction(
            self.tr(u'Migration des données MrvTeraka'), self._do_migration_task,
            migration_data=migration_data, postgrest_client=self.postgrest,
            on_finished=self._on_migration_finished
        )
        QgsApplication.taskManager().addTask(self.active_migration_task)
        if self.dockwidget:
            self.dockwidget.merginResultsTextEdit.setPlainText(self.tr(u"Migration en cours..."))

    @staticmethod
    def _postgres_error_explanation(code):
        explanations = {
            '23503': "Clé étrangère manquante: une donnée liée n'existe pas encore dans la table parente.",
            '23505': "Doublon: une valeur unique existe déjà.",
            '23502': "Champ obligatoire manquant: une colonne NOT NULL reçoit une valeur vide.",
            '22P02': "Format invalide: souvent un UUID, nombre ou date mal formé.",
            '42804': "Type de donnée incompatible avec la colonne cible.",
            '42703': "Colonne introuvable dans la table ou la vue PostgREST.",
            '42P01': "Table ou vue introuvable dans le schéma exposé.",
            'PGRST204': "Colonne introuvable dans le cache de schéma PostgREST. Recharger le cache ou vérifier le mapping.",
        }
        return explanations.get(str(code or ''), "")

    @staticmethod
    def _extract_constraint_name(*texts):
        for text in texts:
            if not text:
                continue
            match = re.search(r'constraint "([^"]+)"', str(text), re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def _sample_row_identifier(rows):
        if not rows:
            return None
        row = rows[0]
        if not isinstance(row, dict):
            return None
        for key in ('id', 'uuid_bosquet_gps', 'uuid_pg_gps', 'uuid_pg', 'uuid_membre', 'uuid_arbre_gps'):
            value = row.get(key)
            if value not in (None, ""):
                return f"{key}={value}"
        return None

    @staticmethod
    def _format_postgrest_error(exc, layer_name, endpoint, start_idx, end_idx, rows):
        if isinstance(exc, PostgRESTError):
            code = exc.code or "Inconnu"
            if not rows:
                packet_label = "Requête"
            elif len(rows) == 1:
                packet_label = f"Ligne {start_idx + 1}"
            else:
                packet_label = f"Paquet {start_idx}-{end_idx}"
            lines = [
                f"{layer_name} -> {endpoint} [{packet_label}]",
                f"HTTP {exc.status_code} {exc.reason}",
                f"Code: {code}",
            ]
            if exc.message:
                lines.append(f"Message: {exc.message}")
            if exc.details:
                lines.append(f"Détails: {exc.details}")
            if exc.hint:
                lines.append(f"Indice: {exc.hint}")

            constraint = MrvTeraka._extract_constraint_name(exc.message, exc.details)
            if constraint:
                lines.append(f"Contrainte: {constraint}")

            explanation = MrvTeraka._postgres_error_explanation(code)
            if explanation:
                lines.append(f"Diagnostic: {explanation}")

            sample_id = MrvTeraka._sample_row_identifier(rows)
            if sample_id:
                row_label = "Ligne concernée" if len(rows) == 1 else "Première ligne du paquet"
                lines.append(f"{row_label}: {sample_id}")
            if rows and len(rows) > 1:
                lines.append(
                    "Note: ce paquet est conservé groupé pour accélérer la migration; "
                    "une des lignes du paquet contient probablement l'erreur."
                )
            return "\n".join(lines)

        return f"{layer_name} -> {endpoint} [Paquet {start_idx}-{end_idx}]\n{str(exc)}"

    @staticmethod
    def _is_probably_row_level_postgrest_error(exc):
        if not isinstance(exc, PostgRESTError):
            return False
        return str(exc.code or '') in {'23503', '23502', '22P02', '22007', '22008', '22003', '23514'}

    @staticmethod
    def _insert_rows_with_diagnostics(
        postgrest_client, endpoint, rows, conflict_field, layer_name, start_idx, results,
        min_diagnostic_batch_size=100
    ):
        if not rows:
            return 0, 0

        try:
            postgrest_client.insert(
                endpoint,
                rows,
                upsert=True,
                on_conflict=conflict_field,
                show_error_ui=False,
            )
            return len(rows), 0
        except Exception as exc:
            if len(rows) <= min_diagnostic_batch_size or not MrvTeraka._is_probably_row_level_postgrest_error(exc):
                error_msg = MrvTeraka._format_postgrest_error(
                    exc, layer_name, endpoint, start_idx, start_idx + len(rows), rows
                )
                results.append(f"❌ {error_msg}")
                return 0, 1

            midpoint = len(rows) // 2
            left_ok, left_errors = MrvTeraka._insert_rows_with_diagnostics(
                postgrest_client,
                endpoint,
                rows[:midpoint],
                conflict_field,
                layer_name,
                start_idx,
                results,
                min_diagnostic_batch_size,
            )
            right_ok, right_errors = MrvTeraka._insert_rows_with_diagnostics(
                postgrest_client,
                endpoint,
                rows[midpoint:],
                conflict_field,
                layer_name,
                start_idx + midpoint,
                results,
                min_diagnostic_batch_size,
            )
            return left_ok + right_ok, left_errors + right_errors

    @staticmethod
    def _do_migration_task(task, migration_data, postgrest_client):
        results, errors_count = [], 0
        CHUNK_SIZE = 1000
        MIN_DIAGNOSTIC_BATCH_SIZE = 100
        for i, (layer_name, endpoint, conflict_field, data) in enumerate(migration_data):
            if task.isCanceled():
                return {'results': results, 'status': 'canceled'}
            layer_errors, migrated_count = 0, 0

            for start_idx in range(0, len(data), CHUNK_SIZE):
                if task.isCanceled():
                    return {'results': results, 'status': 'canceled'}
                end_idx = min(start_idx + CHUNK_SIZE, len(data))
                chunk_data = data[start_idx:end_idx]
                inserted, row_errors = MrvTeraka._insert_rows_with_diagnostics(
                    postgrest_client,
                    endpoint,
                    chunk_data,
                    conflict_field,
                    layer_name,
                    start_idx,
                    results,
                    MIN_DIAGNOSTIC_BATCH_SIZE,
                )
                migrated_count += inserted
                layer_errors += row_errors
                errors_count += row_errors

            if layer_errors:
                results.append(
                    f"⚠️ {layer_name} -> {endpoint}: {migrated_count}/{len(data)} ligne(s) migrée(s), "
                    f"{layer_errors} erreur(s) de données."
                )
            else:
                results.append(f"✅ {layer_name} -> {endpoint}: {migrated_count} ligne(s) migrée(s).")

            task.setProgress((i + 1) / len(migration_data) * 100)
        return {'results': results, 'errors_count': errors_count, 'status': 'completed'}

    def _on_migration_finished(self, exception, result=None):
        self.active_migration_task = None
        if exception:
            self.show_error(self.tr(u'Erreur critique'), exception)
            return
        if not result or result.get('status') == 'canceled':
            self.show_info(self.tr(u'Migration'), self.tr(u"Migration annulée."))
            return
        report = "\n".join(result['results'])
        if self.dockwidget:
            self.dockwidget.merginResultsTextEdit.setPlainText(report)
        if result['errors_count'] > 0:
            self.show_warning(self.tr(u'Migration terminée avec erreurs'), report)
        else:
            self.show_info(self.tr(u'Migration réussie'), report)

    def _requested_api_mappings(self, selected_endpoints=None, fallback_to_project=False):
        if selected_endpoints:
            if isinstance(selected_endpoints, dict):
                requested = {}
                for layer_name, mapping in selected_endpoints.items():
                    if isinstance(mapping, dict):
                        endpoint = mapping.get('endpoint')
                        if endpoint and not self.is_system_endpoint(endpoint) and not self.is_system_endpoint(layer_name):
                            requested[layer_name] = mapping
                    elif mapping:
                        if not self.is_system_endpoint(mapping):
                            requested[layer_name] = self.get_mapping_for_endpoint(mapping)
                return requested

            return {
                name: mapping
                for name in selected_endpoints
                for mapping in [self.get_layer_mapping(name)]
                if mapping and mapping.get('endpoint') and not self.is_system_endpoint(mapping.get('endpoint'))
            }

        selected = self.dockwidget.get_selected_endpoints() if self.dockwidget else []
        if selected:
            return {
                name: mapping
                for name in selected
                for mapping in [self.get_layer_mapping(name)]
                if mapping and mapping.get('endpoint') and not self.is_system_endpoint(mapping.get('endpoint'))
            }

        return self.get_project_layer_endpoints() if fallback_to_project else {}

    def _find_existing_api_layer(self, layer_name, endpoint_value):
        for layer in QgsProject.instance().mapLayers().values():
            if layer.type() != QgsMapLayer.VectorLayer:
                continue
            if layer.customProperty('postgrest:endpoint') == endpoint_value:
                return layer

        for layer in QgsProject.instance().mapLayersByName(layer_name):
            if layer.type() == QgsMapLayer.VectorLayer:
                return layer
        return None

    def _create_api_layer_from_data(self, db_data, display_name, geom_field, endpoint_value):
        if is_geojson(db_data):
            import tempfile
            temp_file = None
            with tempfile.NamedTemporaryFile(mode='w', suffix='.geojson', delete=False, encoding='utf-8') as f:
                json.dump(db_data, f)
                temp_file = f.name

            new_layer = QgsVectorLayer(temp_file, display_name, 'ogr')
            if not new_layer.isValid():
                if temp_file and os.path.exists(temp_file):
                    os.unlink(temp_file)
                QMessageBox.critical(
                    self.iface.mainWindow(),
                    "Erreur",
                    f"GéoJSON invalide pour {endpoint_value}."
                )
                return None
            new_layer.setCustomProperty('mrv:temp_geojson_path', temp_file)
            return new_layer

        return create_vector_layer(db_data, display_name, geom_field)

    def _replace_or_add_api_layer(self, new_layer, existing_layer, endpoint_value, geom_field, mapping):
        preserved_style = None
        preserved_visibility = True
        preserved_opacity = 1.0
        layer_tree_index = None
        had_existing_layer = existing_layer is not None
        old_temp_geojson_path = None

        if had_existing_layer:
            existing_layer_id = existing_layer.id()
            old_temp_geojson_path = existing_layer.customProperty('mrv:temp_geojson_path')
            style_doc = QgsMapLayerStyle()
            style_doc.readFromLayer(existing_layer)
            preserved_style = style_doc
            preserved_opacity = existing_layer.opacity()

            root = QgsProject.instance().layerTreeRoot()
            existing_node = root.findLayer(existing_layer_id)
            if existing_node:
                preserved_visibility = existing_node.itemVisibilityChecked()
            for i, child in enumerate(root.children()):
                if hasattr(child, 'layer') and child.layer() and child.layer().id() == existing_layer_id:
                    layer_tree_index = i
                    break

            QgsProject.instance().removeMapLayer(existing_layer_id)
            existing_layer = None
            if old_temp_geojson_path and os.path.exists(old_temp_geojson_path):
                try:
                    os.unlink(old_temp_geojson_path)
                except OSError:
                    pass

        new_layer.setCustomProperty('postgrest:endpoint', endpoint_value)
        new_layer.setCustomProperty('postgrest:geom_field', geom_field)
        new_layer.setCustomProperty('postgrest:pk_field', mapping.get('pk_field', 'id'))

        if had_existing_layer and layer_tree_index is not None:
            root = QgsProject.instance().layerTreeRoot()
            QgsProject.instance().addMapLayer(new_layer, False)
            new_node = root.insertLayer(layer_tree_index, new_layer)
        else:
            QgsProject.instance().addMapLayer(new_layer)
            new_node = QgsProject.instance().layerTreeRoot().findLayer(new_layer.id())

        if preserved_style:
            preserved_style.writeToLayer(new_layer)
        if new_node:
            new_node.setItemVisibilityChecked(preserved_visibility)
        new_layer.setOpacity(preserved_opacity)

    def load_database_data(self, selected_endpoints=None, update_existing_only=False):
        if not self.dockwidget or not self.check_api_auth():
            return

        commune_context = self.build_commune_filters()
        requested_endpoints = self._requested_api_mappings(
            selected_endpoints=selected_endpoints,
            fallback_to_project=update_existing_only
        )

        if not requested_endpoints:
            message = (
                self.tr(u'Aucune couche QGIS mappée à actualiser.')
                if update_existing_only else
                self.tr(u'Aucune table sélectionnée à charger depuis l\'API.')
            )
            self.show_warning(
                self.tr(u'Erreur'),
                message
            )
            return

        try:
            updated_count = 0
            skipped_count = 0
            for layer_name, mapping in requested_endpoints.items():
                endpoint_value = mapping['endpoint']
                if self.is_system_endpoint(layer_name) or self.is_system_endpoint(endpoint_value):
                    skipped_count += 1
                    continue
                filters = self.build_sector_filters(mapping, commune_context)
                db_data = [] if self.is_empty_filter(filters) else self.postgrest.select(endpoint_value, filters=filters, page_size=5000)
                display_name = f"{layer_name} ({endpoint_value})"
                geom_field = mapping.get('geom_field', 'geom')
                existing_layer = self._find_existing_api_layer(layer_name, endpoint_value)

                if update_existing_only and not existing_layer:
                    skipped_count += 1
                    continue

                if not db_data:
                    skipped_count += 1
                    continue

                new_layer = self._create_api_layer_from_data(db_data, display_name, geom_field, endpoint_value)
                if not new_layer or not new_layer.isValid():
                    skipped_count += 1
                    continue

                self._replace_or_add_api_layer(new_layer, existing_layer, endpoint_value, geom_field, mapping)
                updated_count += 1

            title = self.tr(u'Actualisation terminée') if update_existing_only else self.tr(u'Chargement terminé')
            action = self.tr(u'mise(s) à jour') if update_existing_only else self.tr(u'chargée(s)')
            message = self.tr(u'{0} couche(s) {1} depuis l\'API.').format(updated_count, action)
            if skipped_count:
                message += self.tr(u'\n{0} table(s) ignorée(s): aucune couche existante ou aucune donnée disponible.').format(skipped_count)
            self.show_info(
                title,
                message
            )
        except Exception as exc:
            self.show_error(self.tr(u'Erreur'), exc)

    def compare_project_with_db(self):
        if not self.dockwidget or not self.check_api_auth():
            return

        selected = self.dockwidget.get_selected_endpoints()
        commune_context = self.build_commune_filters()
        
        if selected:
            requested_endpoints = {
                name: mapping
                for name in selected
                for mapping in [self.get_layer_mapping(name)]
                if mapping and mapping.get('endpoint')
            }
        else:
            requested_endpoints = self.get_project_layer_endpoints()

        if not requested_endpoints:
            self.show_warning(
                self.tr(u'Erreur'),
                self.tr(u'Aucun endpoint configuré ou aucune couche vectorielle détectée dans le projet.')
            )
            return

        try:
            report = [f"Statut : Connecté à {self.api_base_url}"]

            sector = self.get_sector_filter_value()
            if sector:
                report.append(f"Filtre Secteur : {sector}")

            commune_codes = self.get_selected_commune_codes()
            if commune_codes:
                report.append(f"Communes sélectionnées : {len(commune_codes)}")

            for layer_name, mapping in requested_endpoints.items():
                endpoint_value = mapping['endpoint']
                filters = self.build_sector_filters(mapping, commune_context)
                count = 0 if self.is_empty_filter(filters) else len(self.postgrest.select(endpoint_value, select="id", filters=filters))
                report.append(f"{layer_name} -> {endpoint_value} : {count} enregistrements")

            qgis_layers = [l.name() for l in QgsProject.instance().mapLayers().values() if l.type() == QgsMapLayer.VectorLayer]
            report.append(f"Couches locales vectorielles détectées : {len(qgis_layers)}")

            self.dockwidget.comparisonResultsTextEdit.setPlainText("\n".join(report))
        except Exception as exc:
            self.show_error("Erreur", exc)

    def load_collected_data(self, collected_data=None, original_data=None):
        if not self.dockwidget or not self.check_api_auth():
            return

        if not self.is_current_user_validator():
            self.show_warning(
                self.tr(u'Accès refusé'),
                self.tr(u'Seul un validateur peut charger et valider les données collectées.')
            )
            return

        selected = self.dockwidget.get_selected_endpoints()
        endpoint = selected[0] if selected else ""
        if not endpoint and collected_data is None:
            self.show_warning(
                self.tr(u'Erreur'),
                self.tr(u'Veuillez spécifier un endpoint.')
            )
            return

        try:
            provided_original_data = original_data
            if collected_data is None:
                mapping = self.get_mapping_for_endpoint(endpoint)
                commune_context = self.build_commune_filters()
                filters = self.build_sector_filters(mapping, commune_context)
                collected_data = [] if self.is_empty_filter(filters) else self.postgrest.select(mapping['endpoint'], filters=filters)
                self.current_data_mapping = mapping
            else:
                if isinstance(collected_data, dict) and len(collected_data) == 1:
                    endpoint_key = next(iter(collected_data.keys()))
                    collected_data = collected_data[endpoint_key]
                    self.current_data_mapping = self.get_mapping_for_endpoint(endpoint_key)
                else:
                    self.current_data_mapping = self.get_mapping_for_endpoint(endpoint)

            self.current_collected_data = collected_data

            original_data = provided_original_data if provided_original_data is not None else []
            if provided_original_data is None and self.current_project_id:
                metadata_file = os.path.join(
                    self.mergin_manager.projects_dir,
                    self.current_project_id,
                    'exported_data.json'
                )
                if os.path.exists(metadata_file):
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        original_data = json.load(f)

            if self.current_project_id:
                self.mergin_manager.import_collected_data(self.current_project_id, collected_data)

            validation_dialog = DataValidationDialog(
                parent=self.iface.mainWindow(),
                collected_data=collected_data,
                original_data=original_data if original_data is not None else []
            )

            if validation_dialog.exec_() == DataValidationDialog.Accepted:
                validated_data = validation_dialog.validated_data
                
                if isinstance(validated_data, dict) and not is_geojson(validated_data):
                    validated_data = {
                        endpoint: self.prepare_rows_for_mapping(
                            table_data,
                            self.get_mapping_for_endpoint(endpoint),
                            add_user_uuid=False,
                            add_verifier_uuid=True
                        )
                        for endpoint, table_data in validated_data.items()
                    }
                elif isinstance(validated_data, list):
                    selected = self.dockwidget.get_selected_endpoints()
                    endpoint = selected[0] if selected else ""
                    mapping = self.current_data_mapping or self.get_mapping_for_endpoint(endpoint)
                    validated_data = self.prepare_rows_for_mapping(
                        validated_data,
                        mapping,
                        add_user_uuid=False,
                        add_verifier_uuid=True
                    )

                validation_results = {
                    'status': 'approved',
                    'data_count': sum(len(rows) for rows in validated_data.values())
                    if isinstance(validated_data, dict) and not is_geojson(validated_data)
                    else len(validated_data),
                    'timestamp': str(__import__('datetime').datetime.now())
                }

                self.current_validated_data = validated_data
                self.set_sync_ready(True)

                if self.current_project_id:
                    self.mergin_manager.validate_data(self.current_project_id, validation_results)

                self.show_info(
                    self.tr(u'Validation terminée'),
                    self.tr(u'Les données validées sont prêtes pour la synchronisation backend.')
                )
        except Exception as exc:
            self.show_error(self.tr(u'Erreur'), exc)

    def sync_validated_data_to_backend(self):
        if not self.dockwidget or not self.check_api_auth():
            return

        if not self.current_validated_data:
            self.show_warning(
                self.tr(u'Synchronisation impossible'),
                self.tr(u"Aucune donnée validée n'a été trouvée. Veuillez d'abord valider des données.")
            )
            return

        sync_payloads = []
        if isinstance(self.current_validated_data, dict) and not is_geojson(self.current_validated_data):
            for endpoint, data in self.current_validated_data.items():
                sync_payloads.append((self.get_mapping_for_endpoint(endpoint), data))
        else:
            selected = self.dockwidget.get_selected_endpoints()
            endpoint = selected[0] if selected else ""
            mapping = self.current_data_mapping or self.get_mapping_for_endpoint(endpoint)
            sync_payloads.append((mapping, self.current_validated_data))

        # Utiliser un worker thread pour ne pas bloquer l'interface
        self.dockwidget.set_status_message("🚀 Synchronisation en cours...", color="blue")
        self.dockwidget.autoSyncButton.setEnabled(False)
        
        def on_sync_finished(results):
            self.dockwidget.autoSyncButton.setEnabled(True)
            self.set_progress(100, "✅ Synchronisation terminée")
            self.set_sync_ready(False)
            self.current_validated_data = None
            total_actions = sum(len(r.get('actions', [])) for r in (results or []))
            self.show_info(
                self.tr(u'Synchronisation terminée'),
                self.tr(f"{total_actions} action(s) effectuée(s) vers le backend.")
            )
            
        def on_sync_error(exc, tb):
            self.dockwidget.autoSyncButton.setEnabled(True)
            self.dockwidget.set_status_message("❌ Erreur de synchronisation", color="red")
            self.show_error("Erreur de synchronisation", f"{exc}\n\n{tb}")

        # On traite les payloads l'un après l'autre ou on adapte le worker
        # Pour simplifier on garde la logique séquentielle mais dans le worker
        def multi_sync_task(worker):
            all_merge_results = []
            full_original_data = {}

            if self.current_project_id:
                metadata_file = os.path.join(
                    self.mergin_manager.projects_dir,
                    self.current_project_id,
                    'exported_data.json'
                )
                if os.path.exists(metadata_file):
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        full_original_data = json.load(f)

            total = len(sync_payloads)
            for i, (mapping, validated_data) in enumerate(sync_payloads):
                if not isinstance(mapping, dict):
                    continue

                endpoint = mapping.get('endpoint')
                if not endpoint:
                    continue
                validated_data = self.prepare_rows_for_mapping(
                    validated_data,
                    mapping,
                    add_user_uuid=False,
                    add_verifier_uuid=True
                )
                
                worker.update_progress(int((i/total)*100), f"Synchronisation de {endpoint}...")

                original_data = full_original_data.get(endpoint) if isinstance(full_original_data, dict) else None
                if not original_data:
                    c_com_values = sorted({
                        str(row.get('c_com'))
                        for row in validated_data
                        if isinstance(row, dict) and row.get('c_com') not in (None, "")
                    })
                    filters = {'c_com': 'in.({})'.format(','.join(c_com_values))} if c_com_values else None
                    original_data = self.postgrest.select(endpoint, filters=filters) if filters else []

                merge_results = self.merge_validated_data_no_ui(mapping, original_data, validated_data)
                if merge_results:
                    all_merge_results.append(merge_results)

            if all_merge_results and self.current_project_id:
                total_actions = sum(len(r.get('actions', [])) for r in all_merge_results)
                self.mergin_manager.sync_to_api(self.current_project_id, {
                    'status': 'synced',
                    'merged_actions': total_actions,
                    'timestamp': str(__import__('datetime').datetime.now())
                })
            return all_merge_results

        from .worker_thread import Worker
        self.sync_worker = Worker(multi_sync_task)
        self.sync_worker.signals.finished.connect(on_sync_finished)
        self.sync_worker.signals.error.connect(on_sync_error)
        self.sync_worker.signals.progress.connect(lambda val, msg: self.set_progress(val, msg))
        self.sync_worker.start()

    def merge_validated_data_no_ui(self, mapping, original, validated):
        """Fusionne les données validées sans ouvrir de widget depuis un worker."""
        table = mapping.get('endpoint') if isinstance(mapping, dict) else str(mapping)
        pk_field = mapping.get('pk_field', 'id') if isinstance(mapping, dict) else 'id'
        merger = MerginDataMerger(self.postgrest)
        merge_results = merger.merge(table, original or [], validated or [], strategy='merge', pk_field=pk_field)
        if self.current_project_id:
            self.mergin_manager.merge_data(self.current_project_id, merge_results)
        return merge_results

    def merge_validated_data(self, mapping, original, validated):
        try:
            table = mapping.get('endpoint') if isinstance(mapping, dict) else str(mapping)
            pk_field = mapping.get('pk_field', 'id') if isinstance(mapping, dict) else 'id'
            merger = MerginDataMerger(self.postgrest)

            conflicts = merger.detect_conflicts(original, validated, pk_field=pk_field)
            summary = self.generate_merge_summary(conflicts)

            reply = QMessageBox.question(
                self.iface.mainWindow(),
                self.tr(u'Confirmation Fusion'),
                Utils.compact_dialog_message(f"Résumé des changements:\n{summary}\n\nProcéder?"),
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                merge_results = merger.merge(table, original, validated, strategy='merge', pk_field=pk_field)
                if self.current_project_id:
                    self.mergin_manager.merge_data(self.current_project_id, merge_results)

                QMessageBox.information(
                    self.iface.mainWindow(),
                    self.tr(u'Fusion Réussie'),
                    f"Fusion complétée!\n{len(merge_results['actions'])} actions effectuées"
                )
                return merge_results
        except Exception as exc:
            self.show_error(self.tr(u'Erreur Fusion'), exc)

    def generate_merge_summary(self, conflicts):
        summary_lines = []
        for conflict in conflicts:
            if conflict['type'] == 'deleted':
                summary_lines.append(f"🗑️ Supprimés: {conflict['count']}")
            elif conflict['type'] == 'added':
                summary_lines.append(f"🆕 Ajoutés: {conflict['count']}")
            elif conflict['type'] == 'modified':
                summary_lines.append(f"✏️ Modifié: ID {conflict['id']}")
        return "\n".join(summary_lines) if summary_lines else "Aucun changement détecté"

    # ─────────────────────────────────────────────────────────────────────
    # RUN
    # ─────────────────────────────────────────────────────────────────────

    def run(self):
        if not self.pluginIsActive:
            self.pluginIsActive = True
            if self.dockwidget is None:
                self.dockwidget = MrvTerakaDockWidget(self)
                self.dockwidget.closingPlugin.connect(self.onClosePlugin)
                self.dockwidget.logout_requested.connect(self.logout)

            if self.token_manager.is_token_valid():
                role = self.token_manager.get_user_role()
                self.dockwidget.set_authenticated(self.current_username, self.api_base_url, role=role)
            else:
                self.dockwidget.set_unauthenticated()

            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dockwidget)
            self.dockwidget.show()

            if self.postgrest and self.auto_update_sources:
                self.migrate_project_layers_to_api()
