# -*- coding: utf-8 -*-
"""
Boîte de dialogue pour sélectionner les tables/endpoints à synchroniser.
"""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QCheckBox, QScrollArea, QWidget,
    QGroupBox, QDialogButtonBox
)


class TableSelectionDialog(QDialog):
    """Dialogue pour sélectionner les tables à synchroniser."""

    def __init__(self, available_tables, parent=None, title="Sélection des tables"):
        """
        Initialise le dialogue de sélection.

        Args:
            available_tables: dict ou list des tables disponibles
                Si dict: {layer_name: mapping_info}
                Si list: [layer_name1, layer_name2, ...]
            parent: Widget parent
            title: Titre de la fenêtre
        """
        super().__init__(parent)
        self.setWindowFlags(
            self.windowFlags() |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)

        # Convertir en dict si c'est une liste
        if isinstance(available_tables, list):
            self.available_tables = {name: {'endpoint': name} for name in available_tables}
        else:
            self.available_tables = available_tables

        self.checkboxes = {}
        self.select_all_checkbox = None

        self.setup_ui()

    def setup_ui(self):
        """Construit l'interface utilisateur."""
        layout = QVBoxLayout(self)

        # En-tête avec description
        header_label = QLabel(
            "Sélectionnez les tables à synchroniser :\n"
            "Utilisez 'Tout sélectionner' pour synchroniser toutes les tables."
        )
        header_label.setWordWrap(True)
        layout.addWidget(header_label)

        # Case "Tout sélectionner"
        select_all_layout = QHBoxLayout()
        self.select_all_checkbox = QCheckBox("✓ Tout sélectionner")
        self.select_all_checkbox.setStyleSheet("font-weight: bold; color: #0066cc;")
        self.select_all_checkbox.stateChanged.connect(self.on_select_all_changed)
        select_all_layout.addWidget(self.select_all_checkbox)
        select_all_layout.addStretch()
        layout.addLayout(select_all_layout)

        # Zone scrollable pour les tables
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Widget conteneur pour les checkboxes
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(5, 5, 5, 5)
        scroll_layout.setSpacing(5)

        # Grouper les tables par catégorie si possible
        if not self.available_tables:
            no_tables_label = QLabel("Aucune table disponible pour la synchronisation.")
            no_tables_label.setStyleSheet("color: #888; font-style: italic;")
            scroll_layout.addWidget(no_tables_label)
        else:
            # Créer une checkbox pour chaque table
            for layer_name, mapping in sorted(self.available_tables.items()):
                checkbox = QCheckBox(layer_name)

                # Ajouter des informations supplémentaires si disponibles
                endpoint = mapping.get('endpoint', layer_name)
                if endpoint and endpoint != layer_name:
                    checkbox.setToolTip(f"Endpoint API: {endpoint}")

                # Style alternatif pour meilleure lisibilité
                checkbox.setStyleSheet("padding: 5px;")

                checkbox.stateChanged.connect(self.on_checkbox_changed)
                self.checkboxes[layer_name] = checkbox
                scroll_layout.addWidget(checkbox)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)

        # Informations sur la sélection
        self.selection_info_label = QLabel()
        self.update_selection_info()
        layout.addWidget(self.selection_info_label)

        # Boutons OK/Annuler
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def on_select_all_changed(self, state):
        """Gérer le changement de la case 'Tout sélectionner'."""
        checked = (state == Qt.Checked)

        # Bloquer les signaux pour éviter les mises à jour multiples
        for checkbox in self.checkboxes.values():
            checkbox.blockSignals(True)
            checkbox.setChecked(checked)
            checkbox.blockSignals(False)

        self.update_selection_info()

    def on_checkbox_changed(self):
        """Gérer le changement d'une checkbox individuelle."""
        # Vérifier si toutes les cases sont cochées
        all_checked = all(cb.isChecked() for cb in self.checkboxes.values())
        none_checked = not any(cb.isChecked() for cb in self.checkboxes.values())

        # Mettre à jour la case "Tout sélectionner"
        self.select_all_checkbox.blockSignals(True)
        if all_checked:
            self.select_all_checkbox.setCheckState(Qt.Checked)
        elif none_checked:
            self.select_all_checkbox.setCheckState(Qt.Unchecked)
        else:
            self.select_all_checkbox.setCheckState(Qt.PartiallyChecked)
        self.select_all_checkbox.blockSignals(False)

        self.update_selection_info()

    def update_selection_info(self):
        """Met à jour le texte d'information sur la sélection."""
        selected_count = sum(1 for cb in self.checkboxes.values() if cb.isChecked())
        total_count = len(self.checkboxes)

        if selected_count == 0:
            info_text = "⚠ Aucune table sélectionnée"
            color = "#cc6600"
        elif selected_count == total_count:
            info_text = f"✓ Toutes les tables sélectionnées ({total_count})"
            color = "#006600"
        else:
            info_text = f"✓ {selected_count} table(s) sélectionnée(s) sur {total_count}"
            color = "#0066cc"

        self.selection_info_label.setText(info_text)
        self.selection_info_label.setStyleSheet(f"font-weight: bold; color: {color}; padding: 5px;")

    def get_selected_tables(self):
        """
        Retourne la liste des tables sélectionnées.

        Returns:
            list: Liste des noms de tables sélectionnées
        """
        return [
            layer_name
            for layer_name, checkbox in self.checkboxes.items()
            if checkbox.isChecked()
        ]

    def get_selected_mappings(self):
        """
        Retourne un dictionnaire des tables sélectionnées avec leurs mappings.

        Returns:
            dict: {layer_name: mapping_info} pour les tables sélectionnées
        """
        return {
            layer_name: self.available_tables[layer_name]
            for layer_name in self.get_selected_tables()
        }

    def is_all_selected(self):
        """
        Vérifie si toutes les tables sont sélectionnées.

        Returns:
            bool: True si toutes les tables sont sélectionnées
        """
        return self.select_all_checkbox.isChecked() or \
               all(cb.isChecked() for cb in self.checkboxes.values())


def show_table_selection_dialog(available_tables, parent=None, title="Sélection des tables"):
    """
    Affiche le dialogue de sélection et retourne les tables sélectionnées.

    Args:
        available_tables: dict ou list des tables disponibles
        parent: Widget parent
        title: Titre de la fenêtre

    Returns:
        tuple: (selected_tables_list, selected_mappings_dict, is_all_selected)
               ou (None, None, False) si annulé
    """
    dialog = TableSelectionDialog(available_tables, parent, title)

    if dialog.exec_() == QDialog.Accepted:
        return (
            dialog.get_selected_tables(),
            dialog.get_selected_mappings(),
            dialog.is_all_selected()
        )

    return None, None, False
