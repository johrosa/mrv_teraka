# 📋 Résumé des Améliorations d'Authentification

## ✨ Nouveautés

### 1. **Formulaire d'Authentification Professionnel**
- ✅ Interface Qt moderne et intuitive
- ✅ Sélection du mode API (Django ou PostgREST Standalone)
- ✅ Saisie de l'URL API personnalisable
- ✅ Fields: Email/Username, Mot de passe
- ✅ Toggle pour afficher/masquer le mot de passe
- ✅ Mémorisation des identifiants
- ✅ Messages d'erreur clairs

**Fichier:** `auth_dialog.py`

### 2. **Gestionnaire de Jeton JWT**
- ✅ Sauvegarde sécurisée du jeton dans QSettings
- ✅ Validation automatique de l'expiration
- ✅ Chargement du jeton au démarrage
- ✅ Suppression complète à la déconnexion
- ✅ Infos du jeton (durée restante, URL, mode)

**Fichier:** `token_manager.py`

### 3. **Barre d'Authentification dans la Dock Widget**
- ✅ Indicateur visuel: `● Connecté` (vert) ou `● Déconnecté` (rouge)
- ✅ Affichage de l'utilisateur et de l'URL
- ✅ Bouton de déconnexion
- ✅ Activation/désactivation automatique des boutons d'action

**Fichier modifié:** `mrv_teraka_dockwidget.py`

### 4. **Bouton Dynamique dans la Barre d'Outils**
- ✅ Affiche `Connexion` si déconnecté
- ✅ Affiche `Déconnecter` si connecté
- ✅ Change de fonction dynamiquement
- ✅ Indicateur visuel de l'état

**Fichier modifié:** `mrv_teraka.py`

### 5. **Chargement Automatique du Jeton**
- ✅ Détecte le jeton sauvegardé au démarrage
- ✅ Vérifie l'expiration
- ✅ Reconnecte automatiquement si valide
- ✅ Evite la saisie à chaque démarrage

## 🎯 Cas d'Usage

### Scénario 1: Première Connexion
```
1. Utilisateur clique "Connexion" dans la barre d'outils
2. Dialog d'authentification s'affiche
3. Utilisateur saisit: email, mot de passe, URL
4. Choisit le mode (Django ou Standalone)
5. Clique "Se connecter"
6. Si succès:
   - Jeton sauvegardé dans QSettings
   - Barre d'outils change à "Déconnecter"
   - Dock widget affiche l'utilisateur
   - Boutons d'action deviennent actifs ✅
```

### Scénario 2: Reconnexion Automatique
```
1. QGIS redémarre
2. Plugin charge au démarrage
3. TokenManager charge le jeton sauvegardé
4. Vérifie qu'il n'a pas expiré
5. Si valide:
   - PostgREST Client configuré automatiquement
   - Barre d'outils affiche "Déconnecter"
   - Dock widget affiche l'utilisateur
   - Tout prêt sans saisir l'identifiant! ✅
```

### Scénario 3: Expiration du Jeton
```
1. Après 24h d'inactivité, le jeton expire
2. Utilisateur clique sur une action (Charger DB, etc.)
3. check_api_auth() détecte l'expiration
4. Affiche "Authentification requise"
5. Dialog d'authentification s'affiche
6. Utilisateur peut se reconnecter
7. Nouveau jeton sauvegardé ✅
```

### Scénario 4: Déconnexion
```
1. Utilisateur clique "Déconnecter"
2. Confirmation demandée
3. Si oui:
   - Jeton supprimé de QSettings
   - PostgREST Client réinitialisé
   - Barre d'outils affiche "Connexion"
   - Dock widget affiche "Déconnecté"
   - Boutons d'action désactivés ✅
```

## 📊 Comparaison Avant/Après

| Fonctionnalité | Avant | Après |
|---|---|---|
| Interface d'auth | QInputDialog simple | Formulaire Qt professionnel |
| Stockage du jeton | Aucun | QSettings |
| Persistance | Non (perte à redémarrage) | Oui (automatique) |
| Expiration | Non gérée | Gestion automatique |
| Indicateurs visuels | Aucun | Barre d'auth + couleurs |
| Déconnexion | Non implémentée | Bouton + suppression sécurisée |
| Modes API | Hardcodé | Sélection dans le dialog |
| URL API | Hardcodée | Personnalisable dans le dialog |
| Mémorisation | Non | Oui (email et URL) |
| Gestion d'erreurs | Basique (message critique) | Complète (validation à chaque étape) |

## 🔧 Détails Techniques

### Fichiers Créés

```
mrv_teraka/
├── auth_dialog.py           # Formulaire d'authentification (165 lignes)
├── token_manager.py         # Gestionnaire de jeton (180 lignes)
├── AUTHENTICATION_GUIDE.md  # Documentation détaillée
└── ...
```

### Fichiers Modifiés

```
mrv_teraka/
├── mrv_teraka.py
│   ├── Imports: AuthDialog, TokenManager
│   ├── __init__: TokenManager instance
│   ├── initGui: Nouveau bouton "Connexion"
│   ├── show_auth_dialog: Nouveau (espace dialog)
│   ├── authenticate_with_credentials: Nouveau (authentification complète)
│   ├── load_saved_token: Nouveau (chargement auto au démarrage)
│   ├── update_auth_ui: Nouveau (mise à jour interface)
│   ├── logout: Nouveau (déconnexion)
│   └── run: Modifié (connexion des signaux dock)
│
└── mrv_teraka_dockwidget.py
    ├── setup_auth_ui: Nouveau (barre d'auth)
    ├── set_authenticated: Nouveau (afficher connecté)
    ├── set_unauthenticated: Nouveau (afficher déconnecté)
    └── setup_connections: Modifié (signaux logout)
```

### Structure des Données (QSettings)

```
Windows Registry:
HKEY_CURRENT_USER\Software\iTeraka\MrvTeraka\
├── auth/
│   ├── username = "user@example.com"
│   ├── url = "http://localhost:8000"
│   └── last_username = "user@example.com"
└── token/
    ├── jwt = "eyJ0eXAiOiJKV1QiLCJhbGc..."
    ├── url = "http://localhost:8000"
    ├── mode = "django"
    └── expiry = "1713867890.12"

Linux (~/.config):
~/.config/iTeraka/MrvTeraka.conf
[auth]
username=user@example.com
...

macOS (Preferences):
~/Library/Preferences/com.iTeraka.MrvTeraka.plist
```

## 🚀 Flux d'Exécution

### Démarrage du Plugin

```
QGIS.startup()
   ↓
classFactory(iface)
   ↓
MrvTeraka.__init__()
   └─> TokenManager() créé
        └─> QSettings('iTeraka', 'MrvTeraka') initialisé
   ↓
MrvTeraka.initGui()
   ├─> Crée ActionButton "Connexion"
   ├─> Crée ActionButton "iTeraka" (pour la dock)
   └─> load_saved_token()
        ├─> TokenManager.load_token()
        │   ├─ Cherche 'token/jwt' dans QSettings
        │   ├─ Vérifie 'token/expiry'
        │   └─ Retourne (token, url, mode) ou (None, None, None)
        ├─> Si token valide:
        │   ├─> PostgREST(url).set_auth_token(token)
        │   └─> update_auth_ui() → Bouton = "Déconnecter"
        └─> Sinon: Bouton = "Connexion"
```

### Authentification

```
Utilisateur clique "Connexion"
   ↓
show_auth_dialog()
   └─> AuthDialog(api_modes={...})
        ├─ load_saved_settings() → remplit les champs
        └─ emit: Accepted ou Rejected
   ↓
Si Accepted:
   ├─> authenticate_with_credentials()
   │   ├─> PostgRESTAuthenticator(url, mode).authenticate()
   │   │   └─> POST /api/auth/signin {username, password}
   │   │       ↓
   │   │       Retourne: {access_token: "..."}
   │   ├─> PostgREST(url).set_auth_token(token)
   │   ├─> TokenManager.save_token()
   │   │   └─> QSettings.setValue('token/jwt', token)
   │   │       QSettings.setValue('token/expiry', time + 24h)
   │   ├─> update_auth_ui()
   │   │   ├─> auth_action.setText("Déconnecter")
   │   │   └─> auth_action.triggered → logout()
   │   ├─> dockwidget.set_authenticated()
   │   │   ├─> status_label = "● Connecté" (vert)
   │   │   ├─> user_label = "user@example.com @ ..."
   │   │   └─> Boutons d'action = enabled
   │   └─> QMessageBox.information("Succès")
   │
   └─> Si Exception:
        ├─> QMessageBox.critical(error)
        └─> dialog.show_error(error)
```

### Actions (Charger DB, Comparer, etc.)

```
Utilisateur clique "Charger données DB"
   ↓
load_database_data()
   ├─> check_api_auth()
   │   ├─> if not postgrest: show_auth_dialog()
   │   ├─> if not token_valid: show_auth_dialog()
   │   └─> return True or False
   ├─> if False: return (fin)
   ├─> endpoint = endpointLineEdit.text()
   ├─> postgrest.select(endpoint)
   │   └─> GET /api/endpoint
   │       Header: Authorization: Bearer {token}
   │       ↓
   │       Retourne: [{...data...}]
   ├─> create_vector_layer_from_json(data)
   ├─> QgsProject.addMapLayer(layer) ✅
   └─> QMessageBox.information("Couche chargée")
```

### Déconnexion

```
Utilisateur clique "Déconnecter"
   ↓
logout()
   ├─> QMessageBox.question("Êtes-vous sûr ?")
   ├─> Si Yes:
   │   ├─> TokenManager.clear_token()
   │   │   └─> QSettings.remove('token/jwt')
   │   │       QSettings.remove('token/expiry')
   │   ├─> postgrest = None
   │   ├─> auth_action.setText("Connexion")
   │   ├─> auth_action.triggered → show_auth_dialog()
   │   ├─> dockwidget.set_unauthenticated()
   │   │   ├─> status_label = "● Déconnecté" (rouge)
   │   │   ├─> user_label = "Pas connecté"
   │   │   └─> Boutons d'action = disabled
   │   └─> QMessageBox.information("Déconnecté")
   └─> Si No: (rien ne change)
```

## 💡 Points Clés

1. **Persistance du jeton**: Le jeton est sauvegardé dans QSettings et rechargé au démarrage
2. **Gestion d'expiration**: Vérifiée automatiquement avant chaque action
3. **Interface synchronisée**: La dock widget et la barre d'outils se mettent à jour ensemble
4. **Sécurité**: Le jeton est supprimé complètement à la déconnexion
5. **UX fluide**: Pas de saisie à chaque redémarrage (reconnexion auto)
6. **Modes API**: Support de Django ET PostgREST Standalone
7. **Erreurs claires**: Messages explicites en cas de problème

## ✅ Checklist

- [x] Formulaire d'authentification modifié avec modes API
- [x] TokenManager créé pour la persistance
- [x] QSettings utilisé pour le stockage sécurisé
- [x] Barre d'auth ajoutée à la dock widget
- [x] Bouton dynamique dans la barre d'outils
- [x] Chargement automatique au démarrage
- [x] Déconnexion sécurisée implémentée
- [x] Indicateurs visuels (couleurs, texte)
- [x] Gestion d'expiration du jeton
- [x] Documentation complète

