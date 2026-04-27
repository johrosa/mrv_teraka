# 🚀 Django Error Viewer - Quick Start

## 📝 Résumé

Vous avez maintenant une **visionneuse d'erreurs Django complète** qui affiche les pages d'erreur (404, 500, etc.) avec rendu HTML natif dans QGIS.

---

## ⚡ Utilisation en 30 secondes

### Option 1: Automatique (Recommandée)

```python
from postgrest_client import PostgREST, PostgRESTMode

postgrest = PostgREST("http://localhost:8000", mode=PostgRESTMode.DJANGO)
postgrest.set_auth_token("token")

# ✅ Les erreurs s'affichent automatiquement avec rendu HTML !
data = postgrest.select_with_ui('communes')
```

### Option 2: Affichage Manuel

```python
from django_error_viewer import show_django_error

show_django_error(
    parent=None,
    error_code=404,
    error_reason="Not Found",
    html_content="<html>...</html>",
    url="http://localhost:8000/api/communes",
    method="GET"
)
```

---

## 📦 Fichiers Créés

```
✨ django_error_viewer.py
   ├─ Classe DjangoErrorViewer
   ├─ Fonction show_django_error()
   └─ Support complet du rendu HTML

✨ postgrest_client.py (modifié)
   ├─ Méthode select_with_ui()
   ├─ Méthode insert_with_ui()
   ├─ Méthode update_with_ui()
   ├─ Méthode delete_with_ui()
   └─ Méthode call_rpc_with_ui()

📚 DJANGO_ERROR_VIEWER_GUIDE.md
   └─ Documentation complète

📚 examples_django_error_viewer.py
   └─ 8 exemples pratiques
```

---

## 🎨 Interface

### Trois Onglets

| Onglet | Description |
|--------|-------------|
| **💻 Vue HTML** | Rendu de la page d'erreur Django |
| **ℹ️ Infos Téchniques** | Code, raison, URL, en-têtes, etc. |
| **📄 Source Brute** | HTML/Texte brut formaté |

### Boutons d'Action

- 📋 **Copier l'erreur** → Dans le presse-papiers
- 💾 **Exporter** → Fichier HTML ou TXT
- 🔄 **Réviser** → Parcourir les onglets

---

## 🔔 Exemple Real-World

```python
# Dans validation_dialog.py

class DataValidationDialog(QDialog):
    def load_data(self):
        try:
            # Charger les données - erreur Django affichée automatiquement
            data = self.postgrest.select_with_ui('communes')
            self.populate_table(data)
        except RuntimeError:
            # L'erreur est déjà affichée dans l'UI
            pass
```

---

## ✅ Caractéristiques

- ✅ **Rendu HTML natif** - QWebEngineView pour affichage perfect
- ✅ **Fallback intelligent** - QTextEdit si QWebEngine indisponible
- ✅ **Export** - HTML ou TXT
- ✅ **Copier/Paster** - Simplement
- ✅ **Multi-plateforme** - Windows/Linux/macOS
- ✅ **Intégration QGIS** - PyQt5 natif

---

## 🎯 Cas d'Usage

**Avant:** ❌ Messages d'erreur texte incompréhensibles
```
"PostgREST HTTP 404 : Not Found
<!DOCTYPE html>... [700 lignes de HTML]"
```

**Après:** ✅ Page d'erreur Django affichée proprement avec UI interactive
- Voir l'erreur comme elle apparaît dans le navigateur
- Exporter pour debug
- Copier pour support

---

## 🔧 Configuration

### Mode Standalone

```python
postgrest = PostgREST(
    "http://localhost:3000",
    mode=PostgRESTMode.STANDALONE
)
```

### Mode Django

```python
postgrest = PostgREST(
    "http://localhost:8000",
    mode=PostgRESTMode.DJANGO
)
```

---

## 📊 Codes Erreur Supportés

| Code | Affichage |
|------|-----------|
| 4xx | 🟠 Orange (Client Error) |
| 5xx | 🔴 Rouge (Server Error) |

---

## 💡 Pro Tips

1. **Toujours utiliser `*_with_ui()` dans les dialogs**
   ```python
   # ✅ Bon
   data = postgrest.select_with_ui('communes')
   
   # ❌ Mauvais
   data = postgrest.select('communes')
   ```

2. **Catcher les RuntimeError**
   ```python
   try:
       data = postgrest.select_with_ui('communes')
   except RuntimeError:
       pass  # Erreur déjà affichée
   ```

3. **Exporter les erreurs pour debug**
   - Bouton "💾 Exporter" dans l'UI
   - Format HTML pour navigateur
   - Format TXT pour logs

---

## 🚀 Intégration Rapide

### Dans votre code existant

```python
# Avant
data = postgrest.select('communes')

# Après  
data = postgrest.select_with_ui('communes')
```

C'est tout! 🎉

---

## 📚 Documentation Complète

Voir **[DJANGO_ERROR_VIEWER_GUIDE.md](./DJANGO_ERROR_VIEWER_GUIDE.md)** pour:
- Configuration avancée
- Personnalisation
- Cas d'usage détaillés
- Dépannage

---

## 🎬 Démarrage

1. ✅ Fichier `django_error_viewer.py` créé
2. ✅ Méthodes `*_with_ui()` ajoutées à `postgrest_client.py`  
3. ✅ Documentation et exemples fournis
4. 🔄 **À faire:** Utiliser dans votre code!

---

**Prêt à utiliser! 🚀**

