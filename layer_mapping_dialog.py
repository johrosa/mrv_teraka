# -*- coding: utf-8 -*-
import os
import json
from qgis.PyQt import uic, QtWidgets, QtCore
from qgis.core import QgsProject, QgsMapLayer


class FieldMappingDialog(QtWidgets.QDialog):
    """Sous-dialog pour mapper les champs QGIS vers les colonnes API."""

    def __init__(self, parent=None, layer=None, existing_field_map=None):
        super(FieldMappingDialog, self).__init__(parent)

        self.setWindowFlags(
            self.windowFlags() |
            QtCore.Qt.WindowType.WindowMinimizeButtonHint |
            QtCore.Qt.WindowType.WindowMaximizeButtonHint |
            QtCore.Qt.WindowType.WindowCloseButtonHint
        )
        self.layer = layer
        self.setWindowTitle(f"Field Mappings — {layer.name() if layer else ''}")
        self.resize(450, 300)

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

        # Champs spécifiques à QGIS qui ne doivent pas être envoyés à l'API par défaut
        QGIS_INTERNAL_FIELDS = {'fid', 'id_0'}

        for i, field_name in enumerate(fields):
            # Colonne 0 : checkbox "Inclure"
            chk = QtWidgets.QTableWidgetItem()
            chk.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            
            # Décoche automatiquement si c'est un champ interne QGIS (sauf si explicitement mappé)
            if field_name in QGIS_INTERNAL_FIELDS and field_name not in existing_field_map:
                chk.setCheckState(QtCore.Qt.Unchecked)
            else:
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

        self.setWindowFlags(
            self.windowFlags() |
            QtCore.Qt.WindowType.WindowMinimizeButtonHint |
            QtCore.Qt.WindowType.WindowMaximizeButtonHint |
            QtCore.Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowTitle("Mapping des Couches vers l'API")
        self.resize(850, 380)

        self.layout = QtWidgets.QVBoxLayout(self)

        self.label = QtWidgets.QLabel("Associez chaque couche QGIS à une table de l'API :")
        self.layout.addWidget(self.label)

        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "",
            "Couche QGIS",
            "Type",
            "Table API (Endpoint)",
            "Clé primaire",
            "Géométrie",
            "Field Mappings",
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QtWidgets.QHeaderView.ResizeToContents)
        self.layout.addWidget(self.table)

        # Bouton sous le tableau
        btn_layout = QtWidgets.QHBoxLayout()
        
        self.select_all_btn = QtWidgets.QPushButton("Sélectionner tout")
        self.select_all_btn.clicked.connect(self._select_all_layers)
        btn_layout.addWidget(self.select_all_btn)
        
        self.deselect_all_btn = QtWidgets.QPushButton("Désélectionner tout")
        self.deselect_all_btn.clicked.connect(self._deselect_all_layers)
        btn_layout.addWidget(self.deselect_all_btn)
        
        self.field_mapping_btn = QtWidgets.QPushButton("Configurer les field mappings…")
        self.field_mapping_btn.setEnabled(False)
        self.field_mapping_btn.clicked.connect(self._open_field_mapping_from_selection)
        btn_layout.addWidget(self.field_mapping_btn)
        btn_layout.addStretch()
        self.layout.addLayout(btn_layout)

        self.layers = layers or []
        self.endpoints = sorted(endpoints or [])
        self._all_mappings = self._load_all_mappings()
        self._field_maps = {}

        self.populate_table()

        self.table.itemSelectionChanged.connect(self._on_selection_changed)

        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def _load_all_mappings(self):
        """Charge les mappings depuis load_layer_mapping pour appliquer l'inférence UUID."""
        from .config_postgrest import load_layer_mapping
        plugin_dir = os.path.dirname(__file__)
        # Utiliser load_layer_mapping qui applique l'inférence UUID des PKs
        return load_layer_mapping(plugin_dir)

    def _mapping_for_endpoint(self, endpoint):
        if not endpoint or endpoint == "-- Ignorer --":
            return {}
        for mapping in self._all_mappings.values():
            if mapping.get('endpoint') == endpoint:
                return mapping
        return {}

    def _set_endpoint_metadata(self, row, endpoint):
        mapping = self._mapping_for_endpoint(endpoint)
        pk_field = mapping.get('pk_field') or "id"
        geom_field = mapping.get('geom_field') or ""
        geom_text = geom_field if geom_field else "Aucune"

        pk_item = QtWidgets.QTableWidgetItem(pk_field if endpoint != "-- Ignorer --" else "—")
        pk_item.setFlags(pk_item.flags() ^ QtCore.Qt.ItemIsEditable)
        self.table.setItem(row, 4, pk_item)

        geom_item = QtWidgets.QTableWidgetItem(geom_text if endpoint != "-- Ignorer --" else "—")
        geom_item.setFlags(geom_item.flags() ^ QtCore.Qt.ItemIsEditable)
        self.table.setItem(row, 5, geom_item)

    def _on_endpoint_changed(self, row, endpoint):
        self._set_endpoint_metadata(row, endpoint)
        if row in self._field_maps:
            del self._field_maps[row]
            btn = self.table.cellWidget(row, 6)
            if isinstance(btn, QtWidgets.QPushButton):
                btn.setText("Configurer…")
        self._on_selection_changed()

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

            combo.currentTextChanged.connect(lambda text, row=i: self._on_endpoint_changed(row, text))
            self.table.setCellWidget(i, 3, combo)
            self._set_endpoint_metadata(i, combo.currentText())

            # Colonne 6 : bouton "Configurer…"
            btn = QtWidgets.QPushButton("Configurer…")
            btn.setToolTip("Définir le mapping des champs pour cette couche")
            btn.clicked.connect(lambda checked, row=i: self._open_field_mapping(row))
            self.table.setCellWidget(i, 6, btn)

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
            btn = self.table.cellWidget(row, 6)
            btn.setText(f"✓ {len(field_map)} champ(s)" if field_map else "Configurer…")
        self._on_selection_changed()

    def _open_field_mapping_from_selection(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return
        self._open_field_mapping(selected_rows[0].row())

    def _select_all_layers(self):
        """Sélectionne toutes les couches."""
        for i in range(self.table.rowCount()):
            item = self.table.item(i, 0)
            item.setCheckState(QtCore.Qt.Checked)
        self._on_selection_changed()

    def _deselect_all_layers(self):
        """Désélectionne toutes les couches."""
        for i in range(self.table.rowCount()):
            item = self.table.item(i, 0)
            item.setCheckState(QtCore.Qt.Unchecked)
        self._on_selection_changed()

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
