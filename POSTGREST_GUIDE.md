# Guide d'utilisation de PostgREST avec le Plugin MrvTeraka

## Vue d'ensemble

Ce plugin QGIS intègre un client PostgREST pour communiquer avec une API PostgREST. PostgREST est une couche API automatic générée depuis une base de données PostgreSQL.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Plugin QGIS (MrvTeraka)                     │
├─────────────────────────────────────────────────────────┤
│  MrvTeraka (classe principale)                          │
│  ├─ PostgRESTAuthenticator (authentification JWT)       │
│  └─ PostgREST (client API)                              │
└────────────────┬────────────────────────────────────────┘
                 │ HTTPS
                 ▼
┌─────────────────────────────────────────────────────────┐
│         Backend Java/Node.js/Python                      │
│         (serveur d'authentification JWT)                 │
└────────────────┬────────────────────────────────────────┘
                 │ 
                 ▼
┌─────────────────────────────────────────────────────────┐
│         PostgREST (http://localhost:3000)                │
│         (API auto-générée depuis PostgreSQL)            │
├─────────────────────────────────────────────────────────┤
│  GET    /communes      - Récupérer toutes communes      │
│  POST   /communes      - Ajouter une commune            │
│  PATCH  /communes      - Mettre à jour commune         │
│  DELETE /communes      - Supprimer commune             │
│  POST   /rpc/function  - Appeler une fonction RPC      │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│         PostgreSQL Database                              │
│         (Base de données)                                │
└─────────────────────────────────────────────────────────┘
```

## Installation et Configuration

### 1. Configuration de l'URL PostgREST

Dans `mrv_teraka.py`, modifiez l'URL de base :

```python
# Avant (Django API)
self.api_base_url = 'http://localhost:8000/api'

# Après (PostgREST)
self.api_base_url = 'http://localhost:3000'
```

### 2. Configuration du serveur d'authentification

Par défaut, le plugin utilise l'endpoint `auth/signin`. Si votre serveur utilise un autre endpoint, vous pouvez le personnaliser :

```python
def authenticate(self):
    self.authenticator = PostgRESTAuthenticator(self.api_base_url)
    # Personnaliser l'endpoint de login
    token = self.authenticator.authenticate(username, password, login_endpoint="login")
```

## Utilisation du Client PostgREST

### Exemple 1: Authentification

```python
# Initialiser l'authentificateur
authenticator = PostgRESTAuthenticator('http://localhost:3000')

# S'authentifier
token = authenticator.authenticate('user@example.com', 'password')

# Créer un client avec le jeton
postgrest = PostgREST('http://localhost:3000')
postgrest.set_auth_token(token)
```

### Exemple 2: Récupérer des données (SELECT)

```python
# Récupérer tous les enregistrements
communes = postgrest.select('communes')

# Avec filtres
communes = postgrest.select(
    'communes',
    filters={'region': 'eq.Nord'}  # PostgREST filters
)

# Avec pagination
communes = postgrest.select(
    'communes',
    limit=10,
    offset=0
)

# Avec tri
communes = postgrest.select(
    'communes',
    order='nom.asc'
)

# Avec sélection de colonnes
communes = postgrest.select(
    'communes',
    select='id,name,geometry'
)
```

### Exemple 3: Insérer des données (INSERT)

```python
# Insérer un enregistrement
data = {
    'name': 'Nouvelle Commune',
    'region': 'Nord',
    'population': 50000
}
result = postgrest.insert('communes', data)

# Insérer plusieurs enregistrements
data_list = [
    {'name': 'Commune 1', 'region': 'Nord'},
    {'name': 'Commune 2', 'region': 'Sud'},
]
result = postgrest.insert('communes', data_list)
```

### Exemple 4: Mettre à jour des données (PATCH)

```python
# Mettre à jour un enregistrement
data = {'population': 55000}
filters = {'id': 'eq.1'}
result = postgrest.update('communes', data, filters)
```

### Exemple 5: Supprimer des données (DELETE)

```python
# Supprimer un enregistrement
filters = {'id': 'eq.1'}
result = postgrest.delete('communes', filters)
```

### Exemple 6: RPC (Stored Procedures)

```python
# Appeler une fonction PostgREST
params = {'param1': 'value1', 'param2': 123}
result = postgrest.call_rpc('my_function', params)
```

## Syntaxe des Filtres PostgREST

PostgREST utilise une syntaxe spéciale pour les filtres :

```python
# Opérateurs disponibles
filters = {
    'id': 'eq.5',              # égal
    'name': 'neq.foo',         # non égal
    'age': 'gt.18',            # plus grand que
    'age': 'gte.18',           # >= 
    'age': 'lt.65',            # plus petit que
    'age': 'lte.65',           # <=
    'name': 'like.%foo%',      # LIKE SQL
    'name': 'ilike.*foo*',     # ILIKE SQL (case-insensitive)
    'status': 'in.(active,pending)',  # IN SQL
    'data': 'cs.{"a":1}',      # contient JSONB
}
```

## Intégration dans le Plugin

### Charger des données QGIS depuis PostgREST

```python
def load_database_data(self):
    endpoint = self.dockwidget.endpointLineEdit.text().strip()
    
    try:
        # Utiliser le client PostgREST
        db_data = self.postgrest.select(endpoint)
        
        # Créer une couche QGIS
        layer = self.create_vector_layer_from_json(db_data, endpoint)
        QgsProject.instance().addMapLayer(layer)
        
        QMessageBox.information(
            self.iface.mainWindow(),
            'Succès',
            f'{len(db_data)} enregistrements chargés'
        )
    except Exception as exc:
        QMessageBox.critical(self.iface.mainWindow(), 'Erreur', str(exc))
```

### Sauvegarder des modifications dans PostgREST

```python
def save_layer_changes(self, layer_name, feature):
    """Sauvegarde une entité modifiée dans PostgREST"""
    attrs = feature.attributes()
    feature_id = feature[0]  # Premier attribut = ID
    
    # Convertir les attributs en dict
    layer = QgsProject.instance().mapLayerByName(layer_name)
    fields = layer.fields()
    data = {}
    for i, field in enumerate(fields):
        data[field.name()] = attrs[i]
    
    # Mettre à jour dans PostgREST
    filters = {layer.fields()[0].name(): f'eq.{feature_id}'}
    result = self.postgrest.update(layer_name, data, filters)
```

## Configuration pour ProjetsMergin

Pour les projets Mergin, assurez-vous que :

1. Les géométries sont au format GeoJSON
2. Les CRS sont correctement définis (EPSG:32738 pour votre cas)
3. Les données JSON contiennent un champ "geom" avec la géométrie

Exemple de réponse PostgREST avec géométrie :

```json
[
  {
    "id": 308,
    "name": "Commune A",
    "geom": {
      "type": "Polygon",
      "crs": {
        "type": "name",
        "properties": {
          "name": "EPSG:32738"
        }
      },
      "coordinates": [[...]]
    }
  }
]
```

## Dépannage

### Authentification échoue

- Vérifiez que l'endpoint de connexion est correct
- Vérifiez les identifiants
- Vérifiez que le serveur d'authentification est actif

### Requêtes PostgREST échouent avec "Unauthorized"

- Assurez-vous que le jeton JWT est valide
- Vérifiez les permissions dans PostgREST
- Le jeton peut avoir expiré, authentifiez-vous à nouveau

### Pas de données retournées

- Vérifiez le nom de la table
- Vérifiez la syntaxe des filtres
- Vérifiez que vous avez les permissions de lecture

### Les géométries ne chargent pas

- Vérifiez que le champ geom contient un GeoJSON valide
- Vérifiez que le CRS est spécifié correctement
- Vérifiez que les coordonnées sont dans le bon ordre (lon, lat)

## Ressources

- [Documentation PostgREST](https://postgrest.org/)
- [Guide d'authentification PostgREST](https://postgrest.org/en/latest/auth.html)
- [Client Python PostgREST](https://github.com/supabase-community/postgrest-py)

