# Comparaison: PostgREST Standalone vs PostgREST via Django

## 📊 Tableau Comparatif Complet

### Architecture

| Critère | PostgREST Standalone | PostgREST via Django |
|---------|----------------------|----------------------|
| **Architecture** | Microservice indépendant | Intégré au framework Django |
| **Port** | 3000 (par défaut) | 8000 (Django) + PostgREST interne |
| **Base de données** | PostgreSQL directement | PostgreSQL via Django |
| **Couches** | 1 couche: PostgREST | 2 couches: Django + PostgREST |
| **Déploiement** | Standalone (`postgrest`) | Intégré (`manage.py runserver`) |

### URL et Endpoints

| Critère | PostgREST Standalone | PostgREST via Django |
|---------|----------------------|----------------------|
| **URL Base** | `http://localhost:3000` | `http://localhost:8000` |
| **Endpoint Table** | `/communes` | `/api/communes` |
| **Login** | `http://localhost:3000/auth/signin` | `http://localhost:8000/api/auth/signin` |
| **RPC** | `/rpc/function_name` | `/api/rpc/function_name` |
| **Schéma** | `GET /` | `GET /api/` |

### Authentification

| Critère | PostgREST Standalone | PostgREST via Django |
|---------|----------------------|----------------------|
| **Méthode** | JWT natif PostgREST | JWT Django ou Token Django |
| **Username Field** | `email` (standard) | `username` ou `email` (configurable) |
| **Endpoint Login** | `/auth/signin` | `/api/auth/signin` ou `/api/token/` |
| **Format Réponse** | `{access_token: "..."}` | `{token: "..."}` ou `{access: "..."}` |
| **Expiration** | Configurable dans PostgREST | Configurable dans Django |
| **Refresh Token** | Non natif | Possible avec JWT Django |

### Filtres et Requêtes

| Critère | PostgREST Standalone | PostgREST via Django |
|---------|----------------------|----------------------|
| **Syntaxe** | Identique | Identique |
| **Opérateurs** | `eq`, `gt`, `lt`, `ilike`, etc. | `eq`, `gt`, `lt`, `ilike`, etc. |
| **Pagination** | `?limit=10&offset=0` | `?limit=10&offset=0` |
| **Tri** | `?order=name.asc` | `?order=name.asc` |
| **Sélection Colonnes** | `?select=id,name` | `?select=id,name` |

### Performance

| Critère | PostgREST Standalone | PostgREST via Django |
|---------|----------------------|----------------------|
| **Latence** | Très faible (direct PostgreSQL) | Légèrement plus haute (couche Django) |
| **Throughput** | Haute (pas d'overhead) | Moyenne (overhead Django) |
| **Concurrence** | Excellente (Haskell natif) | Bonne (Python + workers) |
| **Caching** | HTTP natif | Django caching + HTTP |
| **Compression** | Gzip natif | Django middleware + Gzip |

### Sécurité

| Critère | PostgREST Standalone | PostgREST via Django |
|---------|----------------------|----------------------|
| **SQL Injection** | Prévention native (prepared statements) | Prévention double (Django ORM + SQL) |
| **CORS** | À configurer manuellement | Middleware Django disponible |
| **CSRF** | Non applicable (API) | Non applicable (API) |
| **Rate Limiting** | À implémenter (Nginx, etc.) | Django middleware ou package |
| **RBAC** | PostgreSQL roles natif | Django permissions + PostgreSQL |
| **Audit** | PostgreSQL triggers | Django logging + PostgreSQL |

### Configuration et Administration

| Critère | PostgREST Standalone | PostgREST via Django |
|---------|----------------------|----------------------|
| **Config File** | `postgrest.conf` (TOML) | `settings.py` (Python) |
| **Migrations DB** | Manuelles ou Alembic | Django migrations natif |
| **Admin Interface** | Pas fourni | Django admin intégré ✅ |
| **Users Management** | À implémenter | Django user management ✅ |
| **Monitoring** | Propriétaire | Middleware Django |
| **Logging** | Syslog/JSON | Django logging framework |

### Fonctionnalités Avancées

| Critère | PostgREST Standalone | PostgREST via Django |
|---------|----------------------|----------------------|
| **Views** | Support SQL natif ✅ | Support SQL natif ✅ |
| **Stored Procedures (RPC)** | Support natif ✅ | Support natif ✅ |
| **Triggers** | Support natif ✅ | Support natif ✅ |
| **Custom Logic** | PostgreSQL functions | Django views + PostgreSQL |
| **Webhooks** | À implémenter | Possibilité de signaux Django |
| **Real-time (WebSocket)** | À implémenter | À implémenter |

---

## 🎯 Cas d'Utilisation

### Utiliser PostgREST Standalone si:

✅ **Vous voulez...**
- Une API rapide et légère
- Minimiser les dépendances
- Déployer indépendamment
- Maximum de performance
- Gérer vous-même la logique applicative
- Une solution "micro-service"

**Exemples:**
```
- API mobile/SPA simple
- Prototype rapide
- Microservice dédié
- Haute charge (100k+ req/sec)
- Budget limité en infrastructure
```

### Utiliser PostgREST via Django si:

✅ **Vous voulez...**
- Interface admin intégrée
- Gestion d'utilisateurs/permissions
- Logique applicative complexe
- Un seul déploiement
- Écosystème riche (packages, middleware)
- Authentification sophistiquée

**Exemples:**
```
- Plateforme SaaS complexe
- Système de gestion utilisateurs
- Plusieurs APIs intégrées
- Opérations background (Celery)
- Admin panel pour opérateurs
- Logique métier complexe
```

---

## 📍 Pour Votre Plugin QGIS

### Recommandation: **PostgREST via Django** ✅

**Pourquoi?**

1. **Authentification Simplifiée**
   - Django gère déjà les utilisateurs
   - Intégration facile avec tokens JWT
   
2. **Admin Interface**
   - Gérer les données sans code (Django admin)
   - Ajouter/modifier des communes facilement

3. **Logique Métier**
   - Validations complexes
   - Transformations de données
   - Webhooks et notifications

4. **Maintenance**
   - Un seul déploiement à gérer
   - Logs centralisés
   - Configuration en Python (familier)

5. **Sécurité**
   - Middleware CORS
   - Rate limiting
   - RBAC via Django permissions

---

## 🔀 Migration: Standalone → Django

Si vous passez de Standalone à Django:

### Étapes

```python
# 1. Initializer le mode Django
from postgrest_client import PostgRESTMode

postgrest = PostgREST('http://localhost:8000', mode=PostgRESTMode.DJANGO)

# 2. Authentification
authenticator = PostgRESTAuthenticator(
    'http://localhost:8000',
    mode=PostgRESTMode.DJANGO
)

# 3. Le reste est identique!
communes = postgrest.select('communes')
postgrest.insert('communes', {...})
```

### Changement d'URL Uniquement

```
Avant: http://localhost:3000/communes
Après: http://localhost:8000/api/communes
```

---

## 💡 Configuration Comparative

### PostgREST Standalone

```toml
# postgrest.conf
db-uri = "postgres://user:pass@localhost/db"
db-schema = "public"
db-anon-role = "web_anon"
jwt-secret = "your-secret-key"
server-port = 3000
server-host = "localhost"
```

### PostgREST via Django

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'db',
        'USER': 'user',
        'PASSWORD': 'pass',
        'HOST': 'localhost',
    }
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ]
}

POSTGREST_URL = 'http://localhost:8000/api'
```

---

## 📊 Matrice Décision

```
                     Standalone  |  Django
─────────────────────────────────┼──────────────
Performance         ★★★★★        |  ★★★★
Rapidité démarrage  ★★★★★        |  ★★★
Facilité config     ★★★          |  ★★★★
Admin interface     ★            |  ★★★★★
User management     ★            |  ★★★★★
Authentification    ★★★          |  ★★★★
Middleware/auth     ★★           |  ★★★★★
Scalabilité         ★★★★         |  ★★★
DB Migrations       ★★           |  ★★★★★
Courbe apprentissage★★★★         |  ★★★
Écosystème packages ★★           |  ★★★★★
─────────────────────────────────┼──────────────
SCORE GLOBAL        28/55        |  46/55
```

---

## 🚀 Code Identique

Le client PostgREST fourni supporte les **deux modes**. Votre code reste **identique**:

```python
# ✅ Fonctionne avec les deux
communes = postgrest.select('communes')
communes = postgrest.select('communes', filters={'region': 'eq.Nord'})
postgrest.insert('communes', {'name': 'Nouvelle'})
postgrest.update('communes', {'pop': 60000}, {'id': 'eq.1'})
postgrest.delete('communes', {'id': 'eq.1'})
```

### Seule différence: l'initialisation

```python
# Standalone
postgrest = PostgREST('http://localhost:3000')

# Django
postgrest = PostgREST('http://localhost:8000', mode=PostgRESTMode.DJANGO)
```

---

## 📋 Tableau d'Endpoints

### Standalone

```
GET    http://localhost:3000/commons
POST   http://localhost:3000/communes
PATCH  http://localhost:3000/communes?id=eq.1
DELETE http://localhost:3000/communes?id=eq.1
POST   http://localhost:3000/rpc/my_function
```

### Django

```
GET    http://localhost:8000/api/communes
POST   http://localhost:8000/api/communes
PATCH  http://localhost:8000/api/communes?id=eq.1
DELETE http://localhost:8000/api/communes?id=eq.1
POST   http://localhost:8000/api/rpc/my_function
```

---

## ⚠️ Points d'Attention

### PostgREST Standalone

**Problèmes:**
- Pas de gestion d'utilisateurs (à implémenter)
- Pas d'admin panel
- Authentification basique
- Monitoring limité
- Scaling plus complexe

### PostgREST via Django

**Problèmes:**
- Légèrement plus lent
- Plus de dépendances
- Configuration Python (moins de TOML)
- Overhead Django

---

## 🎓 Exemple Pratique pour QGIS

### Votre Plugin

```python
from postgrest_client import PostgREST, PostgRESTAuthenticator, PostgRESTMode

class MrvTeraka:
    def __init__(self, iface):
        # Configuration
        self.api_base_url = 'http://localhost:8000'
        self.postgrest_mode = PostgRESTMode.DJANGO  # ← C'est tout!
        
    def authenticate(self):
        # Identique pour les deux modes
        auth = PostgRESTAuthenticator(self.api_base_url, mode=self.postgrest_mode)
        token = auth.authenticate(email, password)
        
        self.postgrest = PostgREST(self.api_base_url, mode=self.postgrest_mode)
        self.postgrest.set_auth_token(token)
    
    def load_data(self, table):
        # Identique pour les deux modes
        return self.postgrest.select(table)
```

**Le code fonctionne avec les deux!** Par un simple changement de:
- `PostgRESTMode.DJANGO` → `PostgRESTMode.STANDALONE`
- `http://localhost:8000` → `http://localhost:3000`

---

## 📚 Ressources

- [PostgREST Standalone Doc](https://postgrest.org/)
- [Django + PostgREST Intégration](https://docs.djangoproject.com/)
- [PostgreSQL RBAC](https://www.postgresql.org/docs/current/sql-grant.html)

