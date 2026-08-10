# -*- coding: utf-8 -*-
"""
Dialog for selecting which layers to refresh and viewing their mappings.
"""

from qgis.PyQt import QtWidgets, QtCore
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsMapLayer

from .layer_mapping_dialog import FieldMappingDialog


class RefreshLayersDialog(QtWidgets.QDialog):
    """Dialog to select layers/endpoints and manage their mappings."""

    def __init__(
        self,
        parent=None,
        layer_mappings=None,
        title="Sélectionner les couches à rafraîchir",
        intro="Sélectionnez les couches à rafraîchir et vérifiez leurs mappings :",
        item_label="Couche",
    ):
        super(RefreshLayersDialog, self).__init__(parent)

        self.setWindowFlags(
            self.windowFlags() |
            QtCore.Qt.WindowType.WindowMinimizeButtonHint |
            QtCore.Qt.WindowType.WindowMaximizeButtonHint |
            QtCore.Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowTitle(title)
        self.resize(800, 420)

        self.layer_mappings = layer_mappings or {}
        self._field_maps = {}

        layout = QtWidgets.QVBoxLayout(self)

        # Title label
        title_label = QtWidgets.QLabel(intro)
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        # Table with layers and mappings
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            item_label,
            "Endpoint",
            "Champ PK",
            "Champ Géométrie",
            "Actions"
        ])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSortIndicatorShown(True)
        self.table.horizontalHeader().setSectionsClickable(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)
        layout.addWidget(self.table)

        # Buttons row
        buttons_layout = QtWidgets.QHBoxLayout()

        self.select_all_btn = QtWidgets.QPushButton("Sélectionner tout")
        self.select_all_btn.clicked.connect(self.select_all)
        buttons_layout.addWidget(self.select_all_btn)

        self.deselect_all_btn = QtWidgets.QPushButton("Désélectionner tout")
        self.deselect_all_btn.clicked.connect(self.deselect_all)
        buttons_layout.addWidget(self.deselect_all_btn)

        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)

        # Dialog buttons
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self._populate_table()
        self.select_all()

    def _populate_table(self):
        """Populate the table with layer mappings."""
        self.table.setRowCount(len(self.layer_mappings))
        self.table.setSortingEnabled(False)

        for i, (layer_name, mapping) in enumerate(self.layer_mappings.items()):
            # Column 0: Layer name
            name_item = QtWidgets.QTableWidgetItem(layer_name)
            name_item.setFlags(name_item.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(i, 0, name_item)

            # Column 1: Endpoint
            endpoint = mapping.get('endpoint', '—')
            endpoint_item = QtWidgets.QTableWidgetItem(endpoint)
            endpoint_item.setFlags(endpoint_item.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(i, 1, endpoint_item)

            # Column 2: PK field
            pk_field = mapping.get('pk_field', 'id')
            pk_item = QtWidgets.QTableWidgetItem(pk_field)
            pk_item.setFlags(pk_item.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(i, 2, pk_item)

            # Column 3: Geometry field
            geom_field = mapping.get('geom_field')
            geom_text = geom_field if geom_field else "Aucune"
            geom_item = QtWidgets.QTableWidgetItem(geom_text)
            geom_item.setFlags(geom_item.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(i, 3, geom_item)

            # Column 4: Edit button
            btn = QtWidgets.QPushButton("Modifier...")
            btn.setToolTip(f"Modifier le mapping pour {layer_name}")
            btn.clicked.connect(lambda checked, name=layer_name: self._edit_mapping(name))
            self.table.setCellWidget(i, 4, btn)
        self.table.setSortingEnabled(True)

    def _edit_mapping(self, layer_name):
        """Open dialog to edit mapping for the given row."""
        mapping = self.layer_mappings[layer_name]

        # Create a simple dialog for editing mapping
        dlg = EditMappingDialog(
            self,
            layer_name=layer_name,
            mapping=mapping
        )

        if dlg.exec_():
            updated_mapping = dlg.get_mapping()
            self.layer_mappings[layer_name] = updated_mapping
            self._refresh_row(layer_name)

    def _refresh_row(self, layer_name):
        """Refresh a row in the table after editing."""
        mapping = self.layer_mappings[layer_name]
        row = self._row_for_layer_name(layer_name)
        if row < 0:
            return

        self.table.item(row, 1).setText(mapping.get('endpoint', '—'))
        self.table.item(row, 2).setText(mapping.get('pk_field', 'id'))
        geom_text = mapping.get('geom_field') if mapping.get('geom_field') else "Aucune"
        self.table.item(row, 3).setText(geom_text)

    def select_all(self):
        """Select all layers."""
        self.table.selectAll()

    def deselect_all(self):
        """Deselect all layers."""
        self.table.clearSelection()

    def _row_for_layer_name(self, layer_name):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.text() == layer_name:
                return row
        return -1

    def get_selected_layers(self):
        """
        Returns dict of selected layers with their mappings.
        { 'layer_name': {'endpoint': '...', 'pk_field': '...', 'geom_field': '...'} }
        """
        selected = {}
        rows = sorted({index.row() for index in self.table.selectionModel().selectedRows()})
        for row in rows:
            item = self.table.item(row, 0)
            layer_name = item.text() if item else None
            if layer_name in self.layer_mappings:
                selected[layer_name] = self.layer_mappings[layer_name]
        return selected


class EditMappingDialog(QtWidgets.QDialog):
    """Dialog to edit a single layer's mapping."""

    def __init__(self, parent=None, layer_name=None, mapping=None):
        super(EditMappingDialog, self).__init__(parent)

        self.setWindowTitle(f"Modifier le mapping — {layer_name}")
        self.resize(500, 300)

        self.mapping = mapping or {}

        layout = QtWidgets.QVBoxLayout(self)

        # Title
        layout.addWidget(QtWidgets.QLabel(f"Couche : <b>{layer_name}</b>"))

        # Form layout
        form = QtWidgets.QFormLayout()

        # Endpoint
        self.endpoint_input = QtWidgets.QLineEdit()
        self.endpoint_input.setText(self.mapping.get('endpoint', ''))
        form.addRow("Endpoint :", self.endpoint_input)

        # PK field
        self.pk_input = QtWidgets.QLineEdit()
        self.pk_input.setText(self.mapping.get('pk_field', 'id'))
        form.addRow("Champ PK :", self.pk_input)

        # Geom field
        self.geom_input = QtWidgets.QLineEdit()
        self.geom_input.setText(self.mapping.get('geom_field', '') or '')
        self.geom_input.setPlaceholderText("Laisser vide si aucune géométrie")
        form.addRow("Champ Géométrie :", self.geom_input)

        layout.addLayout(form)
        layout.addStretch()

        # Buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_mapping(self):
        """Returns the edited mapping."""
        return {
            'endpoint': self.endpoint_input.text().strip(),
            'pk_field': self.pk_input.text().strip() or 'id',
            'geom_field': self.geom_input.text().strip() or None,
        }
