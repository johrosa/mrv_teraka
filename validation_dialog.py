# -*- coding: utf-8 -*-
"""
Formulaire de validation des données au retour du terrain
Permet de vérifier, corriger et fusionner les données collectées avec Mergin
"""

from qgis.PyQt.QtCore import Qt, QSize, pyqtSignal
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QTableWidget, QTableWidgetItem, QComboBox,
    QLineEdit, QSpinBox, QDoubleSpinBox, QMessageBox, QProgressBar,
    QHeaderView, QCheckBox, QTextEdit, QGroupBox, QFormLayout
)
from qgis.PyQt.QtGui import QColor, QFont
from qgis.core import QgsProject, QgsVectorLayer
import json


class DataValidationDialog(QDialog):
    """Formulaire de validation et fusion des données collectées"""
    
    data_merged = pyqtSignal(dict)  # Signal quand données fusionnées
    
    def __init__(self, parent=None, collected_data=None, original_data=None):
        super().__init__(parent)
        self.collected_data = collected_data or []
        self.original_data = original_data or []
        self.validated_data = []
        self.setWindowTitle("Validation des Données Collectées")
        self.setGeometry(100, 100, 1000, 600)
        self.initUI()
    
    def initUI(self):
        """Initialise l'interface"""
        layout = QVBoxLayout()
        
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
        self.btn_validate.clicked.connect(self.accept)
        
        button_layout.addWidget(self.btn_cancel)
        button_layout.addWidget(self.btn_validate)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.populate_data()
    
    def create_overview_tab(self):
        """Onglet vue d'ensemble"""
        widget = QGroupBox("Résumé des Données")
        layout = QFormLayout()
        
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
        self.table_collected.setColumnCount(0)
        self.populate_table_from_data(self.table_collected, self.collected_data)
        
        layout.addWidget(self.table_collected)
        
        widget = QGroupBox("Données Collectées")
        widget.setLayout(layout)
        return widget
    
    def create_comparison_tab(self):
        """Onglet comparaison avant/après"""
        layout = QVBoxLayout()
        
        # Contrôles de comparaison
        ctrl_layout = QHBoxLayout()
        
        ctrl_layout.addWidget(QLabel("Sélectionner enregistrement:"))
        self.combo_records = QComboBox()
        self.combo_records.currentIndexChanged.connect(self.show_comparison)
        ctrl_layout.addWidget(self.combo_records)
        
        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout)
        
        # Tables de comparaison
        tables_layout = QHBoxLayout()
        
        # Avant
        layout_before = QVBoxLayout()
        layout_before.addWidget(QLabel("<b>Avant (Original)</b>"))
        self.table_before = QTableWidget()
        layout_before.addWidget(self.table_before)
        
        # Après
        layout_after = QVBoxLayout()
        layout_after.addWidget(QLabel("<b>Après (Collecté)</b>"))
        self.table_after = QTableWidget()
        layout_after.addWidget(self.table_after)
        
        tables_layout.addLayout(layout_before)
        tables_layout.addLayout(layout_after)
        layout.addLayout(tables_layout)
        
        widget = QGroupBox("Comparaison Avant/Après")
        widget.setLayout(layout)
        return widget
    
    def create_validation_tab(self):
        """Onglet validation ligne par ligne"""
        layout = QVBoxLayout()
        
        self.table_validation = QTableWidget()
        self.table_validation.setColumnCount(5)
        self.table_validation.setHorizontalHeaderLabels([
            "ID", "Statut", "Changements", "Action", "Commentaire"
        ])
        
        # Remplir les données de validation
        self.table_validation.setRowCount(len(self.collected_data))
        for row, item in enumerate(self.collected_data):
            self.table_validation.setItem(row, 0, QTableWidgetItem(str(item.get('id', ''))))
            
            # Statut
            status_combo = QComboBox()
            status_combo.addItems(['✓ Valide', '⚠️ À Réviser', '❌ Rejeter', '🆕 Nouveau'])
            self.table_validation.setCellWidget(row, 1, status_combo)
            
            # Changements (détectés automatiquement)
            changes = self.detect_changes(item, row)
            self.table_validation.setItem(row, 2, QTableWidgetItem(changes))
            
            # Action
            action_combo = QComboBox()
            action_combo.addItems(['Fusionner', 'Remplacer', 'Archiver', 'Manuel'])
            self.table_validation.setCellWidget(row, 3, action_combo)
            
            # Commentaire
            comment = QLineEdit()
            self.table_validation.setCellWidget(row, 4, comment)
        
        layout.addWidget(self.table_validation)
        
        widget = QGroupBox("Validation Détaillée")
        widget.setLayout(layout)
        return widget
    
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
        """Remplit les tables avec les données"""
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
    
    def show_comparison(self, index):
        """Affiche la comparaison avant/après pour un enregistrement"""
        if 0 <= index < len(self.collected_data):
            item = self.collected_data[index]
            
            # Remplir après
            self.table_after.clear()
            self.table_after.setRowCount(len(item))
            for row, (key, value) in enumerate(item.items()):
                self.table_after.setItem(row, 0, QTableWidgetItem(key))
                self.table_after.setItem(row, 1, QTableWidgetItem(str(value)))
    
    def detect_changes(self, item, index):
        """Détecte les changements par rapport à l'original"""
        if index >= len(self.original_data):
            return "🆕 Nouveau"
        
        original = self.original_data[index]
        changes = []
        
        for key in item.keys():
            if key not in original or original[key] != item[key]:
                changes.append(key)
        
        if not changes:
            return "✓ Aucun changement"
        
        return f"⚠️ {', '.join(changes[:3])}"
    
    def auto_merge(self):
        """Fusion automatique des données"""
        reply = QMessageBox.question(
            self, "Fusion Automatique",
            "Fusionner automatiquement toutes les données?\n"
            "Les nouveaux enregistrements seront ajoutés."
        )
        
        if reply == QMessageBox.Yes:
            self.validated_data = self.collected_data
            self.progress.setValue(100)
            QMessageBox.information(self, "Succès", "Données prêtes à fusionner")
    
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
        
        filename = "/tmp/validation_report.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        
        QMessageBox.information(self, "Rapport Exporté", f"Rapport sauvegardé: {filename}")

