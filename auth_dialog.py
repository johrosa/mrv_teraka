# -*- coding: utf-8 -*-
"""
Formulaire d'authentification pour MrvTeraka
Gère la connexion et la déconnexion aux APIs PostgREST/Django
"""

import re
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QCheckBox, QMessageBox, QComboBox
)
from qgis.PyQt.QtCore import Qt, QSettings
from qgis.PyQt.QtGui import QIcon, QPixmap
from .utils import Utils


class AuthDialog(QDialog):
    """Formulaire d'authentification avec options avancées"""
    
    def __init__(self, parent=None, api_modes=None):
        """
        Initialise le formulaire d'authentification
        
        Args:
            parent: Widget parent
            api_modes: Dict avec les modes disponibles {nom: PostgRESTMode}
        """
        super().__init__(parent)
        self.api_modes = api_modes or {}
        self.token = None
        self.setup_ui()
        self.load_saved_settings()
    
    def setup_ui(self):
        """Crée l'interface du formulaire"""
        self.setWindowTitle("Authentification MrvTeraka")
        self.setGeometry(100, 100, 450, 350)
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        # Titre
        title_label = QLabel("Connexion à l'API")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # Mode API
        if self.api_modes:
            mode_layout = QHBoxLayout()
            l_mode = QLabel("Mode API:")
            l_mode.setMinimumWidth(120)
            mode_layout.addWidget(l_mode)
            self.mode_combo = QComboBox()
            self.mode_combo.addItems(list(self.api_modes.keys()))
            mode_layout.addWidget(self.mode_combo)
            layout.addLayout(mode_layout)
        
        # URL de base
        url_layout = QHBoxLayout()
        l_url = QLabel("URL API:")
        l_url.setMinimumWidth(120)
        url_layout.addWidget(l_url)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("http://127.0.0.1:8050")
        self.url_input.setText("http://127.0.0.1:8050")
        url_layout.addWidget(self.url_input)
        layout.addLayout(url_layout)
        
        # Email/Username
        user_layout = QHBoxLayout()
        l_user = QLabel("Email/Utilisateur:")
        l_user.setMinimumWidth(120)
        user_layout.addWidget(l_user)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("user@example.com")
        user_layout.addWidget(self.username_input)
        layout.addLayout(user_layout)
        
        # Mot de passe
        pass_layout = QHBoxLayout()
        l_pass = QLabel("Mot de passe:")
        l_pass.setMinimumWidth(120)
        pass_layout.addWidget(l_pass)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("••••••••")
        self.password_input.setEchoMode(QLineEdit.Password)
        pass_layout.addWidget(self.password_input)
        layout.addLayout(pass_layout)
        
        # Afficher le mot de passe
        show_pass_layout = QHBoxLayout()
        show_pass_layout.addStretch()
        self.show_password_check = QCheckBox("Afficher le mot de passe")
        self.show_password_check.stateChanged.connect(self.toggle_password_visibility)
        show_pass_layout.addWidget(self.show_password_check)
        layout.addLayout(show_pass_layout)
        
        # Options de stockage
        self.remember_check = QCheckBox("Mémoriser les identifiants")
        layout.addWidget(self.remember_check)
        
        # Boutons d'action
        button_layout = QHBoxLayout()
        
        self.login_button = QPushButton("Se connecter")
        self.login_button.clicked.connect(self.accept)
        button_layout.addWidget(self.login_button)
        
        self.cancel_button = QPushButton("Annuler")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # Message de statut
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def toggle_password_visibility(self):
        """Affiche/cache le mot de passe"""
        if self.show_password_check.isChecked():
            self.password_input.setEchoMode(QLineEdit.Normal)
        else:
            self.password_input.setEchoMode(QLineEdit.Password)
    
    def load_saved_settings(self):
        """Charge les identifiants sauvegardés si disponibles"""
        settings = QSettings('iTeraka', 'MrvTeraka')
        
        saved_username = settings.value('auth/username', '')
        saved_url = settings.value('auth/url', 'http://127.0.0.1:8050')
        remember = settings.value('auth/remember', False, type=bool)
        saved_mode = settings.value('auth/mode', 'Django')
        
        self.url_input.setText(saved_url)
        if hasattr(self, 'mode_combo'):
            index = self.mode_combo.findText(saved_mode)
            if index >= 0:
                self.mode_combo.setCurrentIndex(index)
        
        if remember:
            if saved_username:
                self.username_input.setText(saved_username)
            #self.mergin_user_input.setText(settings.value('auth/mergin_username', ''))
            self.remember_check.setChecked(True)
    
    def save_settings(self):
        """Sauvegarde les paramètres"""
        settings = QSettings('iTeraka', 'MrvTeraka')
        
        # L'URL est toujours sauvegardée pour plus de confort
        settings.setValue('auth/url', self.url_input.text().strip())
        if hasattr(self, 'mode_combo'):
            settings.setValue('auth/mode', self.mode_combo.currentText())

        if self.remember_check.isChecked():
            settings.setValue('auth/username', self.username_input.text().strip())
            #settings.setValue('auth/mergin_username', self.mergin_user_input.text().strip())
            settings.setValue('auth/remember', True)
        else:
            settings.remove('auth/username')
            #settings.remove('auth/mergin_username')
            settings.setValue('auth/remember', False)
        
        settings.sync()
    
    def get_credentials(self):
        """Retourne les identifiants saisis"""
        return {
            'username': self.username_input.text().strip(),
            'password': self.password_input.text(),
            'url': self.url_input.text().strip(),
            #'mergin_username': self.mergin_user_input.text().strip(),
            #'mergin_password': self.mergin_pass_input.text(),
            'mode': self.mode_combo.currentText() if hasattr(self, 'mode_combo') else None,
            'remember': self.remember_check.isChecked()
        }
    
    def show_error(self, message):
        """Affiche un message d'erreur"""
        self.status_label.setText(f"❌ {message}")

        if message and re.search(r'<(?:!doctype|html|head|body|div|span|p|h1|h2|h3)', message, re.IGNORECASE):
            try:
                from .django_error_viewer import show_django_error
                show_django_error(
                    parent=self,
                    error_code=500,
                    error_reason='Erreur d\'authentification',
                    html_content=message,
                    error_message='',
                    url='',
                    method='POST',
                    headers={},
                    text_content=message
                )
                return
            except Exception:
                pass

        QMessageBox.critical(self, "Erreur d'authentification", Utils.compact_dialog_message(message))

    def show_success(self, message):
        """Affiche un message de succès"""
        self.status_label.setText(f"✓ {message}")
    
    def get_api_mode(self):
        """Retourne le mode API sélectionné"""
        if hasattr(self, 'mode_combo'):
            mode_name = self.mode_combo.currentText()
            return self.api_modes.get(mode_name)
        return None
