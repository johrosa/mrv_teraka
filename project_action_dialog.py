# -*- coding: utf-8 -*-
import os
from qgis.PyQt import QtWidgets, QtCore, QtGui
from qgis.core import QgsProject, QgsMapLayer

class ProjectActionDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, layer_info=None, endpoints=None):
        """
        layer_info: List of dicts {layer_id, name, endpoint, type}
        endpoints: List of available API endpoints
        """
        super(ProjectActionDialog, self).__init__(parent)
        self.setWindowTitle("Analyse et Actions du Projet")
        self.resize(800, 500)

        self.layout = QtWidgets.QVBoxLayout(self)

        self.label = QtWidgets.QLabel("Analyse des couches du projet et correspondances API :")
        self.label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.layout.addWidget(self.label)

        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Sélection", "Couche QGIS", "Type", "Table API (Mapping)"])
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.layout.addWidget(self.table)

        self.layer_info = layer_info or []
        self.endpoints = sorted(endpoints or [])
        self.populate_table()

        # Choix de l'action
        self.action_group = QtWidgets.QGroupBox("Action à entreprendre")
        self.action_layout = QtWidgets.QVBoxLayout(self.action_group)

        self.radio_migrate = QtWidgets.QRadioButton("Migration Initiale (Pousser les données locales vers l'API)")
        self.radio_migrate.setToolTip("Utilisez ceci si vos données sont dans QGIS et que vous voulez remplir la base de données.")

        self.radio_workflow = QtWidgets.QRadioButton("Workflow de Collecte (Synchronisation Mergin Map)")
        self.radio_workflow.setToolTip("Utilisez ceci pour préparer une mission terrain ou valider un retour de collecte.")
        self.radio_workflow.setChecked(True)

        self.radio_refresh = QtWidgets.QRadioButton("Mise à jour / Rafraîchir (Télécharger les données de l'API vers QGIS)")
        self.radio_refresh.setToolTip("Utilisez ceci pour mettre à jour vos couches locales avec le contenu actuel du serveur.")

        self.action_layout.addWidget(self.radio_migrate)
        self.action_layout.addWidget(self.radio_workflow)
        self.action_layout.addWidget(self.radio_refresh)
        self.layout.addWidget(self.action_group)

        # Boutons
        self.button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def populate_table(self):
        self.table.setRowCount(len(self.layer_info))
        for i, info in enumerate(self.layer_info):
            # Checkbox sélection
            check_box = QtWidgets.QCheckBox()
            check_box.setChecked(True)
            container = QtWidgets.QWidget()
            layout = QtWidgets.QHBoxLayout(container)
            layout.addWidget(check_box)
            layout.setAlignment(QtCore.Qt.AlignCenter)
            layout.setContentsMargins(0,0,0,0)
            self.table.setCellWidget(i, 0, container)

            # Nom
            name_item = QtWidgets.QTableWidgetItem(info['name'])
            name_item.setFlags(name_item.flags() ^ QtCore.Qt.ItemIsEditable)
            self.table.setItem(i, 1, name_item)

            # Type
            type_str = "Spatial" if info['is_spatial'] else "Alphanumérique"
            type_item = QtWidgets.QTableWidgetItem(type_str)
            type_item.setFlags(type_item.flags() ^ QtCore.Qt.ItemIsEditable)
            self.table.setItem(i, 2, type_item)

            # Combo Mapping
            combo = QtWidgets.QComboBox()
            combo.setEditable(True)
            combo.addItems(["-- Ignorer --"] + self.endpoints)

            if info['endpoint'] and info['endpoint'] in self.endpoints:
                idx = combo.findText(info['endpoint'])
                combo.setCurrentIndex(idx)
            else:
                # Tentative de match
                found = False
                ln = info['name'].lower()
                for ep in self.endpoints:
                    if ep.lower() == ln or ep.lower() in ln:
                        combo.setCurrentIndex(combo.findText(ep))
                        found = True
                        break
                if not found:
                    combo.setCurrentIndex(0)

            self.table.setCellWidget(i, 3, combo)

    def get_results(self):
        selected_mappings = {}
        for i in range(self.table.rowCount()):
            container = self.table.cellWidget(i, 0)
            checkbox = container.findChild(QtWidgets.QCheckBox)
            if checkbox.isChecked():
                layer_id = self.layer_info[i]['layer_id']
                combo = self.table.cellWidget(i, 3)
                endpoint = combo.currentText()
                if endpoint != "-- Ignorer --":
                    selected_mappings[layer_id] = endpoint

        if self.radio_migrate.isChecked():
            action = "migrate"
        elif self.radio_refresh.isChecked():
            action = "refresh"
        else:
            action = "workflow"

        return action, selected_mappings
