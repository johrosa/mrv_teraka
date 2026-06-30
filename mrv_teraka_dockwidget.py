# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MrvTerakaDockWidget
                                 A QGIS plugin
 plugin for the mrv team in iTeraka
 ***************************************************************************/
"""

import os

from qgis.PyQt import QtGui, QtWidgets, uic
from qgis.PyQt.QtCore import pyqtSignal, Qt, QSettings
from qgis.PyQt.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QWidget, QGroupBox, QSpacerItem, QSizePolicy,
    QListWidget, QListWidgetItem, QCheckBox
)
from qgis.PyQt.QtGui import QColor, QIcon
from qgis.core import QgsProject

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'mrv_teraka_dockwidget_base.ui'))


class MrvTerakaDockWidget(QtWidgets.QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()
    auth_requested = pyqtSignal()
    logout_requested = pyqtSignal()

    def __init__(self, plugin=None, parent=None):
        """Constructor."""
        super(MrvTerakaDockWidget, self).__init__(parent)
        self.plugin = plugin
        self.setupUi(self)
        self.setup_ui_elements()
        self.setup_connections()

    def setup_ui_elements(self):
        """Initialise les composants UI et les info-bulles avec la nouvelle charte Teraka."""
        # Mapping des membres Python
        self.status_label = self.statusLabel
        self.user_label = self.userLabel
        self.logout_button = self.logoutButton

        # Remplir les listes
        self.populate_table_lists()
        self.populate_project_list()
        self.populate_region_list()

        # Style et Ergonomie
        self.logout_button.setIcon(QIcon(':/plugins/mrv_teraka/login_icon.svg'))
        self.logout_button.setToolTip("Quitter la session en cours")

        self.regionComboBox.setEditable(True)
        self.regionComboBox.lineEdit().setPlaceholderText("Sélectionner une région...")

        self.districtComboBox.setEditable(True)
        self.districtComboBox.lineEdit().setPlaceholderText("Sélectionner un district...")

        # Tooltips métier
        self.compareButton.setToolTip("Vérifier les différences avec la base centrale")
        self.loadDbButton.setToolTip("Importer les données de la couche choisie")
        self.refreshFromApiButton.setToolTip("Mettre à jour les données depuis le serveur")
        self.processProjectButton.setText("Assistant Projet")
        self.processProjectButton.setToolTip("Diagnostiquer les couches, confirmer les mappings et choisir une action")

        self.autoPrepareButton.setToolTip("Déployer la mission sur Mergin Maps pour le terrain")
        self.autoImportButton.setToolTip("Récupérer les collectes effectuées sur mobile")
        self.autoValidateButton.setToolTip("Lancer le moteur de validation métier Teraka")
        self.autoSyncButton.setToolTip("Publier définitivement les données validées vers Teraka")

    def populate_table_lists(self):
        """Remplit la liste des couches disponibles avec des cases à cocher."""
        if not self.plugin:
            return
        mappings = self.plugin.load_layer_mappings()
        tables = sorted(list(mappings.keys()))
        
        self.endpointListWidget.blockSignals(True)
        self.endpointListWidget.clear()
        
        for table in tables:
            item = QListWidgetItem(table)
            item.setData(Qt.UserRole, table)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.endpointListWidget.addItem(item)
        
        self.endpointListWidget.blockSignals(False)

    def populate_project_list(self):
        """Remplit la liste des projets Mergin Maps détectés."""
        if not self.plugin or not self.plugin.mergin_manager:
            return

        self.projectComboBox.clear()

        if getattr(self.plugin, 'mergin_bridge', None):
            projects = self.plugin.mergin_bridge.list_local_projects()
            if projects:
                for p in projects:
                    self.projectComboBox.addItem(p.get('name'), p.get('project_file'))
                return

        # Récupérer le chemin Mergin Maps depuis QSettings
        settings = QSettings()
        mergin_path = settings.value("Mergin/projectDir")

        if not mergin_path:
            # Fallback sur le dossier par défaut Mergin si non défini
            home = os.path.expanduser("~")
            mergin_path = os.path.join(home, "Mergin Projects")

        projects = self.plugin.mergin_manager.list_external_mergin_projects(mergin_path)

        if not projects:
            self.projectComboBox.addItem("Aucun projet Mergin trouvé", None)
            return

        for p in projects:
            # On stocke le chemin du fichier .qgs/.qgz en data
            self.projectComboBox.addItem(p.get('name'), p.get('project_file'))

    def populate_region_list(self):
        """Remplit la liste des régions disponibles."""
        self.regionComboBox.blockSignals(True)
        self.regionComboBox.clear()
        self.regionComboBox.addItem("Toutes les régions", "")

        regions = []
        if self.plugin:
            regions = self.plugin.fetch_unique_regions()

        for region in regions:
            self.regionComboBox.addItem(region, region)
        self.regionComboBox.blockSignals(False)

    def populate_district_list(self):
        """Remplit la liste des districts pour la région sélectionnée."""
        region = self.regionComboBox.currentData()
        self.districtComboBox.blockSignals(True)
        self.districtComboBox.clear()
        self.districtComboBox.addItem("Tous les districts", "")

        districts = []
        if self.plugin:
            districts = self.plugin.fetch_unique_districts(region)

        for district in districts:
            self.districtComboBox.addItem(district, district)
        self.districtComboBox.blockSignals(False)

    def populate_commune_list(self):
        """Remplit la liste des communes pour le district sélectionné."""
        district = self.districtComboBox.currentData()
        self.communesListWidget.blockSignals(True)
        self.communesListWidget.clear()

        communes = []
        if self.plugin:
            communes = self.plugin.fetch_communes_by_district(district)

        for name, c_com in communes:
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, c_com)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.communesListWidget.addItem(item)

        self.communesListWidget.blockSignals(False)

    def on_region_changed(self):
        self.populate_district_list()
        self.populate_commune_list()

    def on_district_changed(self):
        self.populate_commune_list()

    def on_select_all_endpoints(self, state):
        """Sélectionne ou désélectionne toutes les couches."""
        self.endpointListWidget.blockSignals(True)
        for i in range(self.endpointListWidget.count()):
            item = self.endpointListWidget.item(i)
            item.setCheckState(Qt.Checked if state == Qt.Checked else Qt.Unchecked)
        self.endpointListWidget.blockSignals(False)

    def get_selected_endpoints(self):
        """Retourne la liste des couches sélectionnées."""
        selected = []
        for i in range(self.endpointListWidget.count()):
            item = self.endpointListWidget.item(i)
            if item.checkState() == Qt.Checked:
                selected.append(item.data(Qt.UserRole))
        return selected

    def on_select_all_communes(self, state):
        self.communesListWidget.blockSignals(True)
        for i in range(self.communesListWidget.count()):
            item = self.communesListWidget.item(i)
            item.setCheckState(Qt.Checked if state == Qt.Checked else Qt.Unchecked)
        self.communesListWidget.blockSignals(False)

    def setup_connections(self):
        """Connecte les signaux aux actions métier."""
        if not self.plugin:
            return

        # Projet
        self.loadProjectButton.clicked.connect(self.on_load_project_clicked)
        self.saveProjectButton.clicked.connect(self.plugin.save_current_project_configuration)

        # Outils Données
        self.loadDbButton.clicked.connect(self.plugin.load_database_data)
        self.compareButton.clicked.connect(self.plugin.compare_project_with_db)
        self.refreshFromApiButton.clicked.connect(self.on_refresh_from_api_clicked)
        self.processProjectButton.clicked.connect(self.plugin.analyze_and_process_project)

        # Cycle Mission
        self.autoPrepareButton.clicked.connect(self.plugin.auto_deploy_mission)
        self.autoImportButton.clicked.connect(self.plugin.auto_import_mission)
        self.autoValidateButton.clicked.connect(self.plugin.auto_validate_mission)
        self.autoSyncButton.clicked.connect(self.plugin.auto_finalize_mission)

        # Filtres Géo
        self.regionComboBox.currentTextChanged.connect(self.on_region_changed)
        self.districtComboBox.currentTextChanged.connect(self.on_district_changed)
        self.selectAllCommunesCheckBox.stateChanged.connect(self.on_select_all_communes)
        self.selectAllEndpointsCheckBox.stateChanged.connect(self.on_select_all_endpoints)

        # Configuration
        self.refreshMappingsButton.clicked.connect(self.on_refresh_mappings_clicked)

        self.logout_button.clicked.connect(self.on_logout_clicked)

    def on_logout_clicked(self):
        self.logout_requested.emit()

    def on_refresh_mappings_clicked(self):
        """Action pour synchroniser les listes depuis l'API."""
        if not self.plugin:
            return

        self.refreshMappingsButton.setEnabled(False)
        self.refreshMappingsButton.setText("⏳ Synchronisation...")
        QtWidgets.QApplication.processEvents()

        success = self.plugin.refresh_api_mappings()

        if success:
            self.populate_table_lists()
            self.populate_region_list()
            QtWidgets.QMessageBox.information(self, "Succès", "Les listes de couches et régions ont été mises à jour depuis l'API.")
        else:
            QtWidgets.QMessageBox.warning(self, "Erreur", "Impossible de contacter l'API pour mettre à jour les listes.")

        self.refreshMappingsButton.setEnabled(True)
        self.refreshMappingsButton.setText("🔄 Synchroniser les Listes")

    def on_refresh_from_api_clicked(self):
        """Open layer selection dialog before refreshing data from API."""
        if not self.plugin:
            return

        # Get current layer mappings
        mappings = self.plugin.load_layer_mappings()
        if not mappings:
            QtWidgets.QMessageBox.warning(
                self,
                "Erreur",
                "Aucun mapping de couche trouvé. Veuillez d'abord configurer les couches."
            )
            return

        from .refresh_layers_dialog import RefreshLayersDialog

        dlg = RefreshLayersDialog(self, layer_mappings=mappings)
        if dlg.exec_():
            selected = dlg.get_selected_layers()
            if selected:
                self.plugin.refresh_data_via_api(selected_endpoints=selected)
            else:
                QtWidgets.QMessageBox.information(
                    self,
                    "Aucune sélection",
                    "Aucune couche n'a été sélectionnée."
                )

    def on_load_project_clicked(self):
        """Ouvre le fichier projet QGIS sélectionné."""
        project_file = self.projectComboBox.currentData()
        if project_file and os.path.exists(project_file):
            if QgsProject.instance().read(project_file):
                self.plugin.iface.messageBar().pushMessage(
                    "Succès", f"Projet chargé : {os.path.basename(project_file)}",
                    level=0, duration=3
                )
                # Optionnel: Analyser le projet après ouverture
                self.plugin.analyze_and_process_project()
            else:
                QtWidgets.QMessageBox.warning(self, "Erreur", "Impossible de lire le fichier projet QGIS.")
        else:
            QtWidgets.QMessageBox.warning(self, "Projet introuvable", "Veuillez sélectionner un projet Mergin valide.")

    def set_status_message(self, message, color="black"):
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")

    def set_authenticated(self, username=None, api_url=None, role=None):
        self.status_label.setText("● Connecté")
        self.status_label.setStyleSheet("color: #2D5A27; font-weight: bold;")
        
        role_suffix = f" ({role})" if role else ""
        if username and api_url:
            self.user_label.setText(f"{username}{role_suffix} @ {api_url}")
        
        self.logout_button.setEnabled(True)
        self.populate_table_lists()
        self.populate_project_list()

        # Activation des contrôles
        for group in [self.groupBoxProject, self.groupBoxDB, self.groupBoxMergin]:
            group.setEnabled(True)

        self.endpointListWidget.setEnabled(True)

        # Liste des boutons avec leur accessibilité par rôle
        buttons = [
            'loadDbButton', 'compareButton', 'refreshFromApiButton', 'processProjectButton',
            'autoPrepareButton', 'autoImportButton', 'autoValidateButton', 'autoSyncButton',
            'refreshMappingsButton'
        ]
        
        # Logique de restriction par rôle
        if isinstance(role, (list, tuple, set)):
            role_text = " ".join(str(item) for item in role)
        else:
            role_text = str(role or "")
        role_text = role_text.lower()
        is_validator = any(
            value in role_text
            for value in ['validator', 'validateur', 'admin', 'superviseur', 'mrv_l3', 'mrv']
        )
        
        for btn_name in buttons:
            if hasattr(self, btn_name):
                btn = getattr(self, btn_name)
                
                # Restrictions spécifiques
                if btn_name in ['autoValidateButton', 'autoSyncButton']:
                    btn.setEnabled(is_validator)
                    if not is_validator:
                        btn.setToolTip("Action réservée aux validateurs")
                else:
                    btn.setEnabled(True)

    def set_unauthenticated(self):
        self.status_label.setText("● Déconnecté")
        self.status_label.setStyleSheet("color: #C62828; font-weight: bold;")
        self.user_label.setText("Pas connecté")
        self.logout_button.setEnabled(False)

        for group in [self.groupBoxProject, self.groupBoxDB, self.groupBoxMergin]:
            group.setEnabled(False)

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()
