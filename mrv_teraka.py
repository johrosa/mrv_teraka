# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MrvTeraka
                                 A QGIS plugin for the mrv team in iTeraka
 ***************************************************************************/
"""
import json
import os.path
import re
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt, QVariant
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QInputDialog, QLineEdit

# Initialisation des ressources Qt
from .resources import *

from qgis.core import QgsProject, QgsVectorLayer, QgsMapLayer, QgsTask, QgsApplication
from .mrv_teraka_dockwidget import MrvTerakaDockWidget
from .layer_utils import is_geojson, create_vector_layer, layer_to_list_of_dicts

# Importation du client PostgREST et gestionnaire d'authentification
from .postgrest_client import PostgREST, PostgRESTAuthenticator, PostgRESTMode
from .config_postgrest import load_layer_mapping, normalize_layer_name_to_endpoint
from .auth_dialog import AuthDialog
from .token_manager import TokenManager
from .mergin_workflow_manager import MerginWorkflowManager, MerginDataMerger
from .validation_dialog import DataValidationDialog
from .connection_checker import ConnectionChecker


class MrvTeraka:
    """Implémentation du Plugin QGIS MrvTeraka."""

    def __init__(self, iface):
        self.iface = iface

        # Configuration de l'API - On utilise l'Enum du client
        self.postgrest_mode = PostgRESTMode.DJANGO
        self.api_base_url = 'http://localhost:8000'  # Port par défaut Django

        # Instances du client API et gestionnaire de jeton
        self.postgrest = None
        self.token_manager = TokenManager()
        self.current_username = None
        self.auth_action = None  # Bouton d'authentification
        
        # Managers pour le workflow Mergin
        self.mergin_manager = None
        self.current_project_id = None

        # Initialisation du checker de connexion
        self.conn_checker = ConnectionChecker(interval=60)
        self.conn_checker.connection_status_changed.connect(self.on_connection_status_changed)
        self.mergin_validation_ready = False
        self.current_collected_data = None
        self.current_original_data = None
        self.current_data_mapping = None
        self.current_validated_data = None

        # Initialisation du répertoire et de la langue
        self.plugin_dir = os.path.dirname(__file__)
        self.default_project_file = os.path.join(self.plugin_dir, 'Q_v17_7_7_ITASY2026_WP.qgz')
        
        # Initialiser le gestionnaire Mergin Workflow
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

        # Développement : ne pas ouvrir automatiquement le projet QGIS au démarrage
        self.auto_open_default_project = False
        # Développement : ne pas mettre à jour automatiquement les sources au démarrage
        self.auto_update_sources = False

        self.pluginIsActive = False
        self.dockwidget = None

    def show_api_error_view(self, exc):
        """Affiche une erreur Django/PostgREST HTML si possible."""
        try:
            from .django_error_viewer import show_django_error
        except ImportError:
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

    def show_message(self, title, message, icon=QMessageBox.Information):
        """Affiche un message en texte brut ou HTML selon le contenu."""
        msg_box = QMessageBox(self.iface.mainWindow())
        msg_box.setIcon(icon)
        msg_box.setWindowTitle(title)
        if self.is_html_content(message):
            msg_box.setTextFormat(Qt.RichText)
            msg_box.setText(message)
        else:
            msg_box.setTextFormat(Qt.PlainText)
            msg_box.setText(message)
        msg_box.exec_()

    def is_html_content(self, text):
        """Retourne True si le texte contient du HTML à afficher."""
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

    def initGui(self):
        """Initialise l'interface graphique."""
        # Bouton d'authentification principal
        self.auth_action = self.add_action(
            ':/plugins/mrv_teraka/login_icon.svg',
            text=self.tr(u'Connexion'),
            callback=self.show_auth_dialog,
            parent=self.iface.mainWindow()
        )
        
        # Bouton principal du plugin
        self.add_action(
            ':/plugins/mrv_teraka/icon.png',
            text=self.tr(u'iTeraka'),
            callback=self.run,
            parent=self.iface.mainWindow()
        )
        
        # Charger le jeton sauvegardé à l'initialisation
        self.load_saved_token()

        # Lancer le thread de vérification
        self.conn_checker.start()
        # Ne pas ouvrir automatiquement le projet par défaut en développement
        if self.auto_open_default_project:
            self.open_default_qgis_project()

    def unload(self):
        """Supprime le plugin de l'interface QGIS."""
        # Arrêter le checker
        if hasattr(self, 'conn_checker'):
            self.conn_checker.stop()

        for action in self.actions:
            self.iface.removePluginMenu(self.tr(u'&MRV Teraka'), action)
            self.iface.removeToolBarIcon(action)
        del self.toolbar

    def onClosePlugin(self):
        """Nettoyage à la fermeture du dockwidget."""
        self.dockwidget.closingPlugin.disconnect(self.onClosePlugin)
        self.pluginIsActive = False

    # --- AUTHENTIFICATION ET GESTION DES JETONS ---

    def show_auth_dialog(self):
        """Affiche le formulaire d'authentification"""
        auth_dialog = AuthDialog(
            parent=self.iface.mainWindow(),
            api_modes={
                'Django': PostgRESTMode.DJANGO,
                'PostgREST (Standalone)': PostgRESTMode.STANDALONE
            }
        )
        
        if auth_dialog.exec_() == AuthDialog.Accepted:
            credentials = auth_dialog.get_credentials()
            self.authenticate_with_credentials(credentials, auth_dialog)

    def authenticate_with_credentials(self, credentials, dialog=None):
        """
        Authentifie avec les identifiants fournis
        
        Args:
            credentials: Dict avec username, password, url, mode, remember
            dialog: Dialog parent pour afficher les erreurs
        """
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
            # Authentification
            authenticator = PostgRESTAuthenticator(self.api_base_url, mode=self.postgrest_mode)
            token = authenticator.authenticate(username, password)
            
            # Initialisation du client PostgREST
            self.postgrest = PostgREST(self.api_base_url, mode=self.postgrest_mode)
            self.postgrest.set_auth_token(token)
            
            # Sauvegarde du jeton et des informations
            self.token_manager.save_token(token, self.api_base_url, self.postgrest_mode.value)
            self.current_username = username
            
            # Mettre à jour le checker
            self.conn_checker.set_client(self.postgrest)

            # Sauvegarder aussi les identifiants si demandé
            if credentials['remember']:
                settings = QSettings('iTeraka', 'MrvTeraka')
                settings.setValue('auth/last_username', username)
            else:
                settings = QSettings('iTeraka', 'MrvTeraka')
                settings.remove('auth/last_username')
            
            # Mettre à jour l'interface
            self.update_auth_ui()
            
            # Relancer une vérification immédiate
            self.conn_checker.set_client(self.postgrest)

            if self.dockwidget:
                self.dockwidget.set_authenticated(username, self.api_base_url)
            
            mode_label = "Django" if self.postgrest_mode == PostgRESTMode.DJANGO else "PostgREST"
            QMessageBox.information(
                self.iface.mainWindow(),
                self.tr(u'Authentification réussie'),
                f"Connecté à {mode_label} en tant que {username}"
            )
            
        except Exception as exc:
            shown = self.show_error(self.tr(u"Erreur d'authentification"), exc)
            if dialog and not shown:
                dialog.show_error(str(exc))

    def load_saved_token(self):
        """Charge le jeton sauvegardé au démarrage"""
        token, api_url, mode = self.token_manager.load_token()
        
        if token and api_url:
            self.postgrest = PostgREST(api_url, mode=PostgRESTMode[mode.upper()] if mode else PostgRESTMode.DJANGO)
            self.postgrest.set_auth_token(token)
            self.api_base_url = api_url

            # Mettre à jour le checker
            self.conn_checker.set_client(self.postgrest)

            if not self.postgrest.verify_token():
                self.token_manager.clear_token()
                self.postgrest = None
                self.current_username = None
                self.conn_checker.set_client(None)
                return
            
            # Charger le dernier username
            settings = QSettings('iTeraka', 'MrvTeraka')
            self.current_username = settings.value('auth/last_username', 'Utilisateur')
            
            # Mettre à jour l'interface
            self.update_auth_ui()

    def open_default_qgis_project(self):
        """Ouvre automatiquement le projet QGIS par défaut au démarrage du plugin."""
        if os.path.exists(self.default_project_file):
            if not QgsProject.instance().read(self.default_project_file):
                QMessageBox.warning(
                    self.iface.mainWindow(),
                    self.tr(u'Ouverture du projet'),
                    self.tr(u'Impossible de charger le projet QGIS par défaut.')
                )
        else:
            QMessageBox.warning(
                self.iface.mainWindow(),
                self.tr(u'Ouverture du projet'),
                self.tr(u'Fichier de projet QGIS introuvable : {path}').format(path=self.default_project_file)
            )

    def update_auth_ui(self):
        """Met à jour l'interface pour afficher l'état connecté"""
        if self.auth_action:
            try:
                self.auth_action.triggered.disconnect()
            except Exception:
                pass
            self.auth_action.setText(self.tr(u'Déconnecter'))
            self.auth_action.triggered.connect(self.logout)
        
        if self.dockwidget:
            # S'assurer que les infos sont à jour avant d'activer les boutons
            username = self.current_username or "Utilisateur"
            url = self.api_base_url or "API"
            self.dockwidget.set_authenticated(username, url)

    def on_connection_status_changed(self, is_connected, message):
        """Réagit aux changements de statut de connexion détectés en arrière-plan."""
        if not is_connected and self.postgrest:
            # On a perdu la connexion ou le token a expiré
            if self.dockwidget:
                self.dockwidget.set_status_message(f"⚠️ {message}", color="orange")
        elif is_connected and self.dockwidget:
            self.dockwidget.set_authenticated(self.current_username, self.api_base_url)

    def logout(self, confirm=True):
        """Déconnecte l'utilisateur et supprime le jeton"""
        if confirm:
            reply = QMessageBox.question(
                self.iface.mainWindow(),
                self.tr(u'Confirmation'),
                self.tr(u'Êtes-vous sûr de vouloir vous déconnecter ?'),
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        # Supprimer le jeton
        self.token_manager.clear_token()
        self.postgrest = None
        self.current_username = None

        # Mettre à jour le checker
        if hasattr(self, 'conn_checker'):
            self.conn_checker.set_client(None)

        # Réinitialiser l'interface
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
            QMessageBox.information(
                self.iface.mainWindow(),
                self.tr(u'Déconnexion'),
                self.tr(u'Vous avez été déconnecté.')
            )

    def check_api_auth(self):
        """Vérifie si l'utilisateur est authentifié"""
        if not self.postgrest or not self.token_manager.is_token_valid():
            QMessageBox.warning(
                self.iface.mainWindow(),
                self.tr(u'Authentification requise'),
                self.tr(u'Veuillez vous authentifier avant de continuer.')
            )
            self.show_auth_dialog()
            return False
        return True

    def load_layer_mappings(self):
        """Charge les correspondances couche QGIS -> endpoint PostgREST."""
        if getattr(self, 'layer_mappings', None) is None:
            self.layer_mappings = load_layer_mapping(self.plugin_dir)
        return self.layer_mappings

    def get_layer_mapping(self, layer_name):
        """Retourne le mapping détaillé pour une couche QGIS."""
        mappings = self.load_layer_mappings()
        if layer_name in mappings and mappings[layer_name].get('endpoint'):
            return mappings[layer_name]
        return {
            'endpoint': normalize_layer_name_to_endpoint(layer_name),
            'geom_field': 'geom',
            'pk_field': 'id'
        }

    def get_project_layer_endpoints(self):
        """Retourne les endpoints API pour chaque couche vectorielle active du projet."""
        endpoints = {}
        for layer in QgsProject.instance().mapLayers().values():
            if layer.type() != QgsMapLayer.VectorLayer:
                continue
            if layer.providerType() not in ('ogr', 'postgres', 'memory'):
                continue
            layer_name = layer.name()
            if not layer_name:
                continue
            endpoints[layer_name] = self.get_layer_mapping(layer_name)
        return endpoints

    def migrate_project_layers_to_api(self):
        """Modifie les couches du projet QGIS pour charger les données via l'API PostgREST."""
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

        for layer_name, mapping in project_endpoints.items():
            try:
                db_data = self.postgrest.select(mapping['endpoint'])
                layer = create_vector_layer(db_data, layer_name, mapping.get('geom_field', 'geom'))
                if layer and layer.isValid():
                    layer.setCustomProperty('postgrest:endpoint', mapping['endpoint'])
                    layer.setCustomProperty('postgrest:geom_field', mapping.get('geom_field', 'geom'))
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
        """Retourne la liste des endpoints à charger ou comparer."""
        if text_endpoint:
            return {text_endpoint: {'endpoint': text_endpoint, 'geom_field': 'geom', 'pk_field': 'id'}}
        endpoint_map = self.get_project_layer_endpoints()
        return endpoint_map if endpoint_map else {}

    def get_mapping_for_endpoint(self, endpoint):
        """Retourne le mapping configuré pour un endpoint donné."""
        if not endpoint:
            return {'endpoint': endpoint, 'geom_field': 'geom', 'pk_field': 'id'}

        # Chercher d'abord dans les mappings chargés explicitement
        mappings = self.load_layer_mappings()
        for m_name, m_data in mappings.items():
            if m_data.get('endpoint') == endpoint:
                return m_data

        # Fallback sur les couches du projet
        for mapping in self.get_project_layer_endpoints().values():
            if mapping.get('endpoint') == endpoint:
                return mapping

        return {'endpoint': endpoint, 'geom_field': 'geom', 'pk_field': 'id'}

    def save_current_project_configuration(self):
        """Enregistre la configuration actuelle des couches comme un nouveau projet."""
        if not self.check_api_auth():
            return

        name, ok = QInputDialog.getText(self.iface.mainWindow(), self.tr(u"Enregistrer Projet"), self.tr(u"Nom du projet :"))
        if not ok or not name:
            return

        endpoints = self.get_project_layer_endpoints()
        if not endpoints:
            QMessageBox.warning(self.iface.mainWindow(), self.tr(u"Erreur"), self.tr(u"Aucune couche mappée trouvée dans le projet."))
            return

        tables = list(set([m['endpoint'] for m in endpoints.values()]))
        project_id = self.mergin_manager.create_project(name, tables)
        self.current_project_id = project_id

        if self.dockwidget:
            self.dockwidget.populate_project_list()
            # Sélectionner le nouveau projet
            idx = self.dockwidget.projectComboBox.findData(project_id)
            if idx >= 0:
                self.dockwidget.projectComboBox.setCurrentIndex(idx)

        QMessageBox.information(self.iface.mainWindow(), self.tr(u"Projet enregistré"),
                                self.tr(u"Projet '{0}' enregistré avec {1} couches.").format(name, len(tables)))

    def load_project_by_id(self, project_id):
        """Charge toutes les couches associées à un projet."""
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

        # Charger chaque table
        errors = []
        project = QgsProject.instance()

        for table in tables:
            try:
                mapping = self.get_mapping_for_endpoint(table)
                db_data = self.postgrest.select(table)
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
            self.show_message(self.tr(u"Chargement partiel"),
                                self.tr(u"Erreur lors du chargement des tables : {0}").format(", ".join(errors)),
                                icon=QMessageBox.Warning)
        else:
            QMessageBox.information(self.iface.mainWindow(), self.tr(u"Projet chargé"),
                                    self.tr(u"Le projet '{0}' a été chargé avec succès.").format(info.get('name')))

    def set_validation_ready(self, ready: bool):
        """Active ou désactive le bouton de validation."""
        self.mergin_validation_ready = ready
        if self.dockwidget and hasattr(self.dockwidget, 'openValidationButton'):
            self.dockwidget.openValidationButton.setEnabled(ready)

    def set_sync_ready(self, ready: bool):
        """Active ou désactive le bouton de synchronisation backend."""
        if self.dockwidget and hasattr(self.dockwidget, 'syncToBackendButton'):
            self.dockwidget.syncToBackendButton.setEnabled(ready)

    def refresh_data_via_api(self):
        """Recharge les couches à partir de l'API PostgREST."""
        if not self.dockwidget or not self.check_api_auth():
            return
        self.current_validated_data = None
        self.set_sync_ready(False)
        self.load_database_data()
        self.set_validation_ready(False)

    def load_project_from_mergin(self):
        """Charge un projet existant depuis le stockage Mergin local."""
        if not self.dockwidget or not self.check_api_auth():
            return

        if not self.current_project_id:
            QMessageBox.warning(
                self.iface.mainWindow(),
                self.tr(u'Projet Mergin manquant'),
                self.tr(u'Veuillez préparer ou sélectionner un projet Mergin avant de charger.')
            )
            return

        imported_file = os.path.join(
            self.mergin_manager.projects_dir,
            self.current_project_id,
            'imported_data.json'
        )

        if not os.path.exists(imported_file):
            QMessageBox.warning(
                self.iface.mainWindow(),
                self.tr(u'Fichier introuvable'),
                self.tr(u"Aucune donnée importée depuis Mergin n'a été trouvée pour ce projet.")
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

    def refresh_data_via_mergin(self):
        """Met à jour les données depuis le projet Mergin et active la validation."""
        if not self.dockwidget or not self.check_api_auth():
            return
        self.load_project_from_mergin()

    def open_validation_form(self):
        """Ouvre le formulaire de validation seulement après mise à jour via Mergin."""
        if not self.mergin_validation_ready:
            QMessageBox.warning(
                self.iface.mainWindow(),
                self.tr(u'Validation non disponible'),
                self.tr(u"Veuillez mettre à jour les données via Mergin Map avant d'ouvrir le formulaire de validation.")
            )
            return
        self.load_collected_data(self.current_collected_data)

    # --- ACTIONS SIG ---

    def push_project_data_to_backend(self):
        """Pousse toutes les données du projet QGIS vers le backend API via une tâche asynchrone."""
        if not self.check_api_auth():
            return

        project_endpoints = self.get_project_layer_endpoints()
        if not project_endpoints:
            QMessageBox.information(self.iface.mainWindow(), self.tr(u'No mapped layers'),
                                  self.tr(u"Aucune couche mappée n'a été trouvée dans le projet."))
            return

        reply = QMessageBox.question(
            self.iface.mainWindow(), self.tr(u'Confirmer la migration'),
            self.tr(u"Voulez-vous pousser les données de {count} couches vers la base de données ?\n\n"
                  u"La migration utilisera la logique 'Upsert' : les enregistrements existants seront mis à jour "
                  u"et les nouveaux seront créés.").format(count=len(project_endpoints)),
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        # Préparer les données pour la tâche (car on ne peut pas manipuler les couches QGIS dans un thread)
        project = QgsProject.instance()
        migration_data = []
        for layer_name, mapping in project_endpoints.items():
            layers = project.mapLayersByName(layer_name)
            if layers:
                data = layer_to_list_of_dicts(layers[0], geom_field=mapping.get('geom_field', 'geom'))
                if data:
                    migration_data.append((layer_name, mapping['endpoint'], data))

        if not migration_data:
            self.show_message(self.tr(u'Migration'), self.tr(u"Aucune donnée à migrer."))
            return

        # Créer et lancer la tâche asynchrone
        task = QgsTask.fromFunction(
            self.tr(u'Migration des données MrvTeraka'),
            self._do_migration_task,
            migration_data=migration_data,
            on_finished=self._on_migration_finished
        )
        QgsApplication.taskManager().addTask(task)

        if self.dockwidget:
            self.dockwidget.merginResultsTextEdit.setPlainText(self.tr(u"Migration en cours en arrière-plan..."))

    def _do_migration_task(self, task, migration_data):
        """Exécution de la migration dans un thread séparé."""
        results = []
        errors_count = 0
        total = len(migration_data)

        for i, (layer_name, endpoint, data) in enumerate(migration_data):
            if task.isCanceled():
                return {'results': results, 'status': 'canceled'}

            try:
                self.postgrest.insert(endpoint, data, upsert=True)
                results.append(f"✅ {layer_name} : {len(data)} enregistrements migrés")
            except Exception as e:
                results.append(f"❌ {layer_name} : {str(e)}")
                errors_count += 1

            task.setProgress((i + 1) / total * 100)

        return {'results': results, 'errors_count': errors_count, 'status': 'completed'}

    def _on_migration_finished(self, result):
        """Callback appelé à la fin de la tâche de migration."""
        if not result or result.get('status') == 'canceled':
            self.show_message(self.tr(u'Migration'), self.tr(u"Migration annulée."))
            return

        report = "\n".join(result['results'])
        if self.dockwidget:
            self.dockwidget.comparisonResultsTextEdit.setPlainText(report)

        if result['errors_count'] > 0:
            QMessageBox.warning(self.iface.mainWindow(), self.tr(u'Migration terminée avec erreurs'), report)
        else:
            QMessageBox.information(self.iface.mainWindow(), self.tr(u'Migration réussie'), report)

    def load_database_data(self):
        """Charge des données depuis l'API vers QGIS."""
        if not self.dockwidget or not self.check_api_auth():
            return

        endpoint = self.dockwidget.endpointLineEdit.text().strip()
        district_filter = self.dockwidget.districtLineEdit.text().strip()
        requested_endpoints = self.get_requested_endpoints(endpoint)

        if not requested_endpoints:
            QMessageBox.warning(
                self.iface.mainWindow(),
                self.tr(u'Erreur'),
                self.tr(u'Aucun endpoint configuré ou aucune couche vectorielle détectée dans le projet.')
            )
            return

        try:
            for layer_name, mapping in requested_endpoints.items():
                endpoint_value = mapping['endpoint']

                filters = {}
                # Appliquer le filtre de district si spécifié et si la table est 'communes'
                if district_filter and endpoint_value == 'communes':
                    filters['district'] = f'eq.{district_filter}'

                db_data = self.postgrest.select(endpoint_value, filters=filters)
                display_name = f"{layer_name} ({endpoint_value})"
                geom_field = mapping.get('geom_field', 'geom')

                if is_geojson(db_data):
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.geojson', delete=False, encoding='utf-8') as f:
                        json.dump(db_data, f)
                        temp_file = f.name

                    layer = QgsVectorLayer(temp_file, display_name, 'ogr')
                    if layer.isValid():
                        QgsProject.instance().addMapLayer(layer)
                        os.unlink(temp_file)
                    else:
                        QMessageBox.critical(self.iface.mainWindow(), "Erreur", f"GéoJSON invalide pour {endpoint_value}.")
                else:
                    layer = create_vector_layer(db_data, display_name, geom_field)
                    if layer and layer.isValid():
                        layer.setCustomProperty('postgrest:endpoint', endpoint_value)
                        layer.setCustomProperty('postgrest:geom_field', geom_field)
                        layer.setCustomProperty('postgrest:pk_field', mapping.get('pk_field', 'id'))
                        QgsProject.instance().addMapLayer(layer)

            QMessageBox.information(
                self.iface.mainWindow(),
                self.tr(u'Chargement terminé'),
                self.tr(u'Des couches API ont été chargées depuis PostgREST.')
            )

        except Exception as exc:
            self.show_error(self.tr(u'Erreur'), exc)


    def compare_project_with_db(self):
        """Compare les couches locales avec les données API."""
        if not self.dockwidget or not self.check_api_auth():
            return

        endpoint = self.dockwidget.endpointLineEdit.text().strip()
        district_filter = self.dockwidget.districtLineEdit.text().strip()
        requested_endpoints = self.get_requested_endpoints(endpoint)

        if not requested_endpoints:
            QMessageBox.warning(
                self.iface.mainWindow(),
                self.tr(u'Erreur'),
                self.tr(u'Aucun endpoint configuré ou aucune couche vectorielle détectée dans le projet.')
            )
            return

        try:
            report = [f"Statut : Connecté à {self.api_base_url}"]
            if district_filter:
                report.append(f"Filtre District : {district_filter}")

            for layer_name, mapping in requested_endpoints.items():
                endpoint_value = mapping['endpoint']

                filters = {}
                if district_filter and endpoint_value == 'communes':
                    filters['district'] = f'eq.{district_filter}'

                count = len(self.postgrest.select(endpoint_value, select="id", filters=filters))
                report.append(f"{layer_name} -> {endpoint_value} : {count} enregistrements")

            qgis_layers = [l.name() for l in QgsProject.instance().mapLayers().values() if l.type() == QgsMapLayer.VectorLayer]
            report.append(f"Couches locales vectorielles détectées : {len(qgis_layers)}")

            self.dockwidget.comparisonResultsTextEdit.setPlainText("\n".join(report))
        except Exception as exc:
            self.show_error("Erreur", exc)

    def prepare_mergin_project(self):
        """Prépare un export des données DB pour ingestion dans un projet Mergin."""
        if not self.dockwidget or not self.check_api_auth():
            return

        # Si un projet est déjà sélectionné, on exporte ses tables
        info = None
        if self.current_project_id:
            info = self.mergin_manager.get_project_info(self.current_project_id)

        requested_endpoints = {}
        if info:
            tables = info.get('source_tables', [])
            for table in tables:
                requested_endpoints[table] = self.get_mapping_for_endpoint(table)
        else:
            endpoint = self.dockwidget.merginEndpointLineEdit.text().strip()
            requested_endpoints = self.get_requested_endpoints(endpoint)

        if not requested_endpoints:
            QMessageBox.warning(
                self.iface.mainWindow(),
                self.tr(u'Erreur'),
                self.tr(u'Aucun endpoint configuré ou aucune couche vectorielle détectée dans le projet.')
            )
            return

        try:
            district_filter = self.dockwidget.districtLineEdit.text().strip()
            export_payload = {}
            for layer_name, mapping in requested_endpoints.items():
                endpoint_value = mapping['endpoint']
                filters = {}
                # Appliquer le filtre de district si spécifié (ex: communes)
                if district_filter and endpoint_value == 'communes':
                    filters['district'] = f'eq.{district_filter}'

                export_payload[endpoint_value] = self.postgrest.select(endpoint_value, filters=filters)

            if not self.current_project_id:
                timestamp = __import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')
                project_name = 'mergin_'
                if district_filter:
                    project_name += f"{district_filter}_"
                project_name += timestamp

                project_description = f"Collecte terrain"
                if district_filter:
                    project_description += f" [District: {district_filter}]"
                project_description += f" - {', '.join(requested_endpoints.keys())}"

                self.current_project_id = self.mergin_manager.create_project(
                    project_name,
                    list(set([mapping['endpoint'] for mapping in requested_endpoints.values()])),
                    project_description
                )

            self.mergin_manager.save_exported_data(self.current_project_id, export_payload)

            output_file = os.path.join(self.plugin_dir, 'mergin_ready_data.json')
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_payload, f, ensure_ascii=False, indent=2)

            endpoints_list = [mapping['endpoint'] for mapping in requested_endpoints.values()]
            message = (
                f"Données préparées pour Mergin\n"
                f"Projet ID: {self.current_project_id}\n"
                f"Endpoints exportés: {', '.join(endpoints_list)}\n"
                f"Fichier: {output_file}"
            )
            self.dockwidget.merginResultsTextEdit.setPlainText(message)
            QMessageBox.information(
                self.iface.mainWindow(),
                self.tr(u'Préparation Mergin terminée'),
                message,
            )
        except Exception as exc:
            self.show_error(self.tr(u'Erreur Mergin'), exc)

    def load_collected_data(self, collected_data=None):
        """Charge les données collectées et affiche le formulaire de validation"""
        if not self.dockwidget or not self.check_api_auth():
            return

        endpoint = self.dockwidget.merginEndpointLineEdit.text().strip()
        if not endpoint and collected_data is None:
            QMessageBox.warning(
                self.iface.mainWindow(),
                self.tr(u'Erreur'),
                self.tr(u'Veuillez spécifier un endpoint.')
            )
            return

        try:
            if collected_data is None:
                mapping = self.get_mapping_for_endpoint(endpoint)
                collected_data = self.postgrest.select(mapping['endpoint'])
                self.current_data_mapping = mapping
            else:
                if isinstance(collected_data, dict) and len(collected_data) == 1:
                    endpoint_key = next(iter(collected_data.keys()))
                    collected_data = collected_data[endpoint_key]
                    self.current_data_mapping = self.get_mapping_for_endpoint(endpoint_key)
                else:
                    self.current_data_mapping = self.get_mapping_for_endpoint(endpoint)

            self.current_collected_data = collected_data
            
            # Si on a un projet créé, charger les données originales
            original_data = []
            if self.current_project_id:
                import json as json_module
                metadata_file = os.path.join(
                    self.mergin_manager.projects_dir,
                    self.current_project_id,
                    'exported_data.json'
                )
                if os.path.exists(metadata_file):
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        original_data = json_module.load(f)
            
            # Importer les données collectées dans le manager
            if self.current_project_id:
                self.mergin_manager.import_collected_data(self.current_project_id, collected_data)
            
            # Afficher le formulaire de validation
            validation_dialog = DataValidationDialog(
                parent=self.iface.mainWindow(),
                collected_data=collected_data,
                original_data=original_data
            )
            
            if validation_dialog.exec_() == DataValidationDialog.Accepted:
                validated_data = validation_dialog.validated_data
                
                # Stocker les résultats de validation
                validation_results = {
                    'status': 'approved',
                    'data_count': len(validated_data),
                    'timestamp': str(__import__('datetime').datetime.now())
                }
                
                self.current_validated_data = validated_data
                self.set_sync_ready(True)
                
                if self.current_project_id:
                    self.mergin_manager.validate_data(self.current_project_id, validation_results)
                
                QMessageBox.information(
                    self.iface.mainWindow(),
                    self.tr(u'Validation terminée'),
                    self.tr(u'Les données validées sont prêtes pour la synchronisation backend.')
                )
        except Exception as exc:
            self.show_error(self.tr(u'Erreur'), exc)

    def sync_validated_data_to_backend(self):
        """Synchronise les données validées avec l'API backend."""
        if not self.dockwidget or not self.check_api_auth():
            return

        if not self.current_validated_data:
            QMessageBox.warning(
                self.iface.mainWindow(),
                self.tr(u'Synchronisation impossible'),
                self.tr(u"Aucune donnée validée n'a été trouvée. Veuillez d'abord valider des données.")
            )
            return

        # Gérer les données multi-tables ou mono-table
        sync_payloads = []
        if isinstance(self.current_validated_data, dict) and not is_geojson(self.current_validated_data):
            # C'est un dictionnaire {endpoint: [data]}
            for endpoint, data in self.current_validated_data.items():
                sync_payloads.append((self.get_mapping_for_endpoint(endpoint), data))
        else:
            # C'est une liste de données (mono-table)
            mapping = self.current_data_mapping or self.get_mapping_for_endpoint(
                self.dockwidget.merginEndpointLineEdit.text().strip()
            )
            sync_payloads.append((mapping, self.current_validated_data))

        try:
            all_merge_results = []

            # Charger les données originales complètes si possible
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

            for mapping, validated_data in sync_payloads:
                endpoint = mapping.get('endpoint')
                if not endpoint:
                    continue

                original_data = full_original_data.get(endpoint) if isinstance(full_original_data, dict) else None
                if not original_data:
                    original_data = self.postgrest.select(endpoint)

                merge_results = self.merge_validated_data(mapping, original_data, validated_data)
                if merge_results:
                    all_merge_results.append(merge_results)

            if all_merge_results and self.current_project_id:
                total_actions = sum(len(r.get('actions', [])) for r in all_merge_results)
                self.mergin_manager.sync_to_api(self.current_project_id, {
                    'status': 'synced',
                    'merged_actions': total_actions,
                    'timestamp': str(__import__('datetime').datetime.now())
                })
                self.set_sync_ready(False)
                self.current_validated_data = None
        except Exception as exc:
            self.show_error(self.tr(u'Erreur'), exc)

    def merge_validated_data(self, mapping, original, validated):
        """Fusionne les données validées avec la base de données"""
        try:
            table = mapping.get('endpoint') if isinstance(mapping, dict) else str(mapping)
            pk_field = mapping.get('pk_field', 'id') if isinstance(mapping, dict) else 'id'
            merger = MerginDataMerger(self.postgrest)
            
            # Détect conflicts
            conflicts = merger.detect_conflicts(original, validated, pk_field=pk_field)
            
            # Afficher résumé
            summary = self.generate_merge_summary(conflicts)
            
            reply = QMessageBox.question(
                self.iface.mainWindow(),
                self.tr(u'Confirmation Fusion'),
                f"Résumé des changements:\n{summary}\n\nProcéder?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Effectuer la fusion
                merge_results = merger.merge(table, original, validated, strategy='merge', pk_field=pk_field)
                if self.current_project_id:
                    self.mergin_manager.merge_data(self.current_project_id, merge_results)
                
                # Afficher résultats
                QMessageBox.information(
                    self.iface.mainWindow(),
                    self.tr(u'Fusion Réussie'),
                    f"Fusion complétée!\n{len(merge_results['actions'])} actions effectuées"
                )
                return merge_results
        except Exception as exc:
            self.show_error(self.tr(u'Erreur Fusion'), exc)

    def generate_merge_summary(self, conflicts):
        """Génère un résumé des conflits pour l'utilisateur"""
        summary_lines = []
        
        for conflict in conflicts:
            if conflict['type'] == 'deleted':
                summary_lines.append(f"🗑️ Supprimés: {conflict['count']}")
            elif conflict['type'] == 'added':
                summary_lines.append(f"🆕 Ajoutés: {conflict['count']}")
            elif conflict['type'] == 'modified':
                summary_lines.append(f"✏️ Modifié: ID {conflict['id']}")
        
        return "\n".join(summary_lines) if summary_lines else "Aucun changement détecté"

    def run(self):
        """Lance l'interface du plugin."""
        if not self.pluginIsActive:
            self.pluginIsActive = True
            if self.dockwidget is None:
                self.dockwidget = MrvTerakaDockWidget(self)
                # Connecter les signaux de la dock widget
                self.dockwidget.closingPlugin.connect(self.onClosePlugin)
                self.dockwidget.logout_requested.connect(self.logout)
            
            # Mettre à jour l'état d'authentification dans la dock
            if self.token_manager.is_token_valid():
                self.dockwidget.set_authenticated(self.current_username, self.api_base_url)
            else:
                self.dockwidget.set_unauthenticated()
            
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dockwidget)
            self.dockwidget.show()

            if self.postgrest and self.auto_update_sources:
                self.migrate_project_layers_to_api()