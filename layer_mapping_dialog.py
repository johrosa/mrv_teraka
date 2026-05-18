# -*- coding: utf-8 -*-
import os
from qgis.PyQt import uic, QtWidgets, QtCore
from qgis.core import QgsProject, QgsMapLayer

class LayerMappingDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, layers=None, endpoints=None):
        super(LayerMappingDialog, self).__init__(parent)
        self.setWindowTitle("Mapping des Couches vers l'API")
        self.resize(600, 400)

        self.layout = QtWidgets.QVBoxLayout(self)

        self.label = QtWidgets.QLabel("Associez chaque couche QGIS à une table de l'API :")
        self.layout.addWidget(self.label)

        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Couche QGIS", "Table API (Endpoint)"])
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.layout.addWidget(self.table)

        self.layers = layers or []
        self.endpoints = sorted(endpoints or [])

        self.populate_table()

        self.button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

        self.mapping = {}

    def populate_table(self):
        self.table.setRowCount(len(self.layers))
        for i, layer in enumerate(self.layers):
            # Nom de la couche
            name_item = QtWidgets.QTableWidgetItem(layer.name())
            name_item.setFlags(name_item.flags() ^ QtCore.Qt.ItemIsEditable)
            self.table.setItem(i, 0, name_item)

            # Sélecteur d'endpoint
            combo = QtWidgets.QComboBox()
            combo.setEditable(True)
            combo.addItems(["-- Ignorer --"] + self.endpoints)

            # Essayer de trouver une correspondance par défaut
            layer_name = layer.name().lower()
            found = False
            for ep in self.endpoints:
                if ep.lower() in layer_name or layer_name in ep.lower():
                    idx = combo.findText(ep)
                    if idx >= 0:
                        combo.setCurrentIndex(idx)
                        found = True
                        break

            if not found:
                combo.setCurrentIndex(0)

            self.table.setCellWidget(i, 1, combo)

    def get_mapping(self):
        mapping = {}
        for i in range(self.table.rowCount()):
            layer = self.layers[i]
            combo = self.table.cellWidget(i, 1)
            endpoint = combo.currentText()
            if endpoint != "-- Ignorer --":
                mapping[layer.id()] = endpoint
        return mapping
