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
from qgis.PyQt.QtCore import pyqtSignal, Qt
from qgis.PyQt.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QWidget, QGroupBox, QSpacerItem, QSizePolicy
)
from qgis.PyQt.QtGui import QColor, QIcon

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
        self.endpointLineEdit = self.endpointComboBox.lineEdit()

        # Remplir les listes
        self.populate_table_lists()
        self.populate_project_list()

        # Style et Ergonomie
        self.logout_button.setIcon(QIcon(':/plugins/mrv_teraka/login_icon.svg'))
        self.logout_button.setToolTip("Quitter la session en cours")

        self.districtLineEdit.setPlaceholderText("Filtrer par secteur (ex: Mandoto)")

        # Tooltips métier
        self.compareButton.setToolTip("Vérifier les différences avec la base centrale")
        self.loadDbButton.setToolTip("Importer les données de la couche choisie")
        self.refreshFromApiButton.setToolTip("Mettre à jour les données depuis le serveur")
        self.processProjectButton.setToolTip("Lancer l'analyse intelligente des couches du projet")

        self.autoPrepareButton.setToolTip("Déployer la mission sur Mergin Maps pour le terrain")
        self.autoImportButton.setToolTip("Récupérer les collectes effectuées sur mobile")
        self.autoValidateButton.setToolTip("Lancer le moteur de validation métier Teraka")
        self.autoSyncButton.setToolTip("Publier définitivement les données validées vers Teraka")

    def populate_table_lists(self):
        """Remplit les ComboBox avec les tables disponibles."""
        if not self.plugin:
            return
        mappings = self.plugin.load_layer_mappings()
        tables = sorted(list(mappings.keys()))
        self.endpointComboBox.clear()
        self.endpointComboBox.addItems(tables)

    def populate_project_list(self):
        """Remplit la liste des projets Mergin Maps détectés."""
        if not self.plugin or not self.plugin.mergin_manager:
            return

        self.projectComboBox.clear()

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
        self.refreshFromApiButton.clicked.connect(self.plugin.refresh_data_via_api)
        self.processProjectButton.clicked.connect(self.plugin.analyze_and_process_project)

        # Cycle Mission
        self.autoPrepareButton.clicked.connect(self.plugin.auto_deploy_mission)
        self.autoImportButton.clicked.connect(self.plugin.auto_import_mission)
        self.autoValidateButton.clicked.connect(self.plugin.auto_validate_mission)
        self.autoSyncButton.clicked.connect(self.plugin.auto_finalize_mission)

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
            QtWidgets.QMessageBox.information(self, "Succès", "Les listes de couches ont été mises à jour depuis l'API.")
        else:
            QtWidgets.QMessageBox.warning(self, "Erreur", "Impossible de contacter l'API pour mettre à jour les listes.")

        self.refreshMappingsButton.setEnabled(True)
        self.refreshMappingsButton.setText("🔄 Synchroniser les Listes")

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

    def set_authenticated(self, username=None, api_url=None):
        self.status_label.setText("● Connecté")
        self.status_label.setStyleSheet("color: #2D5A27; font-weight: bold;")
        if username and api_url:
            self.user_label.setText(f"{username} @ {api_url}")
        self.logout_button.setEnabled(True)
        self.populate_table_lists()
        self.populate_project_list()

        # Activation des contrôles
        for group in [self.groupBoxProject, self.groupBoxDB, self.groupBoxMergin]:
            group.setEnabled(True)

        self.endpointComboBox.setEnabled(True)

        buttons = [
            'loadDbButton', 'compareButton', 'refreshFromApiButton', 'processProjectButton',
            'autoPrepareButton', 'autoImportButton', 'autoValidateButton',
            'refreshMappingsButton'
        ]
        for btn in buttons:
            if hasattr(self, btn):
                getattr(self, btn).setEnabled(True)

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
