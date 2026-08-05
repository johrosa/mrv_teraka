# -*- coding: utf-8 -*-
"""
Visionneuse d'erreurs Django avec rendu HTML
Affiche les pages d'erreur Django (404, 500, etc.) avec support du rendu HTML
"""

from qgis.PyQt.QtCore import Qt, QSize, QUrl
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QTabWidget, QGroupBox, QFormLayout, QMessageBox
)
from qgis.PyQt.QtGui import QFont, QColor
from qgis.PyQt.QtWebEngineWidgets import QWebEngineView
import json
import html
from .utils import Utils


class DjangoErrorViewer(QDialog):
    """Visionneuse d'erreurs Django avec rendu HTML"""
    
    def __init__(self, parent=None, error_data=None):
        """
        Initialise la visionneuse d'erreur Django
        
        Args:
            parent: Widget parent
            error_data: Dict contenant les info d'erreur
                {
                    'status_code': 404,
                    'reason': 'Not Found',
                    'html': '<html>...</html>',
                    'text': 'contenu texte',
                    'url': 'http://...',
                    'method': 'GET',
                    'headers': {...}
                }
        """
        super().__init__(parent)

        self.setWindowFlags(
            self.windowFlags() |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        self.error_data = error_data or {}
        self.status_code = error_data.get('status_code', 500) if error_data else 500
        self.reason = error_data.get('reason', 'Erreur Inconnue') if error_data else 'Erreur Inconnue'
        
        self.setWindowTitle(f"Erreur Django {self.status_code} - {self.reason}")
        self.setGeometry(50, 50, 900, 600)
        self.initUI()
    
    def initUI(self):
        """Initialise l'interface"""
        layout = QVBoxLayout()
        
        # --- Titre et statut ---
        title_layout = QHBoxLayout()
        title = QLabel(f"Erreur HTTP {self.status_code}: {self.reason}")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        
        # Colorer selon le code d'erreur
        if self.status_code >= 500:
            title.setStyleSheet("color: #d32f2f; background-color: #ffebee; padding: 10px; border-radius: 5px;")
        elif self.status_code >= 400:
            title.setStyleSheet("color: #f57c00; background-color: #fff3e0; padding: 10px; border-radius: 5px;")
        
        title_layout.addWidget(title)
        layout.addLayout(title_layout)
        
        # --- Onglets ---
        self.tabs = QTabWidget()
        
        # Onglet 1: Rendu HTML
        self.tabs.addTab(self.create_html_tab(), "💻 Vue HTML")
        
        # Onglet 2: Informations téchniques
        self.tabs.addTab(self.create_info_tab(), "ℹ️ Infos Techniques")
        
        # Onglet 3: Contenu brut
        self.tabs.addTab(self.create_raw_tab(), "📄 Source Brute")
        
        layout.addWidget(self.tabs)
        
        # --- Boutons d'action ---
        button_layout = QHBoxLayout()
        
        self.btn_copy = QPushButton("📋 Copier l'erreur")
        self.btn_copy.clicked.connect(self.copy_error)
        
        self.btn_export = QPushButton("💾 Exporter comme fichier")
        self.btn_export.clicked.connect(self.export_error)
        
        button_layout.addWidget(self.btn_copy)
        button_layout.addWidget(self.btn_export)
        button_layout.addStretch()
        
        self.btn_close = QPushButton("Fermer")
        self.btn_close.clicked.connect(self.accept)
        button_layout.addWidget(self.btn_close)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.populate_data()
    
    def create_html_tab(self):
        """Onglet pour afficher le rendu HTML"""
        widget = QGroupBox("Rendu de la Page d'Erreur")
        layout = QVBoxLayout()
        
        html_content = self.error_data.get('html', '')
        
        if html_content:
            # Utiliser QWebEngineView pour le rendu HTML
            try:
                self.web_view = QWebEngineView()
                # Ajouter le contenu HTML
                self.web_view.setHtml(html_content)
                layout.addWidget(self.web_view)
            except Exception as e:
                # Fallback: Afficher en texte si QWebEngineView échoue
                text_edit = QTextEdit()
                text_edit.setMarkdown(html_content)
                text_edit.setReadOnly(True)
                layout.addWidget(text_edit)
        else:
            # Pas de contenu HTML, afficher un message
            no_html = QLabel("❌ Pas de contenu HTML disponible")
            no_html.setStyleSheet("color: #666; font-size: 12px; padding: 20px;")
            layout.addWidget(no_html)
        
        widget.setLayout(layout)
        return widget
    
    def create_info_tab(self):
        """Onglet pour afficher les informations techniques"""
        widget = QGroupBox("Informations Téchniques")
        layout = QFormLayout()
        
        # Codes d'erreur courants Django
        error_meanings = {
            400: "Mauvaise requête",
            401: "Non authentifié",
            403: "Accès refusé",
            404: "Page non trouvée",
            405: "Méthode non autorisée",
            408: "Délai d'attente dépassé",
            429: "Trop de requêtes",
            500: "Erreur interne du serveur",
            501: "Non implémenté",
            502: "Mauvaise passerelle",
            503: "Service indisponible",
            504: "Délai de la passerelle dépassé"
        }
        
        # Ajouter les infos
        layout.addRow("Code d'erreur:", QLabel(str(self.status_code)))
        layout.addRow("Raison:", QLabel(self.reason))
        layout.addRow("Signification:", QLabel(error_meanings.get(self.status_code, "Erreur inconnue")))
        
        # URL
        url = self.error_data.get('url', 'Non disponible')
        url_label = QLabel(url)
        url_label.setWordWrap(True)
        layout.addRow("URL:", url_label)
        
        # Méthode HTTP
        method = self.error_data.get('method', 'GET')
        layout.addRow("Méthode HTTP:", QLabel(method))
        
        # En-têtes
        headers = self.error_data.get('headers', {})
        if headers:
            headers_text = "\n".join([f"{k}: {v}" for k, v in headers.items()])
            headers_label = QTextEdit()
            headers_label.setPlainText(headers_text)
            headers_label.setReadOnly(True)
            headers_label.setMaximumHeight(200)
            layout.addRow("En-têtes:", headers_label)
        
        # Message d'erreur personnalisé
        error_msg = self.error_data.get('error_message', '')
        if error_msg:
            msg_label = QTextEdit()
            msg_label.setPlainText(error_msg)
            msg_label.setReadOnly(True)
            msg_label.setMaximumHeight(150)
            layout.addRow("Message d'erreur:", msg_label)
        
        widget.setLayout(layout)
        return widget
    
    def create_raw_tab(self):
        """Onglet pour afficher le contenu brut"""
        widget = QGroupBox("Contenu Brut")
        layout = QVBoxLayout()
        
        raw_text = QTextEdit()
        raw_text.setReadOnly(True)
        raw_text.setFont(QFont("Courier", 9))
        
        # Contenu brut (HTML ou texte)
        content = self.error_data.get('html', '') or self.error_data.get('text', '')
        
        # Si c'est du HTML, l'afficher formaté
        if content.startswith('<'):
            # Formater le HTML pour la lisibilité
            formatted = self._format_html(content)
            raw_text.setPlainText(formatted)
        else:
            raw_text.setPlainText(content)
        
        layout.addWidget(raw_text)
        widget.setLayout(layout)
        return widget
    
    def _format_html(self, html_content):
        """Formate le HTML pour meilleure lisibilité"""
        # Ajouter des retours à la ligne après certaines balises
        formatted = html_content
        formatted = formatted.replace('><', '>\n<')
        formatted = formatted.replace('  ', ' ')
        return formatted
    
    def populate_data(self):
        """Remplit les données"""
        # Les données sont déjà chargées dans error_data
        pass
    
    def copy_error(self):
        """Copie l'erreur dans le presse-papiers"""
        error_text = self._generate_error_report()
        
        import subprocess
        try:
            process = subprocess.Popen(['clip'], stdin=subprocess.PIPE)
            process.communicate(error_text.encode('utf-8'))
            QMessageBox.information(self, "Copié", "Erreur copiée dans le presse-papiers")
        except Exception:
            # Fallback: utiliser PyQt
            from qgis.PyQt.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(error_text)
            QMessageBox.information(self, "Copié", "Erreur copiée dans le presse-papiers")
    
    def export_error(self):
        """Exporte l'erreur dans un fichier HTML"""
        from qgis.PyQt.QtWidgets import QFileDialog
        import os
        from datetime import datetime
        
        # Nom par défaut du fichier
        default_name = f"erreur_django_{self.status_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        default_path = os.path.expanduser(f"~/Desktop/{default_name}")
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter l'erreur",
            default_path,
            "Fichiers HTML (*.html);;Fichiers texte (*.txt)"
        )
        
        if file_path:
            try:
                if file_path.endswith('.html'):
                    # Exporter le HTML avec styling
                    html_export = self._generate_html_report()
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(html_export)
                else:
                    # Exporter en texte brut
                    text_export = self._generate_error_report()
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(text_export)
                
                QMessageBox.information(self, "Exporté", Utils.compact_dialog_message(f"Erreur exportée: {file_path}"))
            except Exception as e:
                QMessageBox.critical(self, "Erreur", Utils.compact_dialog_message(f"Impossible d'exporter: {e}"))
    
    def _generate_error_report(self):
        """Génère un rapport d'erreur en texte brut"""
        lines = []
        lines.append("=" * 80)
        lines.append(f"ERREUR DJANGO {self.status_code}: {self.reason}")
        lines.append("=" * 80)
        lines.append("")
        
        # Infos techniques
        lines.append("INFORMATIONS TECHNIQUES")
        lines.append("-" * 80)
        lines.append(f"Code: {self.status_code}")
        lines.append(f"Raison: {self.reason}")
        lines.append(f"URL: {self.error_data.get('url', 'N/A')}")
        lines.append(f"Méthode: {self.error_data.get('method', 'GET')}")
        lines.append("")
        
        # En-têtes
        if self.error_data.get('headers'):
            lines.append("EN-TÊTES")
            lines.append("-" * 80)
            for k, v in self.error_data.get('headers', {}).items():
                lines.append(f"{k}: {v}")
            lines.append("")
        
        # Message d'erreur
        if self.error_data.get('error_message'):
            lines.append("MESSAGE D'ERREUR")
            lines.append("-" * 80)
            lines.append(self.error_data.get('error_message'))
            lines.append("")
        
        # Contenu brut
        if self.error_data.get('html') or self.error_data.get('text'):
            lines.append("CONTENU")
            lines.append("-" * 80)
            content = self.error_data.get('html', '') or self.error_data.get('text', '')
            lines.append(content[:2000])  # Limiter pour éviter trop gros fichier
            if len(content) > 2000:
                lines.append("... (contenu tronqué)")
        
        lines.append("")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def _generate_html_report(self):
        """Génère un rapport d'erreur en HTML"""
        html_parts = []
        html_parts.append("""
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Rapport d'Erreur Django</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    max-width: 1000px;
                    margin: 0;
                    padding: 20px;
                    background: #f5f5f5;
                    color: #333;
                }
                .container {
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }
                h1 {
                    color: #d32f2f;
                    border-bottom: 3px solid #d32f2f;
                    padding-bottom: 10px;
                }
                h2 {
                    color: #1976d2;
                    margin-top: 30px;
                    border-left: 4px solid #1976d2;
                    padding-left: 10px;
                }
                .error-badge {
                    display: inline-block;
                    background: #d32f2f;
                    color: white;
                    padding: 5px 15px;
                    border-radius: 4px;
                    font-weight: bold;
                    margin-right: 10px;
                }
                .info-table {
                    width: 100%;
                    border-collapse: collapse;
                    margin: 10px 0;
                }
                .info-table td {
                    padding: 8px;
                    border: 1px solid #ddd;
                }
                .info-table td:first-child {
                    background: #f9f9f9;
                    font-weight: bold;
                    width: 200px;
                }
                code {
                    background: #f4f4f4;
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-family: 'Courier New', monospace;
                }
                pre {
                    background: #f4f4f4;
                    padding: 15px;
                    border-radius: 4px;
                    overflow-x: auto;
                    border-left: 4px solid #1976d2;
                }
                .error-content {
                    background: #ffebee;
                    padding: 15px;
                    border-radius: 4px;
                    border-left: 4px solid #d32f2f;
                    margin: 10px 0;
                }
                .success {
                    color: #4caf50;
                }
                .warning {
                    color: #f57c00;
                }
                .error {
                    color: #d32f2f;
                }
            </style>
        </head>
        <body>
            <div class="container">
        """)
        
        # Titre avec badge
        html_parts.append(f"""
            <h1>
                <span class="error-badge">Erreur {self.status_code}</span>
                {html.escape(self.reason)}
            </h1>
        """)
        
        # Infos techniques
        html_parts.append("<h2>📊 Informations Téchniques</h2>")
        html_parts.append("<table class='info-table'>")
        html_parts.append(f"<tr><td>Code d'erreur</td><td class='error'><strong>{self.status_code}</strong></td></tr>")
        html_parts.append(f"<tr><td>Raison</td><td>{html.escape(self.reason)}</td></tr>")
        html_parts.append(f"<tr><td>URL</td><td><code>{html.escape(self.error_data.get('url', 'N/A'))}</code></td></tr>")
        html_parts.append(f"<tr><td>Méthode HTTP</td><td><code>{html.escape(self.error_data.get('method', 'GET'))}</code></td></tr>")
        html_parts.append("</table>")
        
        # En-têtes
        if self.error_data.get('headers'):
            html_parts.append("<h2>🔗 En-têtes HTTP</h2>")
            html_parts.append("<table class='info-table'>")
            for k, v in self.error_data.get('headers', {}).items():
                html_parts.append(f"<tr><td>{html.escape(str(k))}</td><td><code>{html.escape(str(v))}</code></td></tr>")
            html_parts.append("</table>")
        
        # Message d'erreur
        if self.error_data.get('error_message'):
            html_parts.append("<h2>⚠️ Message d'Erreur</h2>")
            html_parts.append(f"<div class='error-content'>{html.escape(self.error_data.get('error_message'))}</div>")
        
        # Contenu HTML original
        if self.error_data.get('html'):
            html_parts.append("<h2>💻 Page d'Erreur Django</h2>")
            html_parts.append("<pre>")
            html_parts.append(html.escape(self.error_data.get('html', '')[:1000]))
            if len(self.error_data.get('html', '')) > 1000:
                html_parts.append("\n... (contenu tronqué)")
            html_parts.append("</pre>")
        
        html_parts.append("""
            </div>
        </body>
        </html>
        """)
        
        return "\n".join(html_parts)


def show_django_error(parent, error_code, error_reason, html_content, error_message="", 
                     url="", method="GET", headers=None, text_content=""):
    """
    Fonction helper pour afficher une erreur Django
    
    Args:
        parent: Widget parent
        error_code: Code d'erreur HTTP (404, 500, etc.)
        error_reason: Raison de l'erreur
        html_content: Contenu HTML de la page d'erreur
        error_message: Message d'erreur additionnel
        url: URL de la requête
        method: Méthode HTTP
        headers: Dict des en-têtes HTTP
        text_content: Contenu texte alternatif
    """
    error_data = {
        'status_code': error_code,
        'reason': error_reason,
        'html': html_content,
        'text': text_content,
        'url': url,
        'method': method,
        'headers': headers or {},
        'error_message': error_message
    }
    
    dialog = DjangoErrorViewer(parent, error_data)
    return dialog.exec_()

