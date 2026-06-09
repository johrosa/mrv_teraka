# -*- coding: utf-8 -*-
import os
import json
from qgis.PyQt import QtWidgets, QtCore, QtGui
from qgis.core import QgsProject, QgsMapLayer


class FieldMappingDialog(QtWidgets.QDialog):
    """Sous-dialog pour mapper les champs QGIS vers les colonnes API."""

    def __init__(self, parent=None, layer=None, existing_field_map=None, api_columns=None):
        super(FieldMappingDialog, self).__init__(parent)

        self.setWindowFlags(
            self.windowFlags() |
            QtCore.Qt.WindowType.WindowMinimizeButtonHint |
            QtCore.Qt.WindowType.WindowMaximizeButtonHint |
            QtCore.Qt.WindowType.WindowCloseButtonHint
        )
        self.layer = layer
        self.api_columns = api_columns or []
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
            api_name = existing_field_map.get(field_name)
            if api_name is None:
                # Tentative de pré-remplissage via api_columns
                if field_name in self.api_columns:
                    api_name = field_name
                else:
                    api_name = ""

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


class MissionConfirmationDialog(QtWidgets.QDialog):
    """Dialogue pour confirmer la création d'une mission et renommer le projet."""

    def __init__(self, parent=None, suggested_name="", layers_count=0):
        super(MissionConfirmationDialog, self).__init__(parent)
        self.setWindowTitle("Confirmation de création de mission")
        self.resize(400, 200)

        layout = QtWidgets.QVBoxLayout(self)

        layout.addWidget(QtWidgets.QLabel(
            f"Vous allez créer une nouvelle mission Mergin Maps avec {layers_count} couche(s).\n"
            "Veuillez confirmer ou modifier le nom du projet :"
        ))

        self.project_name_edit = QtWidgets.QLineEdit()
        self.project_name_edit.setText(suggested_name)
        layout.addWidget(self.project_name_edit)

        # On peut ajouter un petit avertissement sur les caractères spéciaux si besoin
        self.hint_label = QtWidgets.QLabel(
            "<small>Note : Utilisez des caractères alphanumériques, tirets ou underscores.</small>"
        )
        self.hint_label.setWordWrap(True)
        layout.addWidget(self.hint_label)

        layout.addStretch()

        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def get_project_name(self):
        return self.project_name_edit.text().strip()


class MissionConfirmationDialog(QtWidgets.QDialog):
    """Dialogue pour confirmer la création d'une mission et renommer le projet."""

    def __init__(self, parent=None, suggested_name="", layers_count=0):
        super(MissionConfirmationDialog, self).__init__(parent)

        self.setWindowFlags(
            self.windowFlags() |
            QtCore.Qt.WindowType.WindowMinimizeButtonHint |
            QtCore.Qt.WindowType.WindowMaximizeButtonHint |
            QtCore.Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowTitle("Confirmation de création de mission")
        self.resize(400, 200)

        layout = QtWidgets.QVBoxLayout(self)

        layout.addWidget(QtWidgets.QLabel(
            f"Vous allez créer une nouvelle mission Mergin Maps avec {layers_count} couche(s).\n"
            "Veuillez confirmer ou modifier le nom du projet :"
        ))

        self.project_name_edit = QtWidgets.QLineEdit()
        self.project_name_edit.setText(suggested_name)
        layout.addWidget(self.project_name_edit)

        # On peut ajouter un petit avertissement sur les caractères spéciaux si besoin
        self.hint_label = QtWidgets.QLabel(
            "<small>Note : Utilisez des caractères alphanumériques, tirets ou underscores.</small>"
        )
        self.hint_label.setWordWrap(True)
        layout.addWidget(self.hint_label)

        layout.addStretch()

        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def get_project_name(self):
        return self.project_name_edit.text().strip()


class ProjectActionDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, layer_info=None, endpoints=None):
        """
        layer_info: List of dicts {layer_id, name, endpoint, type}
        endpoints: List of available API endpoints
        """
        super(ProjectActionDialog, self).__init__(parent)

        self.setWindowFlags(
            self.windowFlags() |
            QtCore.Qt.WindowType.WindowMinimizeButtonHint |
            QtCore.Qt.WindowType.WindowMaximizeButtonHint |
            QtCore.Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowTitle("Analyse et Actions du Projet")
        self.resize(900, 550)

        self._all_mappings = self._load_all_mappings()

        self.layout = QtWidgets.QVBoxLayout(self)

        self.label = QtWidgets.QLabel("Analyse des couches du projet et correspondances API :")
        self.label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.layout.addWidget(self.label)

        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Sélection",
            "Couche QGIS",
            "Type",
            "Table API (Mapping)",
            "Field Mappings",
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.layout.addWidget(self.table)

        self.layer_info = layer_info or []
        self.endpoints = sorted(endpoints or [])
        self._field_maps = {}

        self.populate_table()

        # Bouton sous le tableau
        btn_layout = QtWidgets.QHBoxLayout()
        self.field_mapping_btn = QtWidgets.QPushButton("Configurer les field mappings…")
        self.field_mapping_btn.setEnabled(False)
        self.field_mapping_btn.clicked.connect(self._open_field_mapping_from_selection)
        btn_layout.addWidget(self.field_mapping_btn)
        btn_layout.addStretch()
        self.layout.addLayout(btn_layout)

        self.table.itemSelectionChanged.connect(self._on_selection_changed)

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

        self.radio_update_mapping = QtWidgets.QRadioButton("Mettre à jour le mapping local")
        self.radio_update_mapping.setToolTip("Enregistre les correspondances choisies pour l'utilisateur actuel dans layer_table_mapping.json.")

        self.action_layout.addWidget(self.radio_migrate)
        self.action_layout.addWidget(self.radio_workflow)
        self.action_layout.addWidget(self.radio_refresh)
        self.action_layout.addWidget(self.radio_update_mapping)
        self.layout.addWidget(self.action_group)

        # Boutons
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def _load_all_mappings(self):
        """Charge tout le contenu de layer_table_mapping.json."""
        plugin_dir = os.path.dirname(__file__)
        path = os.path.join(plugin_dir, "layer_table_mapping.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f).get("mappings", {})
            except Exception:
                pass
        return {}

    def populate_table(self):
        self.table.setRowCount(len(self.layer_info))
        for i, info in enumerate(self.layer_info):

            # Colonne 0 : checkbox sélection
            check_box = QtWidgets.QCheckBox()
            check_box.setChecked(True)
            container = QtWidgets.QWidget()
            layout = QtWidgets.QHBoxLayout(container)
            layout.addWidget(check_box)
            layout.setAlignment(QtCore.Qt.AlignCenter)
            layout.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(i, 0, container)

            # Colonne 1 : nom de la couche
            name_item = QtWidgets.QTableWidgetItem(info['name'])
            name_item.setFlags(name_item.flags() ^ QtCore.Qt.ItemIsEditable)
            self.table.setItem(i, 1, name_item)

            # Colonne 2 : type
            type_str = "Spatial" if info['is_spatial'] else "Alphanumérique"
            type_item = QtWidgets.QTableWidgetItem(type_str)
            type_item.setFlags(type_item.flags() ^ QtCore.Qt.ItemIsEditable)
            self.table.setItem(i, 2, type_item)

            # Colonne 3 : combo endpoint
            combo = QtWidgets.QComboBox()
            combo.setEditable(True)
            combo.addItems(["-- Ignorer --"] + self.endpoints)

            endpoint = info.get('mapping')
            if endpoint and endpoint in self.endpoints:
                idx = combo.findText(endpoint)
                combo.setCurrentIndex(idx)
            else:
                found = False
                ln = info['name'].lower()
                for ep in self.endpoints:
                    if ep.lower() == ln or ep.lower() in ln:
                        combo.setCurrentIndex(combo.findText(ep))
                        found = True
                        break
                if not found:
                    combo.setCurrentIndex(0)

            combo.currentTextChanged.connect(lambda text, r=i: self._on_endpoint_changed(r, text))
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
            layer_name = self.layer_info[row]['name']
            n = len(self._field_maps.get(row, {}))
            label = f"Configurer les field mappings — {layer_name}"
            if n:
                label += f" ({n} champ(s) configuré(s))"
            self.field_mapping_btn.setText(label)
        else:
            self.field_mapping_btn.setText("Configurer les field mappings…")

    def _on_endpoint_changed(self, row, text):
        """Réinitialise les mappings de champs si l'endpoint change."""
        if row in self._field_maps:
            del self._field_maps[row]
            btn = self.table.cellWidget(row, 4)
            if isinstance(btn, QtWidgets.QPushButton):
                btn.setText("Configurer…")
            self._on_selection_changed()

    def _open_field_mapping(self, row):
        # Récupérer la vraie couche QGIS depuis le layer_id
        layer_id = self.layer_info[row]['id']
        layer = QgsProject.instance().mapLayer(layer_id)
        if not layer:
            QtWidgets.QMessageBox.warning(
                self, "Couche introuvable",
                "La couche QGIS n'est plus disponible dans le projet."
            )
            return

        existing = self._field_maps.get(row, {})

        # Récupérer les colonnes API attendues pour l'endpoint choisi
        combo = self.table.cellWidget(row, 3)
        endpoint = combo.currentText()
        api_columns = []
        if endpoint != "-- Ignorer --":
            # 1. On cherche d'abord si le nom de la couche QGIS est dans le mapping
            layer_name = self.layer_info[row]['name']
            if layer_name in self._all_mappings:
                m_info = self._all_mappings[layer_name]
                if m_info.get('endpoint') == endpoint:
                    api_columns = m_info.get('columns', [])

            # 2. Sinon on cherche par endpoint (plus générique)
            if not api_columns:
                for m_info in self._all_mappings.values():
                    if m_info.get('endpoint') == endpoint:
                        api_columns = m_info.get('columns', [])
                        break

        dlg = FieldMappingDialog(self, layer=layer, existing_field_map=existing, api_columns=api_columns)
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

    def get_results(self):
        selected_mappings = {}
        for i in range(self.table.rowCount()):
            container = self.table.cellWidget(i, 0)
            checkbox = container.findChild(QtWidgets.QCheckBox)
            if checkbox.isChecked():
                layer_id = self.layer_info[i]['id']
                combo = self.table.cellWidget(i, 3)
                endpoint = combo.currentText()
                if endpoint != "-- Ignorer --":
                    selected_mappings[layer_id] = {
                        'endpoint': endpoint,
                        'field_map': self._field_maps.get(i, {}),
                    }

        if self.radio_migrate.isChecked():
            action = "migrate"
        elif self.radio_refresh.isChecked():
            action = "refresh"
        elif self.radio_update_mapping.isChecked():
            action = "update_mapping"
        else:
            action = "workflow"

        return action, selected_mappings