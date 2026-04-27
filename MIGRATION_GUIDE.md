# 🔄 Guide de Migration - Ancien Code vers Nouveau Système d'Auth

## 📌 Objectif

Si vous aviez du code qui utilisait l'**ancienne authentification** (QInputDialog basique), ce guide vous montre comment **le mettre à jour** vers le **nouveau système**.

---

## ❌ Avant (Ancien Code)

```python
# mrv_teraka.py
def authenticate(self):
    """Authentification basique avec QInputDialog"""
    # 1️⃣ Demander l'email
    username, ok = QInputDialog.getText(
        self.iface.mainWindow(),
        self.tr(u'Connexion'), 
        self.tr(u'Email / Utilisateur')
    )
    if not ok or not username: 
        return

    # 2️⃣ Demander le mot de passe
    password, ok = QInputDialog.getText(
        self.iface.mainWindow(),
        self.tr(u'Connexion'), 
        self.tr(u'Mot de passe'), 
        QLineEdit.Password
    )
    if not ok or not password: 
        return

    # 3️⃣ Envoyer à l'API
    try:
        authenticator = PostgRESTAuthenticator(self.api_base_url, mode=self.postgrest_mode)
        token = authenticator.authenticate(username, password)

        # 4️⃣ Créer le client
        self.postgrest = PostgREST(self.api_base_url, mode=self.postgrest_mode)
        self.postgrest.set_auth_token(token)

        # ❌ PROBLÈME: Token en mémoire seulement! 
        # Perdu au redémarrage!
        
        QMessageBox.information(...)
    except Exception as exc:
        QMessageBox.critical(...)

def check_api_auth(self):
    """Vérification basique du jeton"""
    # ❌ PROBLÈME: Impossible de savoir si connecté encore
    if not self.postgrest or not self.postgrest.jwt_token:
        QMessageBox.warning(...)
        return False
    return True
```

**Problèmes**:
- ❌ Deux QInputDialog séparées (peu fluide)
- ❌ Jeton stocké seulement en mémoire
- ❌ Perte du jeton à chaque redémarrage
- ❌ Aucun indicateur d'état
- ❌ Pas de mémorisation d'identifiant
- ❌ Pas de mode API sélectionnable
- ❌ QInputDialog peu professionnel

---

## ✅ Après (Nouveau Code)

```python
# mrv_teraka.py
from .auth_dialog import AuthDialog
from .token_manager import TokenManager

class MrvTeraka:
    def __init__(self, iface):
        # ... autres inits ...
        
        # ✅ Nouveau: TokenManager pour persistance
        self.token_manager = TokenManager()
        self.current_username = None
        self.auth_action = None

    def initGui(self):
        """Initialise l'interface"""
        # ✅ Nouveau: Bouton dynamique
        self.auth_action = self.add_action(
            ':/plugins/mrv_teraka/login_icon.svg',
            text=self.tr(u'Connexion'),
            callback=self.show_auth_dialog,
            parent=self.iface.mainWindow()
        )
        
        # Autres actions...
        
        # ✅ Nouveau: Charger jeton au démarrage
        self.load_saved_token()

    def show_auth_dialog(self):
        """Affiche un dialog professionnel"""
        # ✅ Nouveau: Dialog Qt personnalisé
        auth_dialog = AuthDialog(
            parent=self.iface.mainWindow(),
            api_modes={
                'Django': PostgRESTMode.DJANGO,
                'PostgREST (Standalone)': PostgRESTMode.STANDALONE
            }
        )
        
        if auth_dialog.exec_() == AuthDialog.Accepted:
            # ✅ Tout au même endroit! (password, url, mode, etc.)
            credentials = auth_dialog.get_credentials()
            self.authenticate_with_credentials(credentials, auth_dialog)

    def authenticate_with_credentials(self, credentials, dialog=None):
        """Authentification complète et sauvegarde"""
        username = credentials['username']
        password = credentials['password']
        self.api_base_url = credentials['url']
        
        if credentials['mode']:
            mode_map = {
                'Django': PostgRESTMode.DJANGO,
                'PostgREST (Standalone)': PostgRESTMode.STANDALONE
            }
            self.postgrest_mode = mode_map.get(credentials['mode'], PostgRESTMode.DJANGO)
        
        try:
            # Authentification
            authenticator = PostgRESTAuthenticator(self.api_base_url, mode=self.postgrest_mode)
            token = authenticator.authenticate(username, password)

            # Client API
            self.postgrest = PostgREST(self.api_base_url, mode=self.postgrest_mode)
            self.postgrest.set_auth_token(token)

            # ✅ Nouveau: Sauvegarde du jeton dans QSettings!
            self.token_manager.save_token(token, self.api_base_url, self.postgrest_mode.value)
            self.current_username = username

            # Mémorisation des paramètres
            if credentials['remember']:
                settings = QSettings('iTeraka', 'MrvTeraka')
                settings.setValue('auth/last_username', username)

            # ✅ Nouveau: Mise à jour de l'interface
            self.update_auth_ui()
            
            if self.dockwidget:
                self.dockwidget.set_authenticated(username, self.api_base_url)

            QMessageBox.information(...)

        except Exception as exc:
            QMessageBox.critical(...)

    def load_saved_token(self):
        """Charge le jeton sauvegardé au démarrage"""
        # ✅ Nouveau: Chargement auto!
        token, api_url, mode = self.token_manager.load_token()
        
        if token and api_url:
            # ✅ Jeton valide: reconnecter automatiquement
            self.postgrest = PostgREST(api_url, mode=PostgRESTMode[mode.upper()] if mode else PostgRESTMode.DJANGO)
            self.postgrest.set_auth_token(token)
            self.api_base_url = api_url
            
            settings = QSettings('iTeraka', 'MrvTeraka')
            self.current_username = settings.value('auth/last_username', 'Utilisateur')
            
            self.update_auth_ui()

    def update_auth_ui(self):
        """Met à jour l'interface pour afficher l'état connecté"""
        # ✅ Nouveau: Bouton change dynamiquement
        if self.auth_action:
            self.auth_action.setText(self.tr(u'Déconnecter'))
            self.auth_action.triggered.disconnect()
            self.auth_action.triggered.connect(self.logout)
        
        if self.dockwidget:
            self.dockwidget.set_authenticated(self.current_username, self.api_base_url)

    def logout(self):
        """Déconnexion sécurisée"""
        # ✅ Nouveau: Déconnexion complète avec suppression du jeton
        reply = QMessageBox.question(...)
        
        if reply == QMessageBox.Yes:
            # Supprimer le jeton
            self.token_manager.clear_token()
            self.postgrest = None
            self.current_username = None
            
            # Réinitialiser interface
            if self.auth_action:
                self.auth_action.setText(self.tr(u'Connexion'))
                self.auth_action.triggered.disconnect()
                self.auth_action.triggered.connect(self.show_auth_dialog)
            
            if self.dockwidget:
                self.dockwidget.set_unauthenticated()
            
            QMessageBox.information(...)

    def check_api_auth(self):
        """Vérification améliorée du jeton"""
        # ✅ Nouveau: Vérification de validité AND expiration
        if not self.postgrest or not self.token_manager.is_token_valid():
            QMessageBox.warning(...)
            self.show_auth_dialog()  # ✅ Relancer le dialog
            return False
        return True
```

**Améliorations**:
- ✅ Un seul dialog professionnel (AuthDialog)
- ✅ Jeton sauvegardé dans QSettings
- ✅ Rechargement automatique au démarrage
- ✅ Indicateurs d'état visuels
- ✅ Mémorisation d'identifiants
- ✅ Modes API sélectionnables
- ✅ Déconnexion sécurisée
- ✅ Gestion d'expiration
- ✅ Interface moderne

---

## 🔄 Étapes de Migration

### Étape 1: Ajouter les Imports

**Avant**:
```python
from qgis.PyQt.QtWidgets import QInputDialog, QLineEdit
# ... autres imports
```

**Après**:
```python
from qgis.PyQt.QtWidgets import QInputDialog, QLineEdit
from .auth_dialog import AuthDialog
from .token_manager import TokenManager
# ... autres imports
```

### Étape 2: Modifier __init__()

**Avant**:
```python
def __init__(self, iface):
    self.iface = iface
    self.postgrest = None
    # ...
```

**Après**:
```python
def __init__(self, iface):
    self.iface = iface
    self.postgrest = None
    self.token_manager = TokenManager()
    self.current_username = None
    self.auth_action = None
    # ...
```

### Étape 3: Modifier initGui()

**Avant**:
```python
def initGui(self):
    self.add_action(':/plugins/icon.png', ...)
    self.add_action(':/plugins/login.svg', callback=self.authenticate, ...)
```

**Après**:
```python
def initGui(self):
    self.auth_action = self.add_action(
        ':/plugins/login.svg',
        text=self.tr(u'Connexion'),
        callback=self.show_auth_dialog,
        parent=self.iface.mainWindow()
    )
    self.add_action(':/plugins/icon.png', ...)
    self.load_saved_token()
```

### Étape 4: Remplacer authenticate()

**Avant**:
```python
def authenticate(self):
    username, ok = QInputDialog.getText(...)
    # ... 2 dialogs ...
    self.postgrest.set_auth_token(token)
```

**Après**:
```python
def show_auth_dialog(self):
    auth_dialog = AuthDialog(...)
    if auth_dialog.exec_() == AuthDialog.Accepted:
        credentials = auth_dialog.get_credentials()
        self.authenticate_with_credentials(credentials, auth_dialog)

def authenticate_with_credentials(self, credentials, dialog=None):
    # ... code complet d'authentification voir ci-dessus ...
```

### Étape 5: Ajouter les Nouvelles Méthodes

```python
def load_saved_token(self):
    # ... voir ci-dessus ...

def update_auth_ui(self):
    # ... voir ci-dessus ...

def logout(self):
    # ... voir ci-dessus ...
```

### Étape 6: Améliorer check_api_auth()

**Avant**:
```python
def check_api_auth(self):
    if not self.postgrest or not self.postgrest.jwt_token:
        QMessageBox.warning(...)
        return False
    return True
```

**Après**:
```python
def check_api_auth(self):
    if not self.postgrest or not self.token_manager.is_token_valid():
        QMessageBox.warning(...)
        self.show_auth_dialog()
        return False
    return True
```

### Étape 7: Modifier run()

**Avant**:
```python
def run(self):
    if not self.pluginIsActive:
        self.pluginIsActive = True
        if self.dockwidget is None:
            self.dockwidget = MrvTerakaDockWidget(self)
        self.dockwidget.closingPlugin.connect(self.onClosePlugin)
        self.iface.addDockWidget(...)
        self.dockwidget.show()
```

**Après**:
```python
def run(self):
    if not self.pluginIsActive:
        self.pluginIsActive = True
        if self.dockwidget is None:
            self.dockwidget = MrvTerakaDockWidget(self)
            self.dockwidget.closingPlugin.connect(self.onClosePlugin)
            self.dockwidget.logout_requested.connect(self.logout)  # ✅ Nouveau
        
        if self.token_manager.is_token_valid():
            self.dockwidget.set_authenticated(self.current_username, self.api_base_url)
        else:
            self.dockwidget.set_unauthenticated()
        
        self.iface.addDockWidget(...)
        self.dockwidget.show()
```

### Étape 8: Modifier mrv_teraka_dockwidget.py

**Avant**:
```python
class MrvTerakaDockWidget(QtWidgets.QDockWidget, FORM_CLASS):
    closingPlugin = pyqtSignal()

    def __init__(self, plugin=None, parent=None):
        super().__init__(parent)
        self.plugin = plugin
        self.setupUi(self)
        self.setup_connections()

    def setup_connections(self):
        if not self.plugin:
            return
        try:
            self.compareButton.clicked.connect(...)
            self.loadDbButton.clicked.connect(...)
            self.prepareMerginButton.clicked.connect(...)
        except AttributeError:
            pass
```

**Après**:
```python
class MrvTerakaDockWidget(QtWidgets.QDockWidget, FORM_CLASS):
    closingPlugin = pyqtSignal()
    logout_requested = pyqtSignal()  # ✅ Nouveau signal

    def __init__(self, plugin=None, parent=None):
        super().__init__(parent)
        self.plugin = plugin
        self.setupUi(self)
        self.setup_auth_ui()  # ✅ Nouveau
        self.setup_connections()

    def setup_auth_ui(self):
        """Ajoute la barre d'authentification"""
        # ... voir mrv_teraka_dockwidget.py ...

    def setup_connections(self):
        if not self.plugin:
            return
        try:
            self.compareButton.clicked.connect(...)
            self.loadDbButton.clicked.connect(...)
            self.prepareMerginButton.clicked.connect(...)
            self.logout_button.clicked.connect(self.on_logout_clicked)  # ✅ Nouveau
        except AttributeError:
            pass

    def set_authenticated(self, username=None, api_url=None):
        """✅ Nouveau: Afficher état connecté"""
        # ... voir mrv_teraka_dockwidget.py ...

    def set_unauthenticated(self):
        """✅ Nouveau: Afficher état déconnecté"""
        # ... voir mrv_teraka_dockwidget.py ...
```

---

## 📝 Checklist de Migration

- [ ] Ajouter imports `AuthDialog`, `TokenManager`
- [ ] Modifier `__init__()` pour ajouter `token_manager`
- [ ] Modifier `initGui()` pour ajouter `load_saved_token()`
- [ ] Remplacer `authenticate()` par `show_auth_dialog()`
- [ ] Ajouter `authenticate_with_credentials()`
- [ ] Ajouter `load_saved_token()`
- [ ] Ajouter `update_auth_ui()`
- [ ] Ajouter `logout()`
- [ ] Améliorer `check_api_auth()`
- [ ] Modifier `run()` pour les signaux dock
- [ ] Modifier `mrv_teraka_dockwidget.py` (barre auth)
- [ ] Tester UI complète (connexion, déconnexion, persit.)
- [ ] Tester la sauvegarde/chargement du jeton
- [ ] Tester les erreurs et edge cases

---

## 🧪 Tests de Vérification

### Test 1: Première Connexion

```
1. Lancez QGIS
2. Voir [🔐 Connexion]
3. Cliquez le bouton
4. Remplissez le dialog (email, pwd, url, mode)
5. Voir message "Authentification réussie"
6. Voir [🔓 Déconnecter] (le bouton a changé!)
7. Voir "● Connecté" dans la dock ✅
```

### Test 2: Reconnexion Auto

```
1. Fermez QGIS
2. Relancez QGIS
3. Voir [🔓 Déconnecter] (déjà connecté!)
4. Voir "● Connecté" dans la dock
5. Pas besoin de saisir identifiant! ✅
```

### Test 3: Déconnexion

```
1. Connecté
2. Cliquez [🔓 Déconnecter]
3. Confirmer dialog
4. Voir [🔐 Connexion] (bouton réinitialisé)
5. Voir "● Déconnecté" dans la dock
6. Boutons d'action désactivés ✅
```

### Test 4: Actions API

```
1. Connecté
2. Entrez endpoint, cliquez "Charger DB"
3. Voir les données chargées ✅
4. Déconnectez-vous
5. Cliquez "Charger DB"
6. Voir dialog auth relancé ✅
```

---

## 🆘 Dépannage Migration

### Problem: Import error `AuthDialog`

**Cause**: Module pas à côté de `mrv_teraka.py`

**Solution**:
```python
# Vérifiez que auth_dialog.py est dans le même dossier
# C:\Users\johro\AppData\Roaming\QGIS\...\plugins\mrv_teraka\
# ├── mrv_teraka.py
# ├── auth_dialog.py  ← Doit exister
# └── token_manager.py ← Doit exister
```

### Problem: QSettings не работает

**Cause**: Mauvais organization/app name

**Solution**:
```python
# Utilisez la même organisation
token_manager = TokenManager('iTeraka', 'MrvTeraka')
```

### Problem: Dock widget ne se met pas à jour

**Cause**: `setup_auth_ui()` pas appelée

**Solution**:
```python
def __init__(self, ...):
    ...
    self.setupUi(self)
    self.setup_auth_ui()  # ← Ajouter cette ligne
    self.setup_connections()
```

---

# 🎉 Migration Réussie!

Une fois les étapes complétées, vous avez:

✅ Un système d'authentification moderne et professionnel
✅ Persistance du jeton entre les sessions
✅ Interface dynamique et intuitive
✅ Code bien structuré et maintenable
✅ Support des modes API multiples
✅ Gestion complète des erreurs

Bon travail! 🚀

