# -*- coding: utf-8 -*-
"""
Guide d'Intégration - Django Error Viewer

Montre comment intégrer le Django Error Viewer dans les fichiers existants
du plugin MrvTeraka (mrv_teraka.py, auth_dialog.py, etc.)
"""

# ============================================================================
# INTÉGRATION 1: Dans auth_dialog.py - Gestion de connexion
# ============================================================================

INTEGRATION_AUTH_DIALOG = """
# Dans auth_dialog.py

from django_error_viewer import show_django_error
from postgrest_client import PostgRESTAuthenticator, PostgRESTMode

class AuthenticationDialog(QDialog):
    def authenticate(self):
        \"\"\"Authentifier l'utilisateur\"\"\"
        username = self.username_input.text()
        password = self.password_input.text()
        
        try:
            authenticator = PostgRESTAuthenticator(
                self.api_url,
                mode=PostgRESTMode.DJANGO
            )
            token = authenticator.authenticate(username, password)
            self.token_obtained.emit(token)
            
        except RuntimeError as e:
            # Extraire le code d'erreur et afficher avec rendu HTML
            import re, urllib.error
            match = re.search(r'HTTP (\\d+)', str(e))
            if match and match.group(1) in ['401', '403', '500']:
                # L'erreur Django est déjà affichée
                show_django_error(
                    self,
                    int(match.group(1)),
                    'Authentication Failed',
                    str(e),
                    url=self.api_url + '/api/login/'
                )
            else:
                QMessageBox.critical(self, "Erreur", str(e))
"""

# ============================================================================
# INTÉGRATION 2: Dans mrv_teraka.py - Chargement des donnees
# ============================================================================

INTEGRATION_MRV_TERAKA = """
# Dans mrv_teraka.py

from postgrest_client import PostgREST, PostgRESTMode
from django_error_viewer import show_django_error

class MrvTeraka(QMainWindow):
    def load_database_data(self):
        \"\"\"Charge les données de la base avec gestion d'erreur Django\"\"\"
        
        try:
            postgrest = PostgREST(self.api_url, mode=PostgRESTMode.DJANGO)
            postgrest.set_auth_token(self.jwt_token)
            
            # Marquer le début du chargement
            self.progress_bar.setValue(10)
            self.status_label.setText("Chargement des données...")
            
            # Charger les données - affiche erreur Django si elle survient
            data = postgrest.select_with_ui(
                'communes',
                limit=1000
            )
            
            self.progress_bar.setValue(100)
            self.status_label.setText(f"✅ {len(data)} communes chargées")
            
            return data
            
        except RuntimeError as e:
            # L'erreur Django est déjà affichée par select_with_ui()
            self.progress_bar.setValue(0)
            self.status_label.setText("❌ Erreur lors du chargement")
            return None
"""

# ============================================================================
# INTÉGRATION 3: Dans mergin_workflow_manager.py - Synchronisation
# ============================================================================

INTEGRATION_MERGIN_WORKFLOW = """
# Dans mergin_workflow_manager.py

from postgrest_client import PostgREST, PostgRESTMode

class MerginWorkflowManager:
    def sync_data_with_api(self, project_id, data):
        \"\"\"Synchronise les données collectées avec l'API\"\"\"
        
        postgrest = PostgREST(self.api_url, mode=PostgRESTMode.DJANGO)
        postgrest.set_auth_token(self.jwt_token)
        
        results = {
            'inserted': 0,
            'updated': 0,
            'deleted': 0,
            'errors': []
        }
        
        try:
            # Insérer les nouveaux enregistrements
            # L'erreur Django s'affiche automatiquement si elle survient
            new_records = [r for r in data if r.get('_is_new')]
            if new_records:
                result = postgrest.insert_with_ui('communes', new_records)
                results['inserted'] = len(result)
            
            # Mettre à jour les enregistrements modifiés
            updated_records = [r for r in data if r.get('_is_modified')]
            for record in updated_records:
                record_id = record.get('id')
                try:
                    postgrest.update_with_ui(
                        'communes',
                        record,
                        {'id': f'eq.{record_id}'}
                    )
                    results['updated'] += 1
                except RuntimeError as e:
                    results['errors'].append(f"Update failed for {record_id}: {e}")
            
            self.log_sync_results(project_id, results)
            return results
            
        except RuntimeError:
            # Erreur affichée par les méthodes *_with_ui()
            results['errors'].append("Synchronisation échouée")
            return results
"""

# ============================================================================
# INTÉGRATION 4: Dans validation_dialog.py - Amélioration
# ============================================================================

INTEGRATION_VALIDATION_DIALOG = """
# Dans validation_dialog.py

from postgrest_client import PostgREST, PostgRESTMode

class DataValidationDialog(QDialog):
    def __init__(self, parent=None, postgrest=None, collected_data=None, original_data=None):
        super().__init__(parent)
        self.postgrest = postgrest
        self.collected_data = collected_data or []
        self.original_data = original_data or []
        
    @classmethod
    def from_api(cls, parent=None, postgrest=None, project_name=None):
        \"\"\"Créer un dialog de validation en chargeant depuis l'API\"\"\"
        
        if not postgrest:
            return None
        
        try:
            # Charger les données - erreur Django affichée automatiquement
            collected = postgrest.select_with_ui('communes')
            original = postgrest.select_with_ui('communes_original')
            
            dialog = cls(
                parent=parent,
                postgrest=postgrest,
                collected_data=collected,
                original_data=original
            )
            
            return dialog
            
        except RuntimeError:
            # Erreur affichée par select_with_ui()
            return None
    
    def accept(self):
        \"\"\"Valider et fusionner les données\"\"\"
        try:
            # Fusionner - erreur Django affichée si elle survient
            result = self.postgrest.insert_with_ui(
                'communes',
                self.validated_data
            )
            
            QMessageBox.information(
                self,
                "Succès",
                f"✅ {len(result)} enregistrements fusionnés"
            )
            
            super().accept()
            
        except RuntimeError:
            # Erreur affichée par insert_with_ui()
            QMessageBox.warning(self, "Erreur", "Fusion échouée")
"""

# ============================================================================
# INTÉGRATION 5: Dans token_manager.py - Validation de token
# ============================================================================

INTEGRATION_TOKEN_MANAGER = """
# Dans token_manager.py

from postgrest_client import PostgREST, PostgRESTMode
from django_error_viewer import show_django_error

class TokenManager:
    def validate_token(self, token):
        \"\"\"Valide un token JWT\"\"\"
        
        postgrest = PostgREST(self.api_url, mode=PostgRESTMode.DJANGO)
        postgrest.set_auth_token(token)
        
        try:
            # Essayer une requête simple - affiche erreur Django si token invalide
            result = postgrest.select_with_ui('communes', limit=1)
            
            # Token valide
            self.save_token(token)
            return True
            
        except RuntimeError as e:
            # Token rejeté - erreur affichée avec rendu HTML
            if '401' in str(e):
                print("Token expiré - Nouvelle authentification requise")
            return False
"""

# ============================================================================
# INTÉGRATION 6: Wrapper Global - Utiliser partout
# ============================================================================

DEFAULT_INTEGRATION_WRAPPER = """
# À ajouter dans __init__.py ou un module central

from postgrest_client import PostgREST, PostgRESTMode

class APIClient:
    \"\"\"Client API global avec gestion d'erreurs Django\"\"\"
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.postgrest = None
        self._jwt_token = None
        self._api_url = None
        self._initialized = True
    
    def configure(self, api_url, mode=PostgRESTMode.DJANGO):
        \"\"\"Configure le client API\"\"\"
        self._api_url = api_url
        self.postgrest = PostgREST(api_url, mode=mode)
    
    def set_token(self, token):
        \"\"\"Définit le token JWT\"\"\"
        self._jwt_token = token
        if self.postgrest:
            self.postgrest.set_auth_token(token)
    
    def select(self, table, **kwargs):
        \"\"\"Requête SELECT avec affichage UI des erreurs Django\"\"\"
        if not self.postgrest:
            raise RuntimeError("API client not configured")
        return self.postgrest.select_with_ui(table, **kwargs)
    
    def insert(self, table, data):
        \"\"\"Requête INSERT avec affichage UI des erreurs Django\"\"\"
        if not self.postgrest:
            raise RuntimeError("API client not configured")
        return self.postgrest.insert_with_ui(table, data)
    
    def update(self, table, data, filters):
        \"\"\"Requête UPDATE avec affichage UI des erreurs Django\"\"\"
        if not self.postgrest:
            raise RuntimeError("API client not configured")
        return self.postgrest.update_with_ui(table, data, filters)
    
    def delete(self, table, filters):
        \"\"\"Requête DELETE avec affichage UI des erreurs Django\"\"\"
        if not self.postgrest:
            raise RuntimeError("API client not configured")
        return self.postgrest.delete_with_ui(table, filters)


# Utilisation partout:
# api = APIClient()
# api.configure('http://localhost:8000')
# api.set_token(token)
# data = api.select('communes')  # Erreur Django affichée automatiquement
"""

# ============================================================================
# Snippet de Copier-Coller: Utiliser partout
# ============================================================================

COPY_PASTE_SNIPPET = """
# Ajouter à n'importe quel fichier Python pour afficher erreurs Django:

from postgrest_client import PostgREST, PostgRESTMode

postgrest = PostgREST("http://localhost:8000", mode=PostgRESTMode.DJANGO)
postgrest.set_auth_token(token)

try:
    data = postgrest.select_with_ui('communes')  # ← Erreur Django affichée !
except RuntimeError:
    pass
"""

# ============================================================================
# Configuration pour mrv_teraka.py
# ============================================================================

MRV_TERAKA_SETUP = """
# Au démarrage du plugin, dans initGui():

def initGui(self):
    # ... code existant ...
    
    # Importer les modules d'erreur Django
    try:
        from django_error_viewer import DjangoErrorViewer
        self.error_viewer_available = True
    except ImportError:
        self.error_viewer_available = False
        print("⚠️ Django Error Viewer non disponible")
    
    # Configure le client PostgREST
    self.setup_postgrest_client()

def setup_postgrest_client(self):
    \"\"\"Configure le client PostgREST avec support UI\"\"\"
    from postgrest_client import PostgREST, PostgRESTMode
    
    self.postgrest = PostgREST(
        self.api_url,
        mode=PostgRESTMode.DJANGO
    )
    
    # Charger le token JWT s'il existe
    from token_manager import TokenManager
    mgr = TokenManager()
    token = mgr.get_stored_token()
    
    if token:
        self.postgrest.set_auth_token(token)
"""

# ============================================================================
# Tests d'Intégration
# ============================================================================

def print_all_integrations():
    """Affiche tous les guides d'intégration"""
    
    integrations = {
        "1. auth_dialog.py": INTEGRATION_AUTH_DIALOG,
        "2. mrv_teraka.py": INTEGRATION_MRV_TERAKA,
        "3. mergin_workflow_manager.py": INTEGRATION_MERGIN_WORKFLOW,
        "4. validation_dialog.py": INTEGRATION_VALIDATION_DIALOG,
        "5. token_manager.py": INTEGRATION_TOKEN_MANAGER,
        "6. Wrapper Global": DEFAULT_INTEGRATION_WRAPPER,
        "Setup Plugin": MRV_TERAKA_SETUP,
    }
    
    for name, code in integrations.items():
        print(f"\n{'='*80}")
        print(f"INTÉGRATION: {name}")
        print('='*80)
        print(code)


if __name__ == "__main__":
    print("\n🚀 GUIDES D'INTÉGRATION - Django Error Viewer\n")
    print_all_integrations()
    
    print(f"\n{'='*80}")
    print("📋 COPIER-COLLER RAPIDE")
    print('='*80)
    print(COPY_PASTE_SNIPPET)
    
    print(f"\n{'='*80}")
    print("✅ Intégration Complète!")
    print('='*80)
    print("""
    Pour intégrer le Django Error Viewer:
    
    1. Copier les snippets ci-dessus
    2. Remplacer les appels PostgREST par les versions *_with_ui()
    3. Les erreurs Django s'affichent automatiquement avec rendu HTML!
    
    Exemple:
    
    # Avant
    data = postgrest.select('communes')
    
    # Après
    data = postgrest.select_with_ui('communes')  ← Automatique !
    """)

