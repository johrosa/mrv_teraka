# 📋 Django Error Viewer - Guide d'Utilisation

## 🎯 Vue d'ensemble

Le module `django_error_viewer.py` affiche les pages d'erreur Django (404, 500, etc.) avec rendu HTML complet dans une interface QGIS élégante.

**Caractéristiques:**
- ✅ Rendu HTML des pages d'erreur Django
- ✅ Onglets pour visualiser différentes perspectives (HTML, Info technique, Source brute)
- ✅ Affichage des en-têtes HTTP, codes d'erreur, messages d'erreur
- ✅ Export en HTML ou texte brut
- ✅ Copie dans le presse-papiers
- ✅ Interface PyQt5 intégrée à QGIS

---

## 🚀 Utilisation Simple

### Méthode 1: Via `postgrest_client.py` (Recommandée)

Les méthodes `*_with_ui()` affichent automatiquement les erreurs Django:

```python
from postgrest_client import PostgREST, PostgRESTMode

# Initialiser le client
postgrest = PostgREST(
    "http://localhost:8000",
    mode=PostgRESTMode.DJANGO
)
postgrest.set_auth_token("your_jwt_token")

# Les erreurs Django s'affichent automatiquement avec rendu HTML
try:
    data = postgrest.select_with_ui('communes')  # ← Affiche erreur si 404/500/etc
except RuntimeError as e:
    print(f"Erreur: {e}")
```

### Méthode 2: Utilisation Directe

```python
from django_error_viewer import show_django_error

# Afficher une erreur Django
show_django_error(
    parent=None,
    error_code=404,
    error_reason="Not Found",
    html_content="<html><body><h1>404 Not Found</h1>...</body></html>",
    url="http://localhost:8000/api/communes/invalid",
    method="GET",
    headers={
        'Content-Type': 'text/html; charset=utf-8',
        'Server': 'Django/3.2'
    },
    error_message="La ressource demandée n'existe pas"
)
```

---

## 📋 Codes d'Erreur Supportés

| Code | Raison | Signification |
|------|--------|---------------|
| 400 | Bad Request | Mauvaise requête |
| 401 | Unauthorized | Non authentifié |
| 403 | Forbidden | Accès refusé |
| 404 | Not Found | Page non trouvée |
| 405 | Method Not Allowed | Méthode non autorisée |
| 500 | Internal Server Error | Erreur interne du serveur |
| 502 | Bad Gateway | Mauvaise passerelle |
| 503 | Service Unavailable | Service indisponible |

---

## 🔧 Configuration

### Dans `postgrest_client.py`

Les méthodes suivantes permettent d'afficher les erreurs avec UI:

```python
# Méthodes avec affichage UI
postgrest.select_with_ui(table, ...)      # GET
postgrest.insert_with_ui(table, data)     # POST
postgrest.update_with_ui(table, data)     # PATCH
postgrest.delete_with_ui(table, filters)  # DELETE
postgrest.call_rpc_with_ui(function, params)  # RPC
```

### Passer `show_error_ui=True` en paramètre

```python
# Utilisation avancée - méthode _make_request()
result = postgrest._make_request(
    method='GET',
    endpoint='communes',
    show_error_ui=True  # ← Affiche l'erreur avec UI
)
```

---

## 💡 Cas d'Utilisation

### 1️⃣ Dans validation_dialog.py

```python
from postgrest_client import PostgREST

# Charger les données avec affichage UI des erreurs
try:
    data = postgrest.select_with_ui('communes')
    self.populate_table_from_data(self.table_collected, data)
except RuntimeError:
    pass  # L'erreur est déjà affichée avec rendu HTML
```

### 2️⃣ Dans mergin_workflow_manager.py

```python
# Fusionner les données avec affichage UI des erreurs
try:
    result = postgrest.insert_with_ui('communes', new_records)
    self.validate_data(project_id, result)
except RuntimeError as e:
    self.save_error_log(str(e))
```

### 3️⃣ Gestion d'erreurs personnalisée

```python
from django_error_viewer import DjangoErrorViewer

class MyCustomDialog:
    def handle_api_error(self, http_error, url, body):
        # Créer une erreur personnalisée
        dialog = DjangoErrorViewer(
            parent=self,
            error_data={
                'status_code': http_error.code,
                'reason': http_error.reason,
                'html': body,
                'url': url,
                'method': 'GET',
                'headers': dict(http_error.headers),
                'error_message': 'Erreur lors de la synchronisation avec le serveur'
            }
        )
        dialog.exec_()
```

---

## 🎨 Personnalisation

### Modifier les couleurs

Éditer `django_error_viewer.py`, section CSS:

```python
# Dans _generate_html_report()
<style>
    body {
        background: #f5f5f5;  # ← Personnaliser
        color: #333;
    }
    h1 {
        color: #d32f2f;  # ← Couleur des titres d'erreur
    }
    /* ... etc ... */
</style>
```

### Ajouter des informations personnalisées

```python
error_data = {
    'status_code': 500,
    'reason': 'Internal Server Error',
    'html': html_content,
    'error_message': 'Erreur lors du traitement - Veuillez réessayer',
    'url': url,
    'method': 'POST',
    'headers': {},
    'custom_info': 'Informations supplémentaires (ajouté séparement)'  # Personnalisé
}
```

---

## 🔍 Onglets Disponibles

### 1️⃣ Vue HTML (💻)
Affiche le rendu HTML complet de la page d'erreur Django. Utilise `QWebEngineView` pour un rendu natif.

### 2️⃣ Infos Téchniques (ℹ️)
Affiche:
- Code d'erreur HTTP
- Raison (ex: "Not Found")
- Signification du code
- URL de la requête
- Méthode HTTP (GET, POST, etc)
- En-têtes HTTP
- Message d'erreur personnalisé

### 3️⃣ Source Brute (📄)
Affiche le contenu HTML brut formaté pour lisibilité avec syntaxe monospace.

---

## 📤 Export et Partage

### Exporter en HTML

```python
# Automatique via le bouton "💾 Exporter comme fichier"
# Le fichier exporté contient:
# - Rapport complet avec styling CSS
# - Informations téchniques formatées
# - Contenu de la page d'erreur
```

### Exporter en Texte

```python
# Sélectionner "Fichiers texte (*.txt)" lors de l'export
# Format:
# ════════════════════════════════════════════════════════════════════════════════
# ERREUR DJANGO 404: Not Found
# ════════════════════════════════════════════════════════════════════════════════
# 
# INFORMATIONS TECHNIQUES
# ────────────────────────────────────────────────────────────────────────────────
# Code: 404
# Raison: Not Found
# URL: http://localhost:8000/api/communes/invalid
# Méthode: GET
```

### Copier dans le presse-papiers

```python
# Bouton "📋 Copier l'erreur"
# Copies un rapport textuel dans le presse-papiers
```

---

## 🐛 Dépannage

### "QWebEngineView n'est pas disponible"
- `django_error_viewer.py` fait un fallback sur `QTextEdit` si `QWebEngineView` échoue
- Le rendu HTML reste disponible mais sans CSS

### "L'erreur Django ne s'affiche pas"
1. Vérifier que `django_error_viewer.py` est dans le même répertoire que `postgrest_client.py`
2. Vérifier les imports:
   ```python
   from django_error_viewer import show_django_error
   ```
3. Utiliser les méthodes `*_with_ui()` au lieu de `*()`:
   ```python
   # ✅ Correct
   data = postgrest.select_with_ui('communes')
   
   # ❌ Incorrect (n'affiche pas l'erreur)
   data = postgrest.select('communes')
   ```

### "Export HTML échoue"
- Vérifier les permissions d'écriture du répertoire
- Préférer `/tmp/` ou le répertoire utilisateur
- Vérifier l'espace disque disponible

---

## 📊 Exemple Complet

```python
# Dans mrv_teraka.py ou un dialogue

from postgrest_client import PostgREST, PostgRESTMode
from validation_dialog import DataValidationDialog

class MyPlugin:
    def load_merged_data(self):
        """Charge les données avec gestion d'erreurs Django"""
        
        postgrest = PostgREST(
            "http://localhost:8000",
            mode=PostgRESTMode.DJANGO
        )
        postgrest.set_auth_token(self.jwt_token)
        
        try:
            # Charger les données - affiche erreur Django si elle survient
            collected_data = postgrest.select_with_ui('communes')
            original_data = postgrest.select_with_ui('communes_original')
            
            # Afficher le dialog de validation
            dialog = DataValidationDialog(
                collected_data=collected_data,
                original_data=original_data
            )
            
            if dialog.exec_():
                # Fusionner avec affichage UI des erreurs
                result = postgrest.insert_with_ui(
                    'communes',
                    dialog.validated_data
                )
                
        except RuntimeError:
            # Erreur Django déjà affichée dans l'UI
            pass
```

---

## ✨ Fonctionnalités Futures

- [ ] Intégration avec système de logging QGIS
- [ ] Suggestions de correction automatiques
- [ ] Historique des erreurs
- [ ] Mise en cache des pages d'erreur
- [ ] Mode "debug" avec traces de pile
- [ ] Intégration avec système de support

---

## 📚 Références

- Documentation Django: https://docs.djangoproject.com/
- Codes HTTP: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status
- PostgREST: https://postgrest.org/
- PyQt5 Widgets: https://doc.qt.io/qt-5/qwebengineview.html

---

**Django Error Viewer - Plugin MrvTeraka**
v1.0 - 2026-04-27

