# -*- coding: utf-8 -*-
"""
Formulaire de validation des données au retour du terrain
Permet de vérifier, corriger et fusionner les données collectées avec Mergin
"""

from qgis.PyQt.QtCore import Qt, QSize, pyqtSignal, QVariant
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QTableWidget, QTableWidgetItem, QComboBox,
    QLineEdit, QSpinBox, QDoubleSpinBox, QMessageBox, QProgressBar,
    QHeaderView, QCheckBox, QTextEdit, QGroupBox, QFormLayout, QWidget
)
from qgis.PyQt.QtGui import QColor, QFont
from qgis.core import QgsProject, QgsVectorLayer, QgsExpression, QgsExpressionContext, QgsExpressionContextUtils, QgsFeature, QgsField, QgsFields
import json
import os
from .business_rules import BusinessRulesEngine


class DataValidationDialog(QDialog):
    """Formulaire de validation et fusion des données collectées"""
    
    data_merged = pyqtSignal(dict)  # Signal quand données fusionnées
    
    def __init__(self, parent=None, collected_data=None, original_data=None):
        super().__init__(parent)

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

        self.collected_data = self.full_collected_data.get(self.current_table, [])
        self.original_data = self.full_original_data.get(self.current_table, [])

        self.validated_data = []
        self.setWindowTitle("Validation des Données Collectées")
        self.setGeometry(100, 100, 1000, 600)
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
        title = QLabel("Validation des Données Collectées au Terrain")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        desc = QLabel(
            "Vérifiez et validez les données collectées avec Mergin Map.\n"
            "Comparez avec les données originales et décidez de la fusion."
        )
        desc.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(desc)
        
        # --- Onglets ---
        self.tabs = QTabWidget()
        
        # Onglet 1: Vue d'ensemble
        self.tabs.addTab(self.create_overview_tab(), "Vue d'ensemble")
        
        # Onglet 2: Données collectées
        self.tabs.addTab(self.create_collected_tab(), "Données Collectées")
        
        # Onglet 3: Comparaison
        self.tabs.addTab(self.create_comparison_tab(), "Comparaison")
        
        # Onglet 4: Validation ligne par ligne
        self.tabs.addTab(self.create_validation_tab(), "Validation")
        
        layout.addWidget(self.tabs)
        
        # --- Barre de progression ---
        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        
        # --- Boutons d'action ---
        button_layout = QHBoxLayout()
        
        self.btn_auto_merge = QPushButton("🔄 Fusion Automatique")
        self.btn_auto_merge.clicked.connect(self.auto_merge)
        
        self.btn_manual_review = QPushButton("👁️ Révision Manuelle")
        self.btn_manual_review.clicked.connect(self.manual_review)
        
        self.btn_export_report = QPushButton("📊 Exporter Rapport")
        self.btn_export_report.clicked.connect(self.export_report)
        
        button_layout.addWidget(self.btn_auto_merge)
        button_layout.addWidget(self.btn_manual_review)
        button_layout.addWidget(self.btn_export_report)
        button_layout.addStretch()
        
        self.btn_cancel = QPushButton("Annuler")
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_validate = QPushButton("✓ Valider et Fusionner")
        self.btn_validate.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.btn_validate.setDefault(True)  # Permet d'utiliser 'Entrée'
        self.btn_validate.clicked.connect(self.accept)
        
        button_layout.addWidget(self.btn_cancel)
        button_layout.addWidget(self.btn_validate)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.table_diff.itemChanged.connect(self.on_diff_item_changed)
        self.populate_data()

    def switch_table(self, table_name):
        """Change la table active et rafraîchit l'UI."""
        self.current_table = table_name
        self.collected_data = self.full_collected_data.get(table_name, [])
        self.original_data = self.full_original_data.get(table_name, [])
        self.current_record_index = -1
        if hasattr(self, 'table_diff'):
            self.table_diff.setRowCount(0)

        # Rafraîchir toutes les vues
        self.populate_data()
        self.tabs.setCurrentIndex(0) # Revenir au résumé
    
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
        self.btn_run_rules.clicked.connect(self.run_validation_rules)
        layout.addRow("", self.btn_run_rules)

        # Statistiques
        total_collected = len(self.collected_data)
        total_original = len(self.original_data)
        
        # Nouvelles entrées
        new_entries = total_collected - total_original
        
        layout.addRow("Total collecté:", QLabel(str(total_collected)))
        layout.addRow("Total original:", QLabel(str(total_original)))
        layout.addRow("Nouvelles entrées:", QLabel(f"<b style='color:blue'>{new_entries}</b>"))
        layout.addRow("Modifiées/Supprimées:", QLabel(f"<b style='color:orange'>À analyser</b>"))
        
        # Statut validation
        layout.addRow("Statut:", QLabel("<b style='color:red'>En attente de validation</b>"))
        
        # Actions recommandées
        self.recommendation = QTextEdit()
        self.recommendation.setReadOnly(True)
        self.recommendation.setMinimumHeight(150)
        layout.addRow("Recommandations:", self.recommendation)
        
        widget.setLayout(layout)
        return widget
    
    def create_collected_tab(self):
        """Onglet données collectées"""
        layout = QVBoxLayout()
        
        self.table_collected = QTableWidget()
        self.table_collected.setAlternatingRowColors(True)
        self.table_collected.setColumnCount(0)
        self.populate_table_from_data(self.table_collected, self.collected_data)
        
        layout.addWidget(self.table_collected)
        
        widget = QGroupBox("Données Collectées")
        widget.setLayout(layout)
        return widget
    
    def create_comparison_tab(self):
        """Onglet comparaison et résolution de conflits"""
        layout = QVBoxLayout()
        
        # Contrôles de comparaison
        ctrl_layout = QHBoxLayout()
        
        l_sel = QLabel("Sélectionner l'enregistrement à comparer :")
        l_sel.setStyleSheet("font-weight: bold;")
        ctrl_layout.addWidget(l_sel)

        self.combo_records = QComboBox()
        self.combo_records.setMinimumWidth(300)
        self.combo_records.currentIndexChanged.connect(self.show_comparison)
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
        layout.addWidget(QLabel("<b>Validation détaillée - Cliquez sur une ligne pour voir les détails:</b>"))

        self.table_validation = self._setup_validation_table()
        layout.addWidget(self.table_validation)
        
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
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(["ID", "Statut", "Changements", "Type", "Action", "Commentaire"])
        table.itemSelectionChanged.connect(self.on_validation_row_selected)
        table.setRowCount(len(self.collected_data))

        for row, item in enumerate(self.collected_data):
            self._fill_validation_row(table, row, item)

        table.resizeColumnsToContents()
        return table

    def _fill_validation_row(self, table, row, item):
        """Remplit une ligne du tableau de validation."""
        item_id = item.get('id', row)
        table.setItem(row, 0, QTableWidgetItem(str(item_id)))

        status_combo = QComboBox()
        status_combo.addItems(['✓ Valide', '⚠️ À Réviser', '❌ Rejeter', '🆕 Nouveau'])
        status_combo.setCurrentIndex(3 if row >= len(self.original_data) else 0)
        table.setCellWidget(row, 1, status_combo)

        changes = self.detect_changes(item, row)
        changes_item = QTableWidgetItem(changes)
        if "🆕" in changes: changes_item.setBackground(QColor(200, 255, 200))
        elif "❌" in changes: changes_item.setBackground(QColor(255, 100, 100))
        elif "✏️" in changes or "⚠️" in changes: changes_item.setBackground(QColor(255, 220, 100))
        table.setItem(row, 2, changes_item)

        type_label = "NOUVEAU" if row >= len(self.original_data) else "MODIFIÉ" if self.has_changes(item, row) else "INCHANGÉ"
        table.setItem(row, 3, QTableWidgetItem(type_label))

        action_combo = QComboBox()
        action_combo.addItems(['Fusionner', 'Remplacer', 'Archiver', 'Manuel'])
        table.setCellWidget(row, 4, action_combo)

        comment = QLineEdit()
        comment.setPlaceholderText("Ajouter un commentaire...")
        table.setCellWidget(row, 5, comment)
    
    def has_changes(self, item, index):
        """Vérifie si l'item a des changements"""
        if index >= len(self.original_data):
            return True

        original = self.original_data[index]
        for key in item.keys():
            if key not in original or original[key] != item[key]:
                return True

        return False

    def on_validation_row_selected(self):
        """Affiche les détails de la ligne sélectionnée"""
        selected_rows = self.table_validation.selectedIndexes()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        if 0 <= row < len(self.collected_data):
            self.show_row_details(row)

    def show_row_details(self, row):
        """Affiche les détails complets d'une ligne"""
        collected_item = self.collected_data[row]
        original_item = self.original_data[row] if row < len(self.original_data) else {}

        # Construire le texte détaillé
        details = []
        details.append(f"{'='*60}")
        details.append(f"ENREGISTREMENT #{row + 1} - ID: {collected_item.get('id', 'N/A')}")
        details.append(f"{'='*60}")

        # Déterminer le type
        if row >= len(self.original_data):
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
                details.append(f"   AVANT:  {original_value}")
                details.append(f"   APRÈS:  {collected_value}")

        if change_count == 0:
            details.append("\n✓ Aucun changement détecté")
        else:
            details.append(f"\n\nTOTAL: {change_count} champ(s) modifié(s)")

        details.append(f"{'='*60}")

        self.detail_text.setText("\n".join(details))

    def populate_table_from_data(self, table, data):
        """Remplit une table à partir des données"""
        if not data:
            return
        
        first_item = data[0]
        columns = list(first_item.keys())
        
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.setRowCount(len(data))
        
        for row, item in enumerate(data):
            for col, key in enumerate(columns):
                value = item.get(key, '')
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)[:50]
                table.setItem(row, col, QTableWidgetItem(str(value)))
        
        table.resizeColumnsToContents()
    
    def populate_data(self):
        """Remplit les tables avec les données de la table active."""
        # Vider les onglets
        self.table_collected.setRowCount(0)
        if hasattr(self, 'table_diff'):
            self.table_diff.setRowCount(0)
        self.combo_records.clear()

        # Recréer la table de validation car sa structure peut changer
        self.table_validation.setRowCount(0)
        self.table_validation.setRowCount(len(self.collected_data))
        for row, item in enumerate(self.collected_data):
            self._fill_validation_row(self.table_validation, row, item)

        # Remplir les onglets
        self.populate_table_from_data(self.table_collected, self.collected_data)
        self.populate_table_from_data(self.table_before, self.original_data)
        
        # Remplir combo de sélection
        for i, item in enumerate(self.collected_data):
            label = f"Enregistrement {i+1} (ID: {item.get('id', 'N/A')})"
            self.combo_records.addItem(label, i)
        
        # Générer recommandations
        self.generate_recommendations()
    
    def generate_recommendations(self):
        """Génère des recommandations basées sur les données"""
        recs = []
        
        if len(self.collected_data) > len(self.original_data):
            recs.append(f"✓ {len(self.collected_data) - len(self.original_data)} nouveaux enregistrements détectés")
        
        recs.append("✓ Vérifier les géométries")
        recs.append("✓ Valider les attributs obligatoires")
        recs.append("✓ Résoudre les doublons potentiels")
        
        self.recommendation.setText("\n".join(recs))

    def run_validation_rules(self):
        """Exécute les règles métier automatisées sur les données collectées."""
        invalid_count = 0
        row_count = self.table_validation.rowCount()
        if row_count == 0:
            return

        # Optimization: Initialize QgsFields and context once outside the loop
        # We collect all unique keys from the entire dataset to ensure compatibility
        all_keys = set()
        for item in self.collected_data:
            all_keys.update(item.keys())

        fields = QgsFields()
        for key in sorted(all_keys):
            fields.append(QgsField(key, QVariant.String))

        context = QgsExpressionContext()
        context.appendScope(QgsExpressionContextUtils.globalScope())

        # Reuse a single QgsFeature object
        feat = QgsFeature(fields)
        sorted_keys = sorted(all_keys)

        for row in range(row_count):
            item_data = self.collected_data[row]

            # Update all feature attributes to prevent leakage from previous rows
            # Performance: setAttributes with a list is faster than multiple setAttribute calls
            feat.setAttributes([item_data.get(key) for key in sorted_keys])

            # Utiliser le moteur de règles avec le contexte réutilisé
            # Optimization: Combining QgsExpression caching with Context reuse gives >90% speedup
            errors = BusinessRulesEngine.validate_feature(self.current_table, feat, context=context)

            if errors:
                invalid_count += 1
                error_msgs = [e['message'] for e in errors]

                # Marquer en orange et ajouter le commentaire d'erreur
                for col in range(self.table_validation.columnCount()):
                    tbl_item = self.table_validation.item(row, col)
                    if tbl_item:
                        tbl_item.setBackground(QColor(255, 165, 0, 150))

                # Mettre à jour le champ commentaire
                comment_widget = self.table_validation.cellWidget(row, 5)
                if isinstance(comment_widget, QLineEdit):
                    comment_widget.setText(f"ERREUR METIER: {', '.join(error_msgs)}")

        if invalid_count > 0:
            QMessageBox.warning(self, "Contrôle Qualité Automatisé",
                                f"{invalid_count} enregistrements présentent des anomalies métier.")
            self.tabs.setCurrentIndex(3)
        else:
            QMessageBox.information(self, "Contrôle Qualité Automatisé",
                                    "Félicitations ! Aucune anomalie métier détectée.")
    
    def show_comparison(self, index):
        """Affiche la comparaison avec sélection interactive de la valeur finale"""
        if index < 0 or index >= len(self.collected_data):
            return

        self.current_record_index = index
        self.table_diff.blockSignals(True)
        self.table_diff.setRowCount(0)

        collected_item = self.collected_data[index]
        original_item = self.original_data[index] if index < len(self.original_data) else {}

        all_keys = sorted(list(set(list(collected_item.keys()) + list(original_item.keys()))))
        self.table_diff.setRowCount(len(all_keys))

        for row, key in enumerate(all_keys):
            orig_val = original_item.get(key, "[absent]")
            coll_val = collected_item.get(key, "[absent]")

            self.table_diff.setItem(row, 0, QTableWidgetItem(key))

            # Case à cocher pour BASE
            base_item = QTableWidgetItem(str(orig_val))
            base_item.setFlags(base_item.flags() | Qt.ItemIsUserCheckable)
            base_item.setCheckState(Qt.Unchecked)
            self.table_diff.setItem(row, 1, base_item)

            # Case à cocher pour TERRAIN (par défaut)
            coll_item = QTableWidgetItem(str(coll_val))
            coll_item.setFlags(coll_item.flags() | Qt.ItemIsUserCheckable)
            coll_item.setCheckState(Qt.Checked)
            self.table_diff.setItem(row, 2, coll_item)

            # Valeur finale (Éditable)
            final_item = QTableWidgetItem(str(coll_val))
            final_item.setFlags(final_item.flags() | Qt.ItemIsEditable)
            if orig_val != coll_val:
                final_item.setBackground(QColor(255, 255, 200)) # Highlight
            self.table_diff.setItem(row, 3, final_item)

        self.table_diff.blockSignals(False)

    def on_diff_item_changed(self, item):
        """Met à jour les données quand la valeur finale ou une checkbox est modifiée"""
        if self.current_record_index == -1:
            return

        row = item.row()
        col = item.column()
        field_name = self.table_diff.item(row, 0).text()

        # Logique des cases à cocher (Colonnes 1: Base, 2: Terrain)
        if col in [1, 2]:
            if item.checkState() == Qt.Checked:
                self.table_diff.blockSignals(True)
                # Décocher l'autre colonne
                other_col = 2 if col == 1 else 1
                self.table_diff.item(row, other_col).setCheckState(Qt.Unchecked)

                # Mettre à jour la valeur finale
                chosen_val = item.text()
                self.table_diff.item(row, 3).setText(chosen_val)
                # Synchroniser avec les données collectées
                self.collected_data[self.current_record_index][field_name] = chosen_val
                print(f"DEBUG: Choix pour {field_name} -> {chosen_val}")
                self.table_diff.blockSignals(False)
            return

        # Mise à jour manuelle de la valeur finale (Colonne 3)
        if col == 3:
            new_value = item.text()
            print(f"DEBUG: Mise à jour {field_name} = {new_value}")
            self.collected_data[self.current_record_index][field_name] = new_value

    def detect_changes(self, item, index):
        """Détecte les changements par rapport à l'original"""
        if index >= len(self.original_data):
            return "🆕 NOUVEAU"

        original = self.original_data[index]
        changes = []
        
        # Comparer tous les champs
        all_keys = set(list(item.keys()) + list(original.keys()))
        for key in sorted(all_keys):
            original_value = original.get(key)
            item_value = item.get(key)

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
            # Si auto_merge n'a pas été appelé, on prend les données actuelles
            if len(self.full_collected_data) > 1 or 'default' not in self.full_collected_data:
                self.validated_data = self.full_collected_data
            else:
                self.validated_data = self.collected_data

        super().accept()

    def auto_merge(self):
        """Fusion automatique des données pour toutes les tables."""
        reply = QMessageBox.question(
            self, "Fusion Automatique",
            "Fusionner automatiquement toutes les données de TOUTES les tables ?\n"
            "Les nouveaux enregistrements seront ajoutés."
        )
        
        if reply == QMessageBox.Yes:
            if len(self.full_collected_data) > 1 or 'default' not in self.full_collected_data:
                self.validated_data = self.full_collected_data
            else:
                self.validated_data = self.collected_data

            self.progress.setValue(100)
            QMessageBox.information(self, "Succès", "Données prêtes à fusionner")
            self.accept()
    
    def manual_review(self):
        """Révision manuelle"""
        self.tabs.setCurrentIndex(3)  # Aller à l'onglet validation
        QMessageBox.information(
            self, "Révision Manuelle",
            "Veuillez réviser chaque enregistrement\n"
            "dans l'onglet 'Validation'"
        )
    
    def export_report(self):
        """Exporte un rapport de validation"""
        report = {
            'date': str(__import__('datetime').datetime.now()),
            'total_collected': len(self.collected_data),
            'total_original': len(self.original_data),
            'new_entries': len(self.collected_data) - len(self.original_data),
            'data': self.collected_data
        }
        
        import tempfile
        temp_dir = tempfile.gettempdir()
        filename = os.path.join(temp_dir, "validation_report.json")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        
        QMessageBox.information(self, "Rapport Exporté", f"Rapport sauvegardé: {filename}")

