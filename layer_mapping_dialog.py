# -*- coding: utf-8 -*-
import os
from qgis.PyQt import uic, QtWidgets, QtCore
from qgis.core import QgsProject, QgsMapLayer


class FieldMappingDialog(QtWidgets.QDialog):
    """Sous-dialog pour mapper les champs QGIS vers les colonnes API."""

    def __init__(self, parent=None, layer=None, existing_field_map=None):
        super(FieldMappingDialog, self).__init__(parent)
        self.layer = layer
        self.setWindowTitle(f"Field Mappings — {layer.name() if layer else ''}")
        self.resize(500, 350)

        layout = QtWidgets.QVBoxLayout(self)

        layout.addWidget(QtWidgets.QLabel(
            "Associez les champs QGIS aux colonnes de l'API :\n"
            "(laisser vide = nom identique, décocher = exclure le champ)"
        ))

        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Inclure", "Champ QGIS", "Colonne API"])
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        layout.addWidget(self.table)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._populate(existing_field_map or {})

    def _populate(self, existing_field_map):
        if not self.layer:
            return

        fields = [f.name() for f in self.layer.fields()]
        self.table.setRowCount(len(fields))

        for i, field_name in enumerate(fields):
            # Colonne 0 : checkbox "Inclure"
            chk = QtWidgets.QTableWidgetItem()
            chk.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            excluded = existing_field_map.get(field_name) is False
            chk.setCheckState(QtCore.Qt.Unchecked if excluded else QtCore.Qt.Checked)
            self.table.setItem(i, 0, chk)

            # Colonne 1 : nom QGIS (non éditable)
            qgis_item = QtWidgets.QTableWidgetItem(field_name)
            qgis_item.setFlags(qgis_item.flags() ^ QtCore.Qt.ItemIsEditable)
            self.table.setItem(i, 1, qgis_item)

            # Colonne 2 : nom API (éditable, vide = identique)
            api_name = existing_field_map.get(field_name) or ""
            api_item = QtWidgets.QTableWidgetItem("" if api_name is False else api_name)
            self.table.setItem(i, 2, api_item)

    def get_field_map(self):
        """
        Retourne un dict :
          { 'qgis_field': 'api_column' }  # renommé
          { 'qgis_field': '' }            # inclus, même nom
          # champ absent = exclu
        """
        result = {}
        for i in range(self.table.rowCount()):
            included = self.table.item(i, 0).checkState() == QtCore.Qt.Checked
            if not included:
                continue
            qgis_name = self.table.item(i, 1).text()
            api_name = self.table.item(i, 2).text().strip()
            result[qgis_name] = api_name
        return result


class LayerMappingDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, layers=None, endpoints=None):
        super(LayerMappingDialog, self).__init__(parent)
        self.setWindowTitle("Mapping des Couches vers l'API")
        self.resize(850, 450)

        self.layout = QtWidgets.QVBoxLayout(self)

        self.label = QtWidgets.QLabel("Associez chaque couche QGIS à une table de l'API :")
        self.layout.addWidget(self.label)

        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "",
            "Couche QGIS",
            "Type",
            "Table API (Endpoint)",
            "Field Mappings",
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)
        self.layout.addWidget(self.table)

        # Bouton sous le tableau
        btn_layout = QtWidgets.QHBoxLayout()
        self.field_mapping_btn = QtWidgets.QPushButton("Configurer les field mappings…")
        self.field_mapping_btn.setEnabled(False)
        self.field_mapping_btn.clicked.connect(self._open_field_mapping_from_selection)
        btn_layout.addWidget(self.field_mapping_btn)
        btn_layout.addStretch()
        self.layout.addLayout(btn_layout)

        self.layers = layers or []
        self.endpoints = sorted(endpoints or [])
        self._field_maps = {}

        self.populate_table()

        self.table.itemSelectionChanged.connect(self._on_selection_changed)

        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def populate_table(self):
        self.table.setRowCount(len(self.layers))
        for i, layer in enumerate(self.layers):

            # Colonne 0 : checkbox sélection
            chk = QtWidgets.QTableWidgetItem()
            chk.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            chk.setCheckState(QtCore.Qt.Checked)
            self.table.setItem(i, 0, chk)

            # Colonne 1 : nom de la couche
            name_item = QtWidgets.QTableWidgetItem(layer.name())
            name_item.setFlags(name_item.flags() ^ QtCore.Qt.ItemIsEditable)
            self.table.setItem(i, 1, name_item)

            # Colonne 2 : type de la couche
            type_map = {
                QgsMapLayer.VectorLayer: "Vecteur",
                QgsMapLayer.RasterLayer: "Raster",
                QgsMapLayer.MeshLayer: "Mesh",
                QgsMapLayer.AnnotationLayer: "Annotation",
            }
            type_item = QtWidgets.QTableWidgetItem(type_map.get(layer.type(), "Inconnu"))
            type_item.setFlags(type_item.flags() ^ QtCore.Qt.ItemIsEditable)
            self.table.setItem(i, 2, type_item)

            # Colonne 3 : sélecteur d'endpoint
            combo = QtWidgets.QComboBox()
            combo.setEditable(True)
            combo.addItems(["-- Ignorer --"] + self.endpoints)

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

            self.table.setCellWidget(i, 3, combo)

            # Colonne 4 : bouton "Configurer…"
            btn = QtWidgets.QPushButton("Configurer…")
            btn.setToolTip("Définir le mapping des champs pour cette couche")
            btn.clicked.connect(lambda checked, row=i: self._open_field_mapping(row))
            self.table.setCellWidget(i, 4, btn)

    def _on_selection_changed(self):
        selected_rows = self.table.selectionModel().selectedRows()
        self.field_mapping_btn.setEnabled(bool(selected_rows))
        if selected_rows:
            row = selected_rows[0].row()
            layer_name = self.layers[row].name()
            n = len(self._field_maps.get(row, {}))
            label = f"Configurer les field mappings — {layer_name}"
            if n:
                label += f" ({n} champ(s) configuré(s))"
            self.field_mapping_btn.setText(label)
        else:
            self.field_mapping_btn.setText("Configurer les field mappings…")

    def _open_field_mapping(self, row):
        layer = self.layers[row]
        existing = self._field_maps.get(row, {})
        dlg = FieldMappingDialog(self, layer=layer, existing_field_map=existing)
        if dlg.exec_():
            field_map = dlg.get_field_map()
            self._field_maps[row] = field_map
            btn = self.table.cellWidget(row, 4)
            btn.setText(f"✓ {len(field_map)} champ(s)" if field_map else "Configurer…")
        self._on_selection_changed()

    def _open_field_mapping_from_selection(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return
        self._open_field_mapping(selected_rows[0].row())

    def get_mapping(self):
        """
        Retourne un dict par layer_id :
        {
            layer_id: {
                'endpoint': 'nom_endpoint',
                'field_map': { 'qgis_field': 'api_column', ... }
            }
        }
        """
        mapping = {}
        for i in range(self.table.rowCount()):
            checked = self.table.item(i, 0).checkState() == QtCore.Qt.Checked
            if not checked:
                continue
            layer = self.layers[i]
            combo = self.table.cellWidget(i, 3)
            endpoint = combo.currentText()
            if endpoint == "-- Ignorer --":
                continue
            mapping[layer.id()] = {
                'endpoint': endpoint,
                'field_map': self._field_maps.get(i, {}),
            }
        return mapping