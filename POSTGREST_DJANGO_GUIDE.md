# Guide: PostgREST via Django

## Situation

Vous avez PostgREST servi par un serveur Django au lieu de PostgREST standalone.

```
Avant (PostgREST standalone):
http://localhost:3000/communes

Maintenant (PostgREST via Django):
http://localhost:8000/api/communes
```

## Configuration

### 1. Initialiser le mode Django

```python
from postgrest_client import PostgREST, PostgRESTAuthenticator, PostgRESTMode

# Créer un client en mode Django
postgrest = PostgREST('http://localhost:8000', mode=PostgRESTMode.DJANGO)

# Ou simplement passer le mode au plugin
# Dans mrv_teraka.py:
self.postgrest = PostgREST(self.api_base_url, mode=PostgRESTMode.DJANGO)
```

### 2. Authentification Django

```python
# Créer un authentificateur en mode Django
authenticator = PostgRESTAuthenticator(
    'http://localhost:8000',
    mode=PostgRESTMode.DJANGO
)

# S'authentifier
token = authenticator.authenticate('user@example.com', 'password')

# Créer le client et définir le jeton
postgrest = PostgREST('http://localhost:8000', mode=PostgRESTMode.DJANGO)
postgrest.set_auth_token(token)
```

## Utilisation

L'utilisation est identique à celle du PostgREST standalone:

```python
# SELECT
communes = postgrest.select('communes')

# AVEC FILTRES
communes = postgrest.select('communes', filters={'region': 'eq.Nord'})

# INSERT
postgrest.insert('communes', {'name': 'Nouvelle', 'population': 25000})

# UPDATE
postgrest.update('communes', {'population': 60000}, {'id': 'eq.1'})

# DELETE
postgrest.delete('communes', {'id': 'eq.1'})

# RPC
result = postgrest.call_rpc('my_function', {'param': 'value'})
```

## Différences Django vs Standalone

### Authentification

| Aspect | Standalone | Django |
|--------|-----------|--------|
| URL base | `http://localhost:3000` | `http://localhost:8000` |
| Endpoint API | `/communes` | `/api/communes` |
| Login endpoint | `/auth/signin` | `/api/auth/signin` |
| Champ username | `email` | `username` ou `email` |
| Format réponse | `{access_token: "..."}` | `{token: "..."}` ou `{access: "..."}` |

### Normalization automatique

Le client gère automatiquement les normalisations:

```python
# Même résultat
postgrest1 = PostgREST('http://localhost:8000', mode=PostgRESTMode.DJANGO)
postgrest2 = PostgREST('http://localhost:8000/api', mode=PostgRESTMode.DJANGO)

# Les deux ont api_base_url = 'http://localhost:8000/api'
```

## Configuration du Plugin MrvTeraka

### Avant (PostgREST standalone)

```python
# Dans __init__
self.api_base_url = 'http://localhost:3000'

# Dans authenticate()
authenticator = PostgRESTAuthenticator(self.api_base_url)
```

### Après (PostgREST via Django)

```python
# Dans __init__
self.api_base_url = 'http://localhost:8000'
self.postgrest_mode = PostgRESTMode.DJANGO  # Ajouter ceci

# Dans authenticate()
authenticator = PostgRESTAuthenticator(
    self.api_base_url,
    mode=self.postgrest_mode
)
postgrest = PostgREST(self.api_base_url, mode=self.postgrest_mode)
postgrest.set_auth_token(token)
```

## Dépannage Django

### 1. "Unauthorized" après authentification

**Cause:** Le jeton JWT n'a pas les permissions appropriées dans PostgREST

**Solution:**
- Vérifiez la configuration PostgREST dans Django
- Assurez-vous que le rôle JWT a les permissions SELECT, INSERT, UPDATE, DELETE

```sql
-- Exemple: Donner les permissions au rôle
GRANT SELECT, INSERT, UPDATE, DELETE ON communes TO api_user;
```

### 2. "401 Unauthorized" sur les requêtes

**Cause:** 
- Jeton expiré
- URL incorrecte
- Headers mal configurés

**Solution:**
```python
# Vérifier le jeton
if self.postgrest.jwt_token:
    print(f"Token: {self.postgrest.jwt_token[:20]}...")
else:
    print("Token non défini!")

# Authentifier de nouveau
try:
    token = authenticator.authenticate(username, password)
    postgrest.set_auth_token(token)
except Exception as e:
    print(f"Erreur: {e}")
```

### 3. "Table not found"

**Cause:** Le schéma Django expose peut-être les tables différemment

**Solution:**
```python
# Essayer avec le schéma préfixé
communes = postgrest.select('public.communes')

# Ou vérifier dans Django:
# POST /api/ pour voir la liste des endpoints disponibles
```

### 4. CORS Issues

**Cause:** Django bloque les requêtes CORS

**Solution:** Configurer CORS dans Django

```python
# settings.py
INSTALLED_APPS = [
    ...
    'corsheaders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    ...
]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:*",
]
```

## Vérifier la configuration PostgREST

### 1. Tester l'endpoint directement

```bash
# Sans authentification (test que PostgREST répond)
curl http://localhost:8000/api/communes

# Avec authentification
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/communes
```

### 2. Vérifier la structure du schéma

```sql
-- Dans PostgreSQL
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
```

### 3. Tester l'authentification

```python
from postgrest_client import PostgRESTAuthenticator, PostgRESTMode

auth = PostgRESTAuthenticator('http://localhost:8000', mode=PostgRESTMode.DJANGO)

try:
    token = auth.authenticate('user@example.com', 'password')
    print(f"✓ Authentification réussie")
    print(f"  Token: {token[:50]}...")
except Exception as e:
    print(f"✗ Erreur: {e}")
```

## Fichier django.conf complet

Voici un exemple de configuration Django avec PostgREST:

```python
# django_postgrest_config.py

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'your_db',
        'USER': 'postgres',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# PostgREST configuration
POSTGREST_URL = 'http://localhost:8000/api'
POSTGREST_JWT_SECRET = 'your_jwt_secret'
POSTGREST_JWT_ALGORITHM = 'HS256'

# Authentification Django
INSTALLED_APPS = [
    'django.contrib.auth',
    'rest_framework',
    'corsheaders',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ]
}
```

## Résumé

| Paramètre | Standalone | Django |
|-----------|-----------|--------|
| Mode | `PostgRESTMode.STANDALONE` | `PostgRESTMode.DJANGO` |
| URL de base | `http://localhost:3000` | `http://localhost:8000` |
| Username field | `email` | `username` ou `email` |
| Response format | `{access_token}` | `{token}` ou `{access}` |
| Authentification | PostgREST interne | Django + PostgREST |

Utilisez le mode approprié lors de l'initialisation:

```python
# Standalone
postgrest = PostgREST('http://localhost:3000')
auth = PostgRESTAuthenticator('http://localhost:3000')

# Django
postgrest = PostgREST('http://localhost:8000', mode=PostgRESTMode.DJANGO)
auth = PostgRESTAuthenticator('http://localhost:8000', mode=PostgRESTMode.DJANGO)
```

