# Guide Complet d'Authentification MrvTeraka

## Vue d'ensemble

Le système d'authentification du plugin MrvTeraka offre:

1. **Formulaire d'authentification** professionnel et ergonomique
2. **Stockage sécurisé** du jeton JWT dans QSettings
3. **Indicateur visuel** dans la barre d'outils et la dock widget
4. **Chargement automatique** du jeton au démarrage
5. **Gestion des sessions** avec déconnexion

## Architecture

```
┌─────────────────────────────────────────────────────┐
│          Interface Utilisateur (QGIS)               │
├─────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────┐   │
│  │  Barre d'outils                              │   │
│  │  [iTeraka] [Connexion/Déconnecter]          │   │
│  └──────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────┐   │
│  │  Dock Widget MrvTeraka                       │   │
│  │  ┌──────────────────────────────────────────┐│   │
│  │  │ Barre Auth: ● Connecté / Déconnecter   ││   │
│  │  │ user@example.com @ http://localhost:8000││   │
│  │  ├──────────────────────────────────────────┤│   │
│  │  │ [Comparaison & Mergin]                  ││   │
│  │  │ - Comparer / Charger DB / Préparer     ││   │
│  │  └──────────────────────────────────────────┘│   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
         │
         ├──→ AuthDialog (auth_dialog.py)
         │    ├─ Formulaire de connexion
         │    ├─ Sélection du mode (Django/Standalone)
         │    └─ Mémorisation des identifiants
         │
         ├──→ TokenManager (token_manager.py)
         │    ├─ Sauvegarde du jeton dans QSettings
         │    ├─ Validation et expiration
         │    └─ Chiffrement optionnel
         │
         └──→ PostgREST Client (postgrest_client.py)
              ├─ PostgRESTAuthenticator (connexion)
              └─ PostgREST (requêtes API)
```

## Fichiers créés/modifiés

### 1. `auth_dialog.py` - Formulaire d'authentification

Affiche un formulaire professionnel avec:
- Sélection du mode API (Django / PostgREST Standalone)
- Saisie de l'URL de base
- Champs email/username et mot de passe
- Toggle pour afficher/masquer le mot de passe
- Mémorisation des identifiants
- Sauvegarde des paramètres

**Utilisation:**
```python
auth_dialog = AuthDialog(
    parent=self.iface.mainWindow(),
    api_modes={
        'Django': PostgRESTMode.DJANGO,
        'PostgREST (Standalone)': PostgRESTMode.STANDALONE
    }
)

if auth_dialog.exec_() == AuthDialog.Accepted:
    credentials = auth_dialog.get_credentials()
    # username, password, url, mode, remember
```

### 2. `token_manager.py` - Gestionnaire de jeton JWT

Gère le cycle de vie du jeton:
- **save_token()**: Sauvegarde le jeton avec métadonnées dans QSettings
- **load_token()**: Charge le jeton sauvegardé
- **is_token_valid()**: Vérifie la validité et l'expiration
- **clear_token()**: Supprime le jeton
- **get_token_info()**: Retourne les informations du jeton
- **refresh_token_expiry()**: Rafraîchit la date d'expiration

**Localisation des données:**
- Windows: `HKEY_CURRENT_USER\Software\iTeraka\MrvTeraka`
- Linux: `~/.config/iTeraka/MrvTeraka.conf`
- macOS: `~/Library/Preferences/com.iTeraka.MrvTeraka.plist`

**Migration du code existant:**

Avant:
```python
self.jwt_token = token
self.api_headers = {...}
```

Après:
```python
self.token_manager.save_token(token, api_url, mode)
# Le jeton est sauvegardé automatiquement
```

### 3. `mrv_teraka_dockwidget.py` - Dock widget améliorée

Ajout d'une barre d'authentification avec:
- **Status Label**: Affiche "● Connecté" (vert) ou "● Déconnecté" (rouge)
- **User Label**: Affiche "user@example.com @ http://localhost:8000"
- **Logout Button**: Bouton de déconnexion

Méthodes:
- `set_authenticated(username, api_url)`: Affiche l'état connecté
- `set_unauthenticated()`: Affiche l'état déconnecté

### 4. `mrv_teraka.py` - Plugin principal

Méthodes d'authentification nouvelles/modifiées:

#### `show_auth_dialog()`
Affiche le formulaire d'authentification avec les modes disponibles.

#### `authenticate_with_credentials(credentials, dialog)`
Traite l'authentification:
1. Récupère les identifiants
2. Appelle PostgRESTAuthenticator
3. Initialise PostgREST Client
4. Sauvegarde le jeton via TokenManager
5. Met à jour l'interface

#### `load_saved_token()`
Appelée au démarrage pour charger automatiquement le jeton.

#### `update_auth_ui()`
Met à jour l'interface:
- Barre d'outils: Change le bouton de "Connexion" à "Déconnecter"
- Dock widget: Affiche l'utilisateur et le statut

#### `logout()`
Déconnecte l'utilisateur:
1. Demande confirmation
2. Supprime le jeton
3. Réinitialise l'interface

#### `check_api_auth()`
Vérifie si l'utilisateur est authentifié avant les actions API.

## Flux d'utilisation

### 1. Démarrage du plugin

```
QGIS lance le plugin
    ↓
__init__() crée TokenManager
    ↓
initGui() crée les boutons d'action
    ↓
load_saved_token() charge le jeton sauvegardé
    ↓
Si jeton valide → update_auth_ui() affiche "Déconnecter"
Si pas de jeton → affiche "Connexion"
```

### 2. Première connexion

```
Utilisateur clique "Connexion" dans la barre d'outils
    ↓
show_auth_dialog() affiche le formulaire
    ↓
Utilisateur remplit les champs et clique "Se connecter"
    ↓
authenticate_with_credentials():
    - PostgRESTAuthenticator.authenticate() ← récupère le jeton
    - PostgREST.set_auth_token() ← configure le client
    - TokenManager.save_token() ← sauvegarde le jeton
    - update_auth_ui() ← met à jour la barre d'outils
    ↓
Dock widget affiche "● Connecté - user@example.com"
Boutons d'action deviennent actifs
```

### 3. Reconnexion automatique

```
QGIS redémarre
    ↓
load_saved_token():
    - TokenManager.load_token() ← charge le jeton sauvegardé
    - Vérifie l'expiration
    - Si valide → crée PostgREST Client avec le jeton
    ↓
update_auth_ui() affiche "Déconnecter"
Dock widget affiche "● Connecté"
```

### 4. Déconnexion

```
Utilisateur clique "Déconnecter" dans la barre d'outils
    ↓
Affiche une fenêtre de confirmation
    ↓
logout():
    - TokenManager.clear_token() ← supprime le jeton
    - self.postgrest = None
    - Réinitialise les boutons
    ↓
Dock widget affiche "● Déconnecté"
Boutons d'action deviennent inactifs
```

## Configuration QSettings

Les données sont stockées dans:

```
[auth]
username=user@example.com          # Dernier utilisateur connecté
url=http://localhost:8000          # URL API
remember=true                       # Mémorise les identifiants

[token]
jwt=eyJ0eXAiOiJKV1QiLCJhbGc...      # Jeton JWT
url=http://localhost:8000           # URL de l'API du jeton
mode=django                         # Mode (django ou standalone)
expiry=1234567890.0                 # Timestamp d'expiration (Unix)
```

## Validation du jeton

Le jeton est considéré valide si:

1. **Présent**: `self.postgrest` est défini
2. **Non expiré**: `time.time() < token_expiry`
3. **Contient les headers JWT**: Authorization: Bearer ...

## Gestion de l'expiration

Par défaut, les jetons expirent après 24 heures.

Pour modifier:
```python
# Sauvegarder avec expiration custom (en secondes)
self.token_manager.save_token(token, api_url, mode, expires_in=7200)  # 2 heures

# Ou rafraîchir l'expiration
self.token_manager.refresh_token_expiry(expires_in=86400)  # 24h
```

## Sécurité

### Stockage du jeton

Le jeton est stocké dans **QSettings** qui utilise:

- **Windows**: Registry (HKEY_CURRENT_USER)
- **Linux**: Fichier de configuration `~/.config/...`
- **macOS**: Preferences plist

**Note:** Pour une sécurité renforcée, vous pouvez chiffrer le jeton en modifiant `TokenManager.save_token()`.

### Bonnes pratiques

1. **Ne pas afficher le jeton complet**:
   ```python
   # ❌ Incorrect
   print(token)
   
   # ✅ Correct
   print(token[:20] + '...')
   ```

2. **Effacer le jeton à la déconnexion**:
   ```python
   self.token_manager.clear_token()
   ```

3. **Valider avant les actions**:
   ```python
   if not self.check_api_auth():
       return
   ```

## Dépannage

### "Jeton expiré"

**Symptôme**: Erreur 401 Unauthorized après une période d'inactivité

**Solution**: 
```python
# Augmenter la durée d'expiration
self.token_manager.refresh_token_expiry(expires_in=86400 * 7)  # 7 jours
```

### "Les identifiants ne sont pas mémorisés"

**Symptôme**: Le champ email/username reste vide après reconnexion

**Cause**: L'utilisateur n'a pas coché "Mémoriser les identifiants"

**Solution**: Cocher la case lors de la connexion

### "Jeton chargé mais API retourne 401"

**Symptôme**: Le jeton a l'air valide mais les requêtes échouent

**Cause**: Le jeton a expiré côté serveur

**Solution**:
```python
# Forcer une nouvelle authentification
self.token_manager.clear_token()
self.show_auth_dialog()
```

## Exemple d'intégration personnalisée

Si vous voulez ajouter votre propre logique d'authentification:

```python
class CustomMrvTeraka(MrvTeraka):
    def authenticate_with_ldap(self, username, password):
        """Authentification via LDAP au lieu de l'API"""
        import ldap
        
        try:
            # Valider via LDAP
            conn = ldap.initialize('ldap://company.com')
            conn.simple_bind_s(f'uid={username},dc=company,dc=com', password)
            
            # Récupérer un jeton de l'API avec le username
            token = ... # logique personnalisée
            
            # Utiliser le flux standard
            credentials = {
                'username': username,
                'password': password,
                'url': self.api_base_url,
                'mode': 'Django',
                'remember': True
            }
            self.authenticate_with_credentials(credentials)
            
        except Exception as e:
            QMessageBox.critical(self.iface.mainWindow(), "LDAP Error", str(e))
```

## Résumé

| Aspect | Avant | Après |
|--------|-------|-------|
| **Authentification** | QInputDialog basique | Formulaire professionnel |
| **Stockage du jeton** | Variable `self.jwt_token` | TokenManager + QSettings |
| **Gestion de l'expiration** | Aucune | Automatique avec validation |
| **Persistance du jeton** | Aucune (perte à redémarrage) | Sauvegardé et rechargé |
| **Interface connectée** | Aucun indicateur | Barre d'auth + statut visuel |
| **Déconnexion** | Non implémentée | Bouton + suppression sécurisée |

