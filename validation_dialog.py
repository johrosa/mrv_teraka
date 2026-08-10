# -*- coding: utf-8 -*-
"""
Formulaire de validation des données au retour du terrain
Permet de vérifier, corriger et fusionner les données collectées avec Mergin
"""

from qgis.PyQt.QtCore import Qt, QSize, pyqtSignal, QVariant, QSignalBlocker
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QTableWidget, QTableWidgetItem, QComboBox,
    QLineEdit, QSpinBox, QDoubleSpinBox, QMessageBox, QProgressBar,
    QHeaderView, QCheckBox, QTextEdit, QGroupBox, QFormLayout, QWidget,
    QAbstractItemView
)
from qgis.PyQt.QtGui import QColor, QFont
from qgis.core import QgsProject, QgsVectorLayer, QgsExpression, QgsExpressionContext, QgsExpressionContextUtils, QgsFeature, QgsField, QgsFields
import json
import os
import re
from .business_rules import BusinessRulesEngine
from .utils import Utils


DISPLAY_VALUE_MAX_LENGTH = 180
TOOLTIP_VALUE_MAX_LENGTH = 1000
GEOMETRY_FIELD_NAMES = {"geom", "geometry", "the_geom"}
FULL_VALUE_ROLE_MARKER = "__mrv_full_value__"


def _is_geometry_field(field_name):
    return str(field_name or "").strip().lower() in GEOMETRY_FIELD_NAMES


def _compact_value_for_display(value, field_name=None, max_length=DISPLAY_VALUE_MAX_LENGTH):
    """Retourne une valeur courte pour l'UI sans modifier la donnée source."""
    if value is None:
        text = ""
    elif _is_geometry_field(field_name) and isinstance(value, dict):
        geom_type = value.get("type", "géométrie")
        coords = value.get("coordinates")
        if coords is not None:
            text = f"{geom_type} - coordonnées masquées"
        else:
            text = str(geom_type)
    elif isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value)

    if _is_geometry_field(field_name) and len(text) > max_length:
        return "Géométrie - coordonnées masquées"

    if len(text) <= max_length:
        return text

    return f"{text[:max_length]}... ({len(text)} caractères)"


def _compact_value_for_tooltip(value, field_name=None):
    if _is_geometry_field(field_name):
        return "Valeur complète masquée pour éviter une boîte de dialogue trop longue."

    return _compact_value_for_display(value, field_name, TOOLTIP_VALUE_MAX_LENGTH)


def _pack_full_value(value):
    return (FULL_VALUE_ROLE_MARKER, value)


def _unpack_full_value(packed, fallback):
    if isinstance(packed, tuple) and len(packed) == 2 and packed[0] == FULL_VALUE_ROLE_MARKER:
        return packed[1]
    return fallback


def _normalize_uuid(value):
    if value is None:
        return None
    text = str(value).strip().replace('{', '').replace('}', '')
    if re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', text, re.IGNORECASE):
        return text.lower()
    return None


def _stamp_verifier_uuid(row, user_uuid):
    if not isinstance(row, dict) or not user_uuid:
        return
    row['uuid_verificateur'] = user_uuid
    if 'uuid_validateur' in row:
        row['uuid_validateur'] = user_uuid


class DataValidationDialog(QDialog):
    """Formulaire de validation et fusion des données collectées"""
    
    data_merged = pyqtSignal(dict)  # Signal quand données fusionnées
    
    def __init__(self, parent=None, collected_data=None, original_data=None):
        super().__init__(parent)

        self.setWindowFlags(
            self.windowFlags() |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        # Gérer les données multi-tables ou mono-table
        self.full_collected_data = collected_data or {}
        self.full_original_data = original_data or {}

        # S'assurer que c'est un dictionnaire pour le multi-table
        if isinstance(self.full_collected_data, list):
            self.full_collected_data = {'default': self.full_collected_data}
        if isinstance(self.full_original_data, list):
            self.full_original_data = {'default': self.full_original_data}

        # Table active
        self.current_table = next(iter(self.full_collected_data.keys())) if self.full_collected_data else 'default'
        self.current_record_index = -1
        self._refreshing_ui = False
        self.page_size = 200
        self.current_page = 0
        self.data_page = 0
        self.large_table_threshold = 500
        self._loaded_tabs = set()
        self.validation_errors = {}
        self.excluded_rows = {}
        self.included_error_rows = {}
        self.table_publish_state = {
            table_name: True
            for table_name in self.full_collected_data.keys()
        }

        self.collected_data = self.full_collected_data.get(self.current_table, [])
        self.original_data = self.full_original_data.get(self.current_table, [])

        self.validated_data = []
        self.setWindowTitle("Validation des données terrain")
        self.setGeometry(80, 80, 1100, 720)
        self.initUI()
    
    def initUI(self):
        """Initialise l'interface"""
        layout = QVBoxLayout()
        
        # --- Sélecteur de table (pour multi-table) ---
        if len(self.full_collected_data) > 1 or 'default' not in self.full_collected_data:
            table_selector_layout = QHBoxLayout()
            table_selector_layout.addWidget(QLabel("<b>Table à valider :</b>"))
            self.table_selector = QComboBox()
            self.table_selector.addItems(sorted(self.full_collected_data.keys()))
            self.table_selector.currentTextChanged.connect(self.switch_table)
            table_selector_layout.addWidget(self.table_selector)
            table_selector_layout.addStretch()
            layout.addLayout(table_selector_layout)

        # --- Titre et Description ---
        title = QLabel("Validation des données collectées")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        desc = QLabel("1. Vérifiez les lignes retenues  2. Traitez les problèmes  3. Validez pour publier.")
        desc.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(desc)

        self.status_strip = QLabel("")
        self.status_strip.setWordWrap(True)
        self.status_strip.setStyleSheet(
            "padding: 6px; border: 1px solid #c8d3df; background: #f3f7fb; font-weight: bold;"
        )
        layout.addWidget(self.status_strip)
        
        # --- Onglets ---
        self.tabs = QTabWidget()

        self.tabs.addTab(self.create_validation_tab(), "1. Validation")
        self.tabs.addTab(self.create_issues_tab(), "2. Problèmes")
        self.tabs.addTab(self.create_comparison_tab(), "3. Comparaison")
        self.tabs.addTab(self.create_data_tabs(), "4. Données")
        self.tabs.addTab(self.create_overview_tab(), "5. Résumé")
        self.tabs.currentChanged.connect(self.on_main_tab_changed)
        
        layout.addWidget(self.tabs)
        
        # --- Barre de progression ---
        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        
        # --- Boutons d'action ---
        button_layout = QHBoxLayout()
        
        self.btn_auto_merge = QPushButton("Valider lignes correctes")
        self.btn_auto_merge.clicked.connect(self.auto_merge)
        
        self.btn_manual_review = QPushButton("Traiter les problèmes")
        self.btn_manual_review.clicked.connect(self.manual_review)
        
        self.btn_export_report = QPushButton("Exporter rapport")
        self.btn_export_report.clicked.connect(self.export_report)
        
        button_layout.addWidget(self.btn_auto_merge)
        button_layout.addWidget(self.btn_manual_review)
        button_layout.addWidget(self.btn_export_report)
        button_layout.addStretch()
        
        self.btn_cancel = QPushButton("Annuler")
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_validate = QPushButton("Valider et fermer")
        self.btn_validate.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.btn_validate.setDefault(True)  # Permet d'utiliser 'Entrée'
        self.btn_validate.clicked.connect(self.confirm_accept)
        
        button_layout.addWidget(self.btn_cancel)
        button_layout.addWidget(self.btn_validate)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.table_diff.itemChanged.connect(self.on_diff_item_changed)
        self.populate_data()
        self.run_validation_rules(show_messages=False)

    def switch_table(self, table_name):
        """Change la table active et rafraîchit l'UI."""
        if not table_name or table_name == self.current_table:
            return

        self.current_table = table_name
        self.collected_data = self.full_collected_data.get(table_name, [])
        self.original_data = self.full_original_data.get(table_name, [])
        self.current_record_index = -1
        self.current_page = 0
        self.data_page = 0
        self._loaded_tabs = set()

        # Rafraîchir toutes les vues
        self.populate_data()
        self.tabs.setCurrentIndex(0)
    
    def create_overview_tab(self):
        """Onglet vue d'ensemble"""
        widget = QGroupBox("Résumé et Contrôle Qualité")
        layout = QFormLayout()
        
        # Règles de validation
        self.rules_edit = QTextEdit()
        self.rules_edit.setPlaceholderText("Saisir une expression QGIS par ligne (ex: diameter > 0)")
        self.rules_edit.setMaximumHeight(80)
        self.rules_edit.setToolTip("Une expression QGIS par ligne. Les lignes invalides seront marquées en orange.")
        layout.addRow("Règles métier :", self.rules_edit)

        self.btn_run_rules = QPushButton("🚀 Lancer vérification")
        self.btn_run_rules.clicked.connect(lambda: self.run_validation_rules())
        layout.addRow("", self.btn_run_rules)

        # Statistiques
        total_collected = len(self.collected_data)
        total_original = len(self.original_data)
        
        # Nouvelles entrées
        new_entries = total_collected - total_original
        
        self.total_collected_label = QLabel(str(total_collected))
        self.total_original_label = QLabel(str(total_original))
        self.new_entries_label = QLabel(f"<b style='color:blue'>{new_entries}</b>")
        self.modified_label = QLabel(f"<b style='color:orange'>À analyser</b>")
        self.tables_label = QLabel("")
        self.ok_rows_label = QLabel("")
        self.blocking_errors_label = QLabel("")
        self.warning_rows_label = QLabel("")
        self.large_table_label = QLabel("")
        self.large_table_label.setStyleSheet("color: #cc6600; font-weight: bold;")
        self.blocking_errors_label.setStyleSheet("color: #b00020; font-weight: bold;")
        self.ok_rows_label.setStyleSheet("color: #1b5e20; font-weight: bold;")

        layout.addRow("Tables:", self.tables_label)
        layout.addRow("Total collecté:", self.total_collected_label)
        layout.addRow("Total original:", self.total_original_label)
        layout.addRow("Nouvelles entrées:", self.new_entries_label)
        layout.addRow("Modifiées/Supprimées:", self.modified_label)
        layout.addRow("Lignes correctes:", self.ok_rows_label)
        layout.addRow("Erreurs bloquantes:", self.blocking_errors_label)
        layout.addRow("À vérifier:", self.warning_rows_label)
        layout.addRow("Affichage:", self.large_table_label)
        
        # Statut validation
        self.validation_status_label = QLabel("<b style='color:red'>En attente de validation</b>")
        layout.addRow("Statut:", self.validation_status_label)
        
        # Actions recommandées
        self.recommendation = QTextEdit()
        self.recommendation.setReadOnly(True)
        self.recommendation.setMinimumHeight(150)
        layout.addRow("Recommandations:", self.recommendation)
        
        widget.setLayout(layout)
        return widget
    
    def create_data_tabs(self):
        """Onglet contenant les données originales et collectées"""
        layout = QVBoxLayout()
        data_tabs = QTabWidget()
        self.data_subtabs = data_tabs

        # Sous-onglet: Original (Base)
        self.table_before = QTableWidget()
        self.table_before.setAlternatingRowColors(True)
        self.table_before.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_before.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table_before.setColumnCount(0)
        data_tabs.addTab(self.table_before, "Données Originales (Base)")

        # Sous-onglet: Collecté (Terrain)
        self.table_collected = QTableWidget()
        self.table_collected.setAlternatingRowColors(True)
        self.table_collected.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_collected.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table_collected.setColumnCount(0)
        data_tabs.addTab(self.table_collected, "Données Collectées (Terrain)")

        layout.addWidget(data_tabs)

        pager_layout = QHBoxLayout()
        self.data_prev_button = QPushButton("Précédent")
        self.data_prev_button.clicked.connect(self.previous_data_page)
        self.data_next_button = QPushButton("Suivant")
        self.data_next_button.clicked.connect(self.next_data_page)
        self.data_page_label = QLabel("")
        pager_layout.addWidget(self.data_prev_button)
        pager_layout.addWidget(self.data_next_button)
        pager_layout.addWidget(self.data_page_label)
        pager_layout.addStretch()
        layout.addLayout(pager_layout)
        data_tabs.currentChanged.connect(lambda _: self.populate_data_tables_page())

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def create_issues_tab(self):
        """Vue simplifiée des anomalies à traiter."""
        layout = QVBoxLayout()
        layout.addWidget(QLabel("<b>Lignes avec problème</b>"))

        self.issues_table = QTableWidget()
        self.issues_table.setAlternatingRowColors(True)
        self.issues_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.issues_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.issues_table.setColumnCount(6)
        self.issues_table.setHorizontalHeaderLabels(["Publier", "Table", "Ligne", "ID", "Type", "Problème"])
        self.issues_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.issues_table.itemChanged.connect(self.on_issue_item_changed)
        layout.addWidget(self.issues_table)

        self.issues_hint = QLabel("")
        self.issues_hint.setStyleSheet("color: gray;")
        layout.addWidget(self.issues_hint)

        widget = QGroupBox("Exceptions à traiter")
        widget.setLayout(layout)
        return widget
    
    def create_comparison_tab(self):
        """Onglet comparaison et résolution de conflits"""
        layout = QVBoxLayout()
        
        # Contrôles de comparaison
        ctrl_layout = QHBoxLayout()
        
        l_sel = QLabel("Enregistrement à comparer :")
        l_sel.setStyleSheet("font-weight: bold;")
        ctrl_layout.addWidget(l_sel)

        self.record_spin = QSpinBox()
        self.record_spin.setMinimum(1)
        self.record_spin.setMaximum(max(1, len(self.collected_data)))
        self.record_spin.valueChanged.connect(lambda value: self.show_comparison(value - 1))
        ctrl_layout.addWidget(self.record_spin)

        self.combo_records = QComboBox()
        self.combo_records.setMinimumWidth(280)
        self.combo_records.currentIndexChanged.connect(self.show_comparison_from_combo)
        ctrl_layout.addWidget(self.combo_records)
        
        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout)
        
        # Table de résolution unique
        self.table_diff = QTableWidget()
        self.table_diff.setAlternatingRowColors(True)
        self.table_diff.setColumnCount(4)
        self.table_diff.setHorizontalHeaderLabels(["Champ", "Base", "Terrain", "Valeur finale"])
        self.table_diff.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table_diff)

        widget = QGroupBox("Résolution des Conflits")
        widget.setLayout(layout)
        return widget
    
    def create_validation_tab(self):
        """Onglet validation ligne par ligne"""
        layout = QVBoxLayout()
        layout.addWidget(QLabel("<b>Tables à publier</b>"))

        self.table_status = QTableWidget()
        self.table_status.setAlternatingRowColors(True)
        self.table_status.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_status.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_status.setColumnCount(7)
        self.table_status.setHorizontalHeaderLabels([
            "Publier", "Table", "Statut", "Retenues", "Problèmes", "Exclues", "Total"
        ])
        self.table_status.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_status.itemChanged.connect(self.on_table_publish_item_changed)
        layout.addWidget(self.table_status)

        table_action_layout = QHBoxLayout()
        self.btn_publish_all_tables = QPushButton("Publier toutes")
        self.btn_publish_all_tables.clicked.connect(lambda: self.set_all_tables_publish_state(True))
        self.btn_unpublish_current_table = QPushButton("Retirer table active")
        self.btn_unpublish_current_table.clicked.connect(self.unpublish_current_table)
        table_action_layout.addWidget(self.btn_publish_all_tables)
        table_action_layout.addWidget(self.btn_unpublish_current_table)
        table_action_layout.addStretch()
        layout.addLayout(table_action_layout)

        layout.addWidget(QLabel("<b>Lignes retenues pour la table active</b>"))

        batch_layout = QHBoxLayout()
        self.btn_exclude_selected = QPushButton("Exclure sélection")
        self.btn_exclude_selected.clicked.connect(self.exclude_selected_validation_rows)
        self.btn_include_selected = QPushButton("Réinclure sélection")
        self.btn_include_selected.clicked.connect(self.include_selected_validation_rows)
        batch_layout.addWidget(self.btn_exclude_selected)
        batch_layout.addWidget(self.btn_include_selected)
        batch_layout.addStretch()
        layout.addLayout(batch_layout)

        self.table_validation = self._setup_validation_table()
        layout.addWidget(self.table_validation)

        pager_layout = QHBoxLayout()
        self.validation_prev_button = QPushButton("Précédent")
        self.validation_prev_button.clicked.connect(self.previous_validation_page)
        self.validation_next_button = QPushButton("Suivant")
        self.validation_next_button.clicked.connect(self.next_validation_page)
        self.validation_page_label = QLabel("")
        pager_layout.addWidget(self.validation_prev_button)
        pager_layout.addWidget(self.validation_next_button)
        pager_layout.addWidget(self.validation_page_label)
        pager_layout.addStretch()
        layout.addLayout(pager_layout)
        
        layout.addWidget(QLabel("<b>Détails de la ligne sélectionnée:</b>"))
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setMaximumHeight(150)
        layout.addWidget(self.detail_text)

        widget = QGroupBox("Validation Détaillée")
        widget.setLayout(layout)
        return widget

    def _setup_validation_table(self):
        """Configure et remplit le tableau de validation."""
        table = QTableWidget()
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(["ID", "Statut", "Changements", "Type", "Action", "Commentaire"])
        table.itemSelectionChanged.connect(self.on_validation_row_selected)

        table.resizeColumnsToContents()
        return table

    def _fill_validation_row(self, table, row, item, data_index=None):
        """Remplit une ligne du tableau de validation."""
        data_index = row if data_index is None else data_index
        item_id = item.get('id', row)
        table.setItem(row, 0, QTableWidgetItem(str(item_id)))

        is_excluded = data_index in self.excluded_rows.get(self.current_table, set())
        table_published = self.table_publish_state.get(self.current_table, True)
        status_label = 'Table retirée' if not table_published else 'Exclu' if is_excluded else '🆕 Nouveau' if self.original_for_item(item, data_index) is None else '✓ Valide'
        table.setItem(row, 1, QTableWidgetItem(status_label))

        changes = self.detect_changes(item, data_index)
        changes_item = QTableWidgetItem(changes)
        if "🆕" in changes: changes_item.setBackground(QColor(200, 255, 200))
        elif "❌" in changes: changes_item.setBackground(QColor(255, 100, 100))
        elif "✏️" in changes or "⚠️" in changes: changes_item.setBackground(QColor(255, 220, 100))
        table.setItem(row, 2, changes_item)

        type_label = "NOUVEAU" if data_index >= len(self.original_data) else "MODIFIÉ" if self.has_changes(item, data_index) else "INCHANGÉ"
        table.setItem(row, 3, QTableWidgetItem(type_label))

        table.setItem(row, 4, QTableWidgetItem("Fusionner"))
        table.setItem(row, 5, QTableWidgetItem(""))

        if is_excluded or not table_published:
            for col in range(table.columnCount()):
                tbl_item = table.item(row, col)
                if tbl_item:
                    tbl_item.setBackground(QColor(210, 210, 210))
                    tbl_item.setToolTip("Table retirée de la publication." if not table_published else "Ligne exclue de la publication.")

        error_msgs = self.validation_errors.get(self.current_table, {}).get(data_index, [])
        if error_msgs:
            for col in range(table.columnCount()):
                tbl_item = table.item(row, col)
                if tbl_item:
                    tbl_item.setBackground(QColor(255, 165, 0, 150))
                    tbl_item.setToolTip(f"Anomalies détectées :\n- " + "\n- ".join(error_msgs))
            comment_item = table.item(row, 5)
            if comment_item:
                comment_item.setText(f"ERREUR METIER: {', '.join(error_msgs)}")
    
    def has_changes(self, item, index):
        """Vérifie si l'item a des changements"""
        original = self.original_for_item(item, index)
        if original is None:
            return True

        for key in item.keys():
            if key not in original or original[key] != item[key]:
                return True

        return False

    def row_key_field(self, row, table_name=None):
        if not isinstance(row, dict):
            return None
        table_hint = str(table_name or self.current_table or '').strip().lower()
        candidates = []
        if table_hint:
            candidates.append(f"uuid_{table_hint}")
            if table_hint.endswith('s'):
                candidates.append(f"uuid_{table_hint[:-1]}")
        candidates.extend([
            'uuid_arbre_gps', 'uuid_bosquet_gps', 'uuid_pg_gps', 'uuid_pg',
            'uuid_membre', 'uuid', 'id'
        ])
        lower_keys = {str(key).lower(): key for key in row.keys()}
        for candidate in candidates:
            key = lower_keys.get(candidate)
            if key and row.get(key) not in (None, ''):
                return key
        for key in row.keys():
            if str(key).lower().startswith('uuid') and row.get(key) not in (None, ''):
                return key
        return None

    def normalized_row_key(self, row, table_name=None):
        key_field = self.row_key_field(row, table_name=table_name)
        if not key_field:
            return None
        value = row.get(key_field)
        normalized = _normalize_uuid(value)
        return key_field.lower(), normalized or str(value)

    def original_for_item(self, item, fallback_index=None, table_name=None, original_data=None):
        original_rows = self.original_data if original_data is None else original_data
        item_key = self.normalized_row_key(item, table_name=table_name)
        if item_key:
            for original in original_rows:
                if self.normalized_row_key(original, table_name=table_name) == item_key:
                    return original
        if fallback_index is not None and 0 <= fallback_index < len(original_rows):
            return original_rows[fallback_index]
        return None

    def on_validation_row_selected(self):
        """Affiche les détails de la ligne sélectionnée"""
        if self._refreshing_ui:
            return

        selected_rows = self.table_validation.selectedIndexes()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        data_index = self.current_page * self.page_size + row
        if 0 <= data_index < len(self.collected_data):
            self.show_row_details(data_index)

    def selected_validation_data_indices(self):
        rows = sorted({index.row() for index in self.table_validation.selectedIndexes()})
        start = self.current_page * self.page_size
        return [
            start + row
            for row in rows
            if 0 <= start + row < len(self.collected_data)
        ]

    def exclude_selected_validation_rows(self):
        indices = self.selected_validation_data_indices()
        if not indices:
            return
        excluded = self.excluded_rows.setdefault(self.current_table, set())
        excluded.update(indices)
        self.populate_validation_page()
        self.populate_table_status()
        self.update_overview_stats()

    def include_selected_validation_rows(self):
        indices = self.selected_validation_data_indices()
        if not indices:
            return
        excluded = self.excluded_rows.setdefault(self.current_table, set())
        for index in indices:
            excluded.discard(index)
        self.populate_validation_page()
        self.populate_table_status()
        self.update_overview_stats()

    def show_row_details(self, row):
        """Affiche les détails complets d'une ligne"""
        collected_item = self.collected_data[row]
        original_item = self.original_for_item(collected_item, row) or {}

        # Construire le texte détaillé
        details = []
        details.append(f"{'='*60}")
        details.append(f"ENREGISTREMENT #{row + 1} - ID: {collected_item.get('id', 'N/A')}")
        details.append(f"{'='*60}")

        # Déterminer le type
        if not original_item:
            details.append("TYPE: 🆕 NOUVEL ENREGISTREMENT")
        else:
            details.append(f"TYPE: {'✏️ MODIFIÉ' if self.has_changes(collected_item, row) else '✓ INCHANGÉ'}")

        details.append("")
        details.append("CHANGEMENTS DÉTECTÉS:")
        details.append("-" * 60)

        # Récupérer tous les champs
        all_keys = set(list(collected_item.keys()) + list(original_item.keys()))

        change_count = 0
        for key in sorted(all_keys):
            original_value = original_item.get(key)
            collected_value = collected_item.get(key)

            if original_value != collected_value:
                change_count += 1
                details.append(f"\n🔹 CHAMP: {key}")
                details.append(f"   AVANT:  {_compact_value_for_display(original_value, key)}")
                details.append(f"   APRÈS:  {_compact_value_for_display(collected_value, key)}")

        if change_count == 0:
            details.append("\n✓ Aucun changement détecté")
        else:
            details.append(f"\n\nTOTAL: {change_count} champ(s) modifié(s)")

        details.append(f"{'='*60}")

        self.detail_text.setText("\n".join(details))

    def populate_table_from_data(self, table, data, page=0):
        """Remplit une table à partir des données"""
        table.clearContents()
        if not data:
            table.setRowCount(0)
            table.setColumnCount(0)
            return
        
        first_item = data[0]
        columns = list(first_item.keys())
        start = max(0, page * self.page_size)
        end = min(start + self.page_size, len(data))
        page_data = data[start:end]
        
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.setRowCount(len(page_data))
        
        for row, item in enumerate(page_data):
            for col, key in enumerate(columns):
                value = item.get(key, '')
                display_value = _compact_value_for_display(value, key, max_length=80)
                table_item = QTableWidgetItem(display_value)
                table_item.setData(Qt.UserRole, _pack_full_value(value))
                table_item.setToolTip(_compact_value_for_tooltip(value, key))
                table.setItem(row, col, table_item)
        
        table.resizeColumnsToContents()
    
    def populate_data(self):
        """Remplit les tables avec les données de la table active."""
        self._refreshing_ui = True
        blockers = [
            QSignalBlocker(self.table_collected),
            QSignalBlocker(self.table_before),
            QSignalBlocker(self.table_validation),
            QSignalBlocker(self.table_status),
            QSignalBlocker(self.table_diff),
            QSignalBlocker(self.issues_table),
            QSignalBlocker(self.combo_records),
            QSignalBlocker(self.record_spin),
        ]

        try:
            # Vider les onglets sans déclencher les slots connectés aux tables.
            self.table_collected.clearContents()
            self.table_collected.setRowCount(0)
            self.table_before.clearContents()
            self.table_before.setRowCount(0)
            self.table_diff.clearContents()
            self.table_diff.setRowCount(0)
            self.combo_records.clear()
            self.detail_text.clear()
            self.table_validation.clearContents()
            self.table_validation.setRowCount(0)
            self.table_status.clearContents()
            self.table_status.setRowCount(0)
            self.issues_table.clearContents()
            self.issues_table.setRowCount(0)
            self.record_spin.setMaximum(max(1, len(self.collected_data)))
            self.record_spin.setValue(1)
        finally:
            del blockers
            self._refreshing_ui = False

        self.update_overview_stats()
        self.populate_table_status()
        self.populate_issues_table()
        self.update_lazy_tab()
        # Générer recommandations
        self.generate_recommendations()

    def _table_counts(self, table_name):
        collected = self.full_collected_data.get(table_name, [])
        original = self.full_original_data.get(table_name, [])
        errors = self.validation_errors.get(table_name, {})
        excluded = self.excluded_rows.get(table_name, set())
        included_errors = self.included_error_rows.get(table_name, set())
        new_count = 0
        modified_count = 0
        for idx, item in enumerate(collected):
            original_item = self.original_for_item(
                item,
                fallback_index=idx,
                table_name=table_name,
                original_data=original
            )
            if original_item is None:
                new_count += 1
            elif item != original_item:
                modified_count += 1
        error_count = max(0, len(errors) - len(included_errors))
        excluded_count = len(excluded)
        published = self.table_publish_state.get(table_name, True)
        ok_count = max(0, len(collected) - error_count - excluded_count) if published else 0
        return {
            'collected': len(collected),
            'original': len(original),
            'new': new_count,
            'modified': modified_count,
            'errors': error_count,
            'excluded': excluded_count,
            'published': 1 if published else 0,
            'ok': ok_count,
        }

    def _global_counts(self):
        totals = {
            'tables': len(self.full_collected_data),
            'collected': 0,
            'original': 0,
            'new': 0,
            'modified': 0,
            'errors': 0,
            'excluded': 0,
            'published': 0,
            'ok': 0,
        }
        for table_name in self.full_collected_data:
            counts = self._table_counts(table_name)
            for key in counts:
                totals[key] += counts[key]
        return totals

    def _build_validated_payload(self, exclude_errors=True):
        payload = {}
        for table_name, rows in self.full_collected_data.items():
            if not self.table_publish_state.get(table_name, True):
                continue
            error_rows = set(self.validation_errors.get(table_name, {}).keys()) if exclude_errors else set()
            included_errors = self.included_error_rows.get(table_name, set())
            excluded = self.excluded_rows.get(table_name, set())
            payload[table_name] = [
                row
                for idx, row in enumerate(rows)
                if (idx not in error_rows or idx in included_errors) and idx not in excluded
            ]

        if len(payload) == 1 and 'default' in payload:
            return payload['default']
        return payload

    def populate_table_status(self):
        blocker = QSignalBlocker(self.table_status)
        try:
            table_names = sorted(self.full_collected_data.keys())
            self.table_status.clearContents()
            self.table_status.setRowCount(len(table_names))
            for row, table_name in enumerate(table_names):
                counts = self._table_counts(table_name)
                publish_item = QTableWidgetItem("")
                publish_item.setFlags(publish_item.flags() | Qt.ItemIsUserCheckable)
                publish_item.setCheckState(Qt.Checked if self.table_publish_state.get(table_name, True) else Qt.Unchecked)
                publish_item.setData(Qt.UserRole, table_name)
                self.table_status.setItem(row, 0, publish_item)

                status = "Retirée" if not self.table_publish_state.get(table_name, True) else (
                    "Avec problèmes" if counts['errors'] else "Prête"
                )
                values = [
                    table_name,
                    status,
                    str(counts['ok'] if self.table_publish_state.get(table_name, True) else 0),
                    str(counts['errors']),
                    str(counts['excluded']),
                    str(counts['collected']),
                ]
                for col, value in enumerate(values, start=1):
                    item = QTableWidgetItem(value)
                    if status == "Retirée":
                        item.setBackground(QColor(210, 210, 210))
                    elif status == "Avec problèmes":
                        item.setBackground(QColor(255, 220, 180))
                    self.table_status.setItem(row, col, item)
            self.table_status.resizeColumnsToContents()
        finally:
            del blocker

    def on_table_publish_item_changed(self, item):
        if self._refreshing_ui or item is None or item.column() != 0:
            return
        table_name = item.data(Qt.UserRole)
        if not table_name:
            return
        self.table_publish_state[table_name] = item.checkState() == Qt.Checked
        self.populate_table_status()
        self.update_overview_stats()

    def set_all_tables_publish_state(self, publish):
        for table_name in self.full_collected_data:
            self.table_publish_state[table_name] = publish
        self.populate_table_status()
        self.update_overview_stats()

    def unpublish_current_table(self):
        self.table_publish_state[self.current_table] = False
        self.populate_table_status()
        self.update_overview_stats()

    def update_overview_stats(self):
        """Met à jour le résumé sans reconstruire les widgets."""
        total_collected = len(self.collected_data)
        total_original = len(self.original_data)
        new_entries = total_collected - total_original
        global_counts = self._global_counts()

        self.tables_label.setText(str(global_counts['tables']))
        self.total_collected_label.setText(str(total_collected))
        self.total_original_label.setText(str(total_original))
        self.new_entries_label.setText(f"<b style='color:blue'>{new_entries}</b>")
        self.modified_label.setText(f"<b style='color:orange'>{global_counts['modified']}</b>")
        self.ok_rows_label.setText(str(global_counts['ok']))
        self.blocking_errors_label.setText(str(global_counts['errors']))
        self.warning_rows_label.setText(str(global_counts['modified'] + global_counts['new']))
        if global_counts['errors']:
            self.validation_status_label.setText("<b style='color:#b00020'>Anomalies à traiter</b>")
        else:
            self.validation_status_label.setText("<b style='color:#1b5e20'>Prêt pour validation</b>")

        status_color = "#b00020" if global_counts['errors'] else "#1b5e20"
        status_text = "Anomalies à traiter" if global_counts['errors'] else "Prêt pour validation"
        self.status_strip.setText(
            "<span style='color:{color}'>{status}</span> | "
            "Table active: {table} | Tables: {tables} | Retenues: {ok} | "
            "Problèmes: {errors} | Exclues: {excluded} | Tables publiées: {published}".format(
                color=status_color,
                status=status_text,
                table=self.current_table,
                tables=global_counts['tables'],
                ok=global_counts['ok'],
                errors=global_counts['errors'],
                excluded=global_counts['excluded'],
                published=sum(1 for value in self.table_publish_state.values() if value),
            )
        )

        if total_collected > self.large_table_threshold:
            self.large_table_label.setText(
                f"Table volumineuse : affichage paginé à {self.page_size} lignes."
            )
        else:
            self.large_table_label.setText(f"Affichage direct, {self.page_size} lignes maximum par page.")

    def populate_issues_table(self):
        """Remplit la vue globale des lignes problématiques."""
        blocker = QSignalBlocker(self.issues_table)
        try:
            rows = []
            for table_name in sorted(self.full_collected_data.keys()):
                table_errors = self.validation_errors.get(table_name, {})
                for data_index, messages in sorted(table_errors.items()):
                    item = self.full_collected_data.get(table_name, [])[data_index]
                    rows.append((table_name, data_index, item, messages))

            self.issues_table.clearContents()
            self.issues_table.setRowCount(len(rows))
            for row, (table_name, data_index, item, messages) in enumerate(rows):
                publish_item = QTableWidgetItem("")
                publish_item.setFlags(publish_item.flags() | Qt.ItemIsUserCheckable)
                is_included = data_index in self.included_error_rows.get(table_name, set())
                publish_item.setCheckState(Qt.Checked if is_included else Qt.Unchecked)
                publish_item.setData(Qt.UserRole, (table_name, data_index))
                self.issues_table.setItem(row, 0, publish_item)
                self.issues_table.setItem(row, 1, QTableWidgetItem(str(table_name)))
                self.issues_table.setItem(row, 2, QTableWidgetItem(str(data_index + 1)))
                self.issues_table.setItem(row, 3, QTableWidgetItem(str(item.get('id', 'N/A'))))
                self.issues_table.setItem(row, 4, QTableWidgetItem("Erreur métier"))
                msg = "; ".join(messages)
                msg_item = QTableWidgetItem(Utils.compact_dialog_message(msg, max_length=220))
                msg_item.setToolTip(Utils.compact_dialog_message(msg, max_length=1000))
                self.issues_table.setItem(row, 5, msg_item)
            self.issues_table.resizeColumnsToContents()
            if rows:
                self.issues_hint.setText(
                    "Les lignes en anomalie sont bloquées par défaut. Cochez Publier seulement après correction ou décision métier."
                )
            else:
                self.issues_hint.setText("Aucune anomalie détectée. Les lignes correctes peuvent être validées.")
        finally:
            del blocker

    def on_issue_item_changed(self, item):
        if self._refreshing_ui or item is None or item.column() != 0:
            return
        marker = item.data(Qt.UserRole)
        if not marker:
            return
        table_name, data_index = marker
        included = self.included_error_rows.setdefault(table_name, set())
        if item.checkState() == Qt.Checked:
            included.add(data_index)
        else:
            included.discard(data_index)
        self.populate_table_status()
        self.update_overview_stats()

    def on_main_tab_changed(self, index):
        """Charge les onglets lourds uniquement quand ils deviennent visibles."""
        self.update_lazy_tab(index)

    def update_lazy_tab(self, index=None):
        """Charge la vue active selon l'onglet courant."""
        if index is None:
            index = self.tabs.currentIndex()

        if index == 0:
            self.populate_validation_page()
            self._loaded_tabs.add(index)
        elif index == 1:
            self.populate_issues_table()
            self._loaded_tabs.add(index)
        elif index == 2:
            self.populate_comparison_controls()
            if self.collected_data:
                self.show_comparison(self.record_spin.value() - 1)
            self._loaded_tabs.add(index)
        elif index == 3:
            self.populate_data_tables_page()
            self._loaded_tabs.add(index)
        elif index == 4:
            self.update_overview_stats()
            self.generate_recommendations()
            self._loaded_tabs.add(index)

    def _page_bounds(self, data, page):
        total = len(data)
        start = min(max(0, page * self.page_size), max(0, total - 1))
        if total:
            start = (start // self.page_size) * self.page_size
        end = min(start + self.page_size, total)
        return start, end

    def _max_page(self, data):
        if not data:
            return 0
        return (len(data) - 1) // self.page_size

    def populate_data_tables_page(self):
        """Remplit l'onglet Données avec une page seulement."""
        visible_data = self.original_data if self.data_subtabs.currentIndex() == 0 else self.collected_data
        self.data_page = min(self.data_page, self._max_page(visible_data))
        table = self.table_before if self.data_subtabs.currentIndex() == 0 else self.table_collected

        blocker = QSignalBlocker(table)
        try:
            self.populate_table_from_data(table, visible_data, self.data_page)
        finally:
            del blocker

        start, end = self._page_bounds(visible_data, self.data_page)
        total = len(visible_data)
        self.data_page_label.setText(f"Lignes {start + 1 if total else 0}-{end} sur {total}")
        self.data_prev_button.setEnabled(self.data_page > 0)
        self.data_next_button.setEnabled(self.data_page < self._max_page(visible_data))

    def previous_data_page(self):
        if self.data_page > 0:
            self.data_page -= 1
            self.populate_data_tables_page()

    def next_data_page(self):
        visible_data = self.original_data if self.data_subtabs.currentIndex() == 0 else self.collected_data
        if self.data_page < self._max_page(visible_data):
            self.data_page += 1
            self.populate_data_tables_page()

    def populate_validation_page(self):
        """Remplit la validation détaillée avec une page seulement."""
        self.current_page = min(self.current_page, self._max_page(self.collected_data))
        start, end = self._page_bounds(self.collected_data, self.current_page)
        page_data = self.collected_data[start:end]

        blocker = QSignalBlocker(self.table_validation)
        try:
            self.table_validation.clearContents()
            self.table_validation.setRowCount(len(page_data))
            for row, item in enumerate(page_data):
                self._fill_validation_row(self.table_validation, row, item, start + row)
            self.table_validation.resizeColumnsToContents()
        finally:
            del blocker

        total = len(self.collected_data)
        self.validation_page_label.setText(f"Lignes {start + 1 if total else 0}-{end} sur {total}")
        self.validation_prev_button.setEnabled(self.current_page > 0)
        self.validation_next_button.setEnabled(self.current_page < self._max_page(self.collected_data))

    def previous_validation_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.populate_validation_page()

    def next_validation_page(self):
        if self.current_page < self._max_page(self.collected_data):
            self.current_page += 1
            self.populate_validation_page()

    def populate_comparison_controls(self):
        """Limite la liste déroulante de comparaison à la page courante."""
        blocker = QSignalBlocker(self.combo_records)
        try:
            self.combo_records.clear()
            start, end = self._page_bounds(self.collected_data, self.current_page)
            for i, item in enumerate(self.collected_data[start:end], start):
                key = self.normalized_row_key(item)
                key_text = "{}={}".format(key[0], key[1]) if key else f"ID: {item.get('id', 'N/A')}"
                label = f"Enregistrement {i + 1} ({key_text})"
                self.combo_records.addItem(label, i)
        finally:
            del blocker

    def show_comparison_from_combo(self, combo_index):
        """Affiche la comparaison depuis la liste paginée."""
        if self._refreshing_ui or combo_index < 0:
            return
        data_index = self.combo_records.itemData(combo_index)
        if data_index is not None:
            self.record_spin.blockSignals(True)
            self.record_spin.setValue(data_index + 1)
            self.record_spin.blockSignals(False)
            self.show_comparison(data_index)
    
    def generate_recommendations(self):
        """Génère des recommandations basées sur les données"""
        recs = []
        counts = self._global_counts()

        recs.append(f"Tables prêtes: {counts['tables']}")
        recs.append(f"Lignes correctes validables: {counts['ok']}")
        if counts['new']:
            recs.append(f"{counts['new']} nouveaux enregistrements détectés")
        if counts['modified']:
            recs.append(f"{counts['modified']} lignes à vérifier")
        if counts['errors']:
            recs.append(f"{counts['errors']} anomalies à traiter avant publication")
        if not counts['errors']:
            recs.append("Aucune anomalie métier détectée")
        
        self.recommendation.setText("\n".join(recs))

    def show_info(self, title, message):
        """Affiche une information."""
        QMessageBox.information(self, title, Utils.compact_dialog_message(message))

    def show_warning(self, title, message):
        """Affiche un avertissement."""
        QMessageBox.warning(self, title, Utils.compact_dialog_message(message))

    def show_error(self, title, message):
        """Affiche une erreur."""
        QMessageBox.critical(self, title, Utils.compact_dialog_message(message))

    def prune_validation_decisions(self):
        for table_name, rows in self.full_collected_data.items():
            valid_indices = set(range(len(rows)))
            self.excluded_rows[table_name] = self.excluded_rows.get(table_name, set()) & valid_indices
            error_indices = set(self.validation_errors.get(table_name, {}).keys())
            self.included_error_rows[table_name] = self.included_error_rows.get(table_name, set()) & error_indices

    def run_validation_rules(self, show_messages=True):
        """Exécute les règles métier automatisées sur les données collectées."""
        invalid_count = 0
        if not self.full_collected_data:
            return

        context = QgsExpressionContext()
        context.appendScope(QgsExpressionContextUtils.globalScope())

        self.validation_errors = {}
        for table_name, table_data in self.full_collected_data.items():
            if not table_data:
                self.validation_errors[table_name] = {}
                continue

            all_keys = set()
            for item in table_data:
                all_keys.update(item.keys())

            fields = QgsFields()
            sorted_keys = sorted(all_keys)
            for key in sorted_keys:
                fields.append(QgsField(key, QVariant.String))

            feat = QgsFeature(fields)
            table_errors = {}
            for data_index, item_data in enumerate(table_data):
                feat.setAttributes([item_data.get(key) for key in sorted_keys])
                errors = BusinessRulesEngine.validate_feature(table_name, feat, context=context)
                if errors:
                    invalid_count += 1
                    table_errors[data_index] = [e['message'] for e in errors]
            self.validation_errors[table_name] = table_errors

        self.prune_validation_decisions()

        if invalid_count > 0:
            if show_messages:
                msg = f"{invalid_count} enregistrements présentent des anomalies métier."
                self.show_warning("Contrôle Qualité Automatisé", msg)
            
            # Mettre à jour les recommandations dans l'onglet 0
            self.generate_recommendations()
            
            self.populate_validation_page()
            self.populate_issues_table()
            self.populate_table_status()
            self.update_overview_stats()
            if show_messages:
                self.tabs.setCurrentIndex(1)
        else:
            self.populate_validation_page()
            self.populate_issues_table()
            self.populate_table_status()
            self.update_overview_stats()
            self.generate_recommendations()
            if show_messages:
                self.show_info("Contrôle Qualité Automatisé",
                                        "Félicitations ! Aucune anomalie métier détectée.")
    
    def show_comparison(self, index):
        """Affiche la comparaison avec sélection interactive de la valeur finale"""
        if self._refreshing_ui:
            return

        if index < 0 or index >= len(self.collected_data):
            return

        self.current_record_index = index
        self.table_diff.blockSignals(True)
        self.table_diff.setRowCount(0)

        collected_item = self.collected_data[index]
        original_item = self.original_for_item(collected_item, index) or {}

        all_keys = sorted(list(set(list(collected_item.keys()) + list(original_item.keys()))))
        self.table_diff.setRowCount(len(all_keys))

        for row, key in enumerate(all_keys):
            orig_val = original_item.get(key, "[absent]")
            coll_val = collected_item.get(key, "[absent]")

            self.table_diff.setItem(row, 0, QTableWidgetItem(key))

            # Case à cocher pour BASE
            base_item = QTableWidgetItem(_compact_value_for_display(orig_val, key))
            base_item.setData(Qt.UserRole, _pack_full_value(orig_val))
            base_item.setToolTip(_compact_value_for_tooltip(orig_val, key))
            base_item.setFlags(base_item.flags() | Qt.ItemIsUserCheckable)
            base_item.setCheckState(Qt.Unchecked)
            self.table_diff.setItem(row, 1, base_item)

            # Case à cocher pour TERRAIN (par défaut)
            coll_item = QTableWidgetItem(_compact_value_for_display(coll_val, key))
            coll_item.setData(Qt.UserRole, _pack_full_value(coll_val))
            coll_item.setToolTip(_compact_value_for_tooltip(coll_val, key))
            coll_item.setFlags(coll_item.flags() | Qt.ItemIsUserCheckable)
            coll_item.setCheckState(Qt.Checked)
            self.table_diff.setItem(row, 2, coll_item)

            # Valeur finale (Éditable)
            final_item = QTableWidgetItem(_compact_value_for_display(coll_val, key))
            final_item.setData(Qt.UserRole, _pack_full_value(coll_val))
            final_item.setToolTip(_compact_value_for_tooltip(coll_val, key))
            final_item.setFlags(final_item.flags() | Qt.ItemIsEditable)
            if orig_val != coll_val:
                final_item.setBackground(QColor(255, 255, 200)) # Highlight
            self.table_diff.setItem(row, 3, final_item)

        self.table_diff.blockSignals(False)

    def on_diff_item_changed(self, item):
        """Met à jour les données quand la valeur finale ou une checkbox est modifiée"""
        if self._refreshing_ui or self.current_record_index == -1 or item is None:
            return

        row = item.row()
        col = item.column()
        field_item = self.table_diff.item(row, 0)
        if field_item is None:
            return
        field_name = field_item.text()

        # Logique des cases à cocher (Colonnes 1: Base, 2: Terrain)
        if col in [1, 2]:
            if item.checkState() == Qt.Checked:
                self.table_diff.blockSignals(True)
                # Décocher l'autre colonne
                other_col = 2 if col == 1 else 1
                other_item = self.table_diff.item(row, other_col)
                final_item = self.table_diff.item(row, 3)
                if other_item is None or final_item is None:
                    self.table_diff.blockSignals(False)
                    return
                other_item.setCheckState(Qt.Unchecked)

                # Mettre à jour la valeur finale
                chosen_val = _unpack_full_value(item.data(Qt.UserRole), item.text())
                final_item.setData(Qt.UserRole, _pack_full_value(chosen_val))
                final_item.setText(_compact_value_for_display(chosen_val, field_name))
                final_item.setToolTip(_compact_value_for_tooltip(chosen_val, field_name))
                # Synchroniser avec les données collectées
                self.collected_data[self.current_record_index][field_name] = chosen_val
                print(f"DEBUG: Choix pour {field_name} -> {chosen_val}")
                self.table_diff.blockSignals(False)
            return

        # Mise à jour manuelle de la valeur finale (Colonne 3)
        if col == 3:
            new_value = item.text()
            item.setData(Qt.UserRole, _pack_full_value(new_value))
            print(f"DEBUG: Mise à jour {field_name} = {new_value}")
            self.collected_data[self.current_record_index][field_name] = new_value

    def detect_changes(self, item, index):
        """Détecte les changements par rapport à l'original"""
        original = self.original_for_item(item, index)
        if original is None:
            return "🆕 NOUVEAU"

        changes = []
        
        # Comparer tous les champs
        from .utils import Utils
        all_keys = set(list(item.keys()) + list(original.keys()))
        for key in sorted(all_keys):
            original_value = original.get(key)
            item_value = item.get(key)

            # Normaliser les UUID pour la comparaison
            if isinstance(original_value, str) and ('uuid' in key.lower() or key.lower() == 'id'):
                original_value = Utils.normalize_uuid(original_value)
            if isinstance(item_value, str) and ('uuid' in key.lower() or key.lower() == 'id'):
                item_value = Utils.normalize_uuid(item_value)

            if key not in original:
                changes.append(f"🆕 {key}")
            elif key not in item:
                changes.append(f"🗑️ {key}")
            elif original_value != item_value:
                changes.append(f"✏️ {key}")

        if not changes:
            return "✓ INCHANGÉ"

        # Afficher max 3 changements
        summary = ", ".join(changes[:3])
        if len(changes) > 3:
            summary += f" ... +{len(changes) - 3}"
        return summary

    def accept(self):
        """S'assure que les données sont marquées comme validées avant de fermer."""
        if not self.validated_data:
            self.validated_data = self._build_validated_payload(exclude_errors=True)

        # Remplir uuid_verificateur avec l'utilisateur actuel au clic Valider.
        try:
            from .token_manager import TokenManager
            tm = TokenManager()
            user_uuid = _normalize_uuid(tm.get_user_id())
            if user_uuid:
                if isinstance(self.validated_data, dict):
                    for table_data in self.validated_data.values():
                        for row in table_data:
                            _stamp_verifier_uuid(row, user_uuid)
                elif isinstance(self.validated_data, list):
                    for row in self.validated_data:
                        _stamp_verifier_uuid(row, user_uuid)
        except Exception:
            pass

        super().accept()

    def validation_final_summary(self):
        counts = self._global_counts()
        published_tables = [
            table_name
            for table_name, publish in self.table_publish_state.items()
            if publish
        ]
        return (
            f"Tables publiées : {len(published_tables)}/{counts['tables']}\n"
            f"Lignes retenues : {counts['ok']}\n"
            f"Lignes exclues : {counts['excluded']}\n"
            f"Anomalies non publiées : {counts['errors']}\n\n"
            "La validation finale concerne toutes les tables cochées, pas seulement la table affichée."
        )

    def confirm_accept(self):
        if not any(self.table_publish_state.values()):
            self.show_warning("Validation", "Aucune table n'est cochée pour publication.")
            return
        reply = QMessageBox.question(
            self,
            "Confirmer validation multi-tables",
            self.validation_final_summary(),
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.validated_data = self._build_validated_payload(exclude_errors=True)
            self.accept()

    def auto_merge(self):
        """Fusion automatique des données pour toutes les tables."""
        counts = self._global_counts()
        reply = QMessageBox.question(
            self, "Valider les lignes correctes",
            f"Valider les lignes correctes de {counts['tables']} table(s) ?\n"
            f"{counts['ok']} ligne(s) seront retenues."
            + (f"\n{counts['errors']} ligne(s) avec anomalie seront exclues." if counts['errors'] else "")
        )
        
        if reply == QMessageBox.Yes:
            self.validated_data = self._build_validated_payload(exclude_errors=True)

            self.progress.setValue(100)
            self.show_info("Succès", "Lignes correctes prêtes à publier")
            self.accept()
    
    def manual_review(self):
        """Révision manuelle"""
        self.populate_issues_table()
        self.tabs.setCurrentIndex(1)
    
    def export_report(self):
        """Exporte un rapport de validation"""
        report = {
            'date': str(__import__('datetime').datetime.now()),
            'summary': self._global_counts(),
            'errors': self.validation_errors,
            'excluded_rows': {table: sorted(rows) for table, rows in self.excluded_rows.items()},
            'included_error_rows': {table: sorted(rows) for table, rows in self.included_error_rows.items()},
            'table_publish_state': self.table_publish_state,
            'tables': {
                table_name: {
                    'collected': len(self.full_collected_data.get(table_name, [])),
                    'original': len(self.full_original_data.get(table_name, [])),
                }
                for table_name in self.full_collected_data
            }
        }
        
        import tempfile
        temp_dir = tempfile.gettempdir()
        filename = os.path.join(temp_dir, "validation_report.json")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        
        self.show_info("Rapport Exporté", f"Rapport sauvegardé: {filename}")

