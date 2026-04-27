# 🔍 ANALYSE COMPLÈTE DES LOGIQUES - Plugin MrvTeraka

**Date:** 2026-04-27  
**Version:** 2.0 (avec modifications utilisateur)  
**Tables mappées:** 76

---

## 📊 APERÇU EXÉCUTIF

Le plugin MrvTeraka est un **système complet d'automatisation multi-tables** basé sur PostgREST et Mergin Map pour la collecte, validation et fusion de données géospatiales au terrain.

### 🎯 Objectif Principal
Automatiser le cycle complet: **Préparation → Terrain → Validation → Fusion → Sync**

### 📈 Statistiques
- **76 tables** mappées dans PostgREST
- **1 projet QGIS** de base chargé automatiquement
- **7 étapes** du workflow Mergin complètement automatisées
- **4 onglets** de validation avec détection de conflits
- **100% compatible** avec Django/PostgREST

---

## 🗺️ FLUX GLOBAL (7 ÉTAPES)

```
ÉTAPE 1: PRÉPARATION (Bureau)
   ↓
   ├─ Authentification JWT (token_manager.py + auth_dialog.py)
   ├─ Chargement projet QGIS par défaut
   ├─ Chargement des mappings (76 tables)
   ├─ Migration des sources vers API (layer_table_mapping.json)
   └─ Comparaison QGIS ↔ API
   
ÉTAPE 2: EXPORT → Mergin
   ↓
   ├─ Sélectionner les tables à exporter
   ├─ Créer projet Mergin (mergin_manager)
   ├─ Exporter données actuelles (JSON)
   └─ Préparer formulaire mobile
   
ÉTAPE 3: COLLECTE (Terrain) 💻→📱
   ↓
   └─ Mergin Map mobile (manuel)
   
ÉTAPE 4: IMPORTATION (Bureau)
   ↓
   ├─ Charger les données collectées
   ├─ Importer dans fichier local
   └─ Marquer prêt pour validation
   
ÉTAPE 5: VALIDATION ⭐ (Bureau)
   ↓
   ├─ Dialog: 4 onglets
   ├─ Afficher données collectées
   ├─ Comparaison avant/après
   ├─ Validation ligne par ligne
   └─ Actions: Auto/Manual/Report
   
ÉTAPE 6: FUSION (Bureau)
   ↓
   ├─ Détecter conflicts (MerginDataMerger)
   ├─ INSERT/UPDATE/DELETE
   ├─ Backup automatique
   └─ Rapport généré
   
ÉTAPE 7: SYNCHRONISATION (Backend)
   ↓
   └─ Mise à jour API PostgREST
```

---

## 🔑 LOGIQUES PRINCIPALES

### 1️⃣ AUTHENTIFICATION & CONFIGURATION

**Fichiers:** `auth_dialog.py`, `token_manager.py`, `config_postgrest.py`

```
FLUX:
├─ Plugin startup
├─ → load_saved_token()
│   └─ QSettings('iTeraka', 'MrvTeraka')
│      ├─ token/jwt → JWT Token
│      ├─ token/url → API URL
│      ├─ token/mode → Django/PostgREST
│      └─ token/expiry → Timestamp
│
├─ Si pas de token valide
│   └─ show_auth_dialog()
│      ├─ Saisie: username, password, url, mode
│      ├─ PostgRESTAuthenticator.authenticate()
│      │  └─ POST /api/auth/signin (Django)
│      │  └─ POST /auth/signin (PostgREST)
│      └─ Sauvegarder token et URL
│
└─ Token valide
   └─ Charger Project QGIS
   └─ Charger Mappings
   └─ UI prête
```

**Code clé (mrv_teraka.py:208-222):**
```python
def load_saved_token(self):
    token, api_url, mode = self.token_manager.load_token()
    if token and api_url:
        self.postgrest = PostgREST(api_url, mode=PostgRESTMode[mode.upper()])
        self.postgrest.set_auth_token(token)
        self.update_auth_ui()
```

---

### 2️⃣ CHARGEMENT AUTOMATIQUE DU PROJET QGIS

**Fichiers:** `mrv_teraka.py`  
**Clé:** Ligne 224-238

```
FLUX:
├─ initGui() appelé
│  └─ open_default_qgis_project()
│
├─ self.default_project_file = 'Q_v17_7_7_ITASY2026_WP.qgz'
│
├─ Si fichier existe
│  └─ QgsProject.instance().read(file)
│     └─ Charge 76 couches
│
├─ Mettre à jour les sources
│  └─ migrate_project_layers_to_api()
│
└─ Interface prête avec 76 couches actives
```

**Code clé (mrv_teraka.py:224-238):**
```python
def open_default_qgis_project(self):
    if os.path.exists(self.default_project_file):
        if not QgsProject.instance().read(self.default_project_file):
            QMessageBox.warning(...)
```

---

### 3️⃣ MAPPING MULTI-TABLES

**Fichiers:** `layer_table_mapping.json`, `config_postgrest.py`  
**Tables:** 76 mappées

```
STRUCTURE (layer_table_mapping.json):
{
  "mappings": {
    "1-Petit_Groupe": {
      "endpoint": "1_petit_groupe",
      "geom_field": "geom",
      "pk_field": "id"
    },
    ... (73 autres tables)
    "users": {
      "endpoint": "users",
      "geom_field": "geom",
      "pk_field": "id"
    }
  }
}

NORMALISATION (config_postgrest.py):
├─ normalize_layer_name_to_endpoint()
│  └─ "1-Petit Groupe" → "1_petit_groupe"
│
├─ normalize_layer_mapping()
│  └─ Valider structure mapping
│
└─ load_layer_mapping()
   └─ Charger depuis JSON + cache
```

**Code clé (config_postgrest.py:16-45):**
```python
def normalize_layer_name_to_endpoint(layer_name: str) -> str:
    value = layer_name.strip().lower()
    value = value.replace(' ', '_').replace('-', '_')
    value = re.sub(r'[^a-z0-9_]', '_', value)
    return value
```

---

### 4️⃣ MIGRATION DES SOURCES → API

**Fichiers:** `mrv_teraka.py`  
**Méthode:** `migrate_project_layers_to_api()` (ligne 323-365)

```
FLUX:
├─ get_project_layer_endpoints()
│  └─ Parcourir toutes les couches QGIS
│  └─ Récupérer mapping de chacune
│
├─ Pour chaque couche
│  ├─ Charger données API: postgrest.select(endpoint)
│  ├─ Créer couche mémoire: create_vector_layer_from_json()
│  ├─ Ajouter propriétés personnalisées:
│  │  ├─ 'postgrest:endpoint' → "1_petit_groupe"
│  │  ├─ 'postgrest:geom_field' → "geom"
│  │  └─ 'postgrest:pk_field' → "id"
│  └─ Remplacer source dans QGIS
│
└─ Rapport utilisateur
```

**Code clé (mrv_teraka.py:341-358):**
```python
for layer_name, mapping in project_endpoints.items():
    db_data = self.postgrest.select(mapping['endpoint'])
    layer = self.create_vector_layer_from_json(db_data, layer_name)
    if layer and layer.isValid():
        layer.setCustomProperty('postgrest:endpoint', mapping['endpoint'])
        layer.setCustomProperty('postgrest:geom_field', mapping.get('geom_field'))
        new_layers.append((layer_name, layer))
```

---

### 5️⃣ CRÉATION DE COUCHES VECTORIELLES

**Fichiers:** `mrv_teraka.py`  
**Méthode:** `create_vector_layer_from_json()` (ligne 525-613)

```
FLUX DE CRÉATION:
├─ Détecter type géométrie
│  ├─ Chercher champ 'geom' dans données
│  ├─ Lire type GeoJSON: Point/LineString/Polygon
│  └─ Créer URI: f"{geom_type}?crs={crs}"
│
├─ Détecter CRS
│  ├─ CRS_1: Dans l'objet géométrie (priorité haute)
│  │   └─ geom.crs.properties.name → "EPSG:32738"
│  ├─ CRS_2: Au niveau global (fallback)
│  │   └─ data.crs → "EPSG:32738"
│  └─ CRS_3: Par défaut
│      └─ "EPSG:4326"
│
├─ Créer couche QGIS mémoire
│  ├─ QgsVectorLayer(uri, name, "memory")
│  ├─ Ajouter tous les champs (sauf geom)
│  └─ updateFields()
│
├─ Ajouter features
│  ├─ Pour chaque objet JSON
│  │  ├─ Créer QgsFeature
│  │  ├─ setAttributes(columns)
│  │  ├─ Parser GeoJSON → QgsGeometry
│  │  └─ setGeometry()
│  └─ addFeatures()
│
└─ Retourner layer valide
```

**Code clé - Détection CRS (mrv_teraka.py:538-565):**
```python
# 1. CRS dans la géométrie (priorité haute)
if geom_key and isinstance(sample.get(geom_key), dict):
    geom_obj = sample[geom_key]
    crs_info = geom_obj.get("crs")
    if crs_info and crs_info.get("type") == "name":
        crs_name = crs_info["properties"]["name"]
        if "EPSG" in crs_name.upper():
            code = crs_name.split(":")[-1]
            crs = f"EPSG:{code}"
```

---

### 6️⃣ PRÉPARATION MERGIN (Export)

**Fichiers:** `mrv_teraka.py`, `mergin_workflow_manager.py`  
**Méthode:** `prepare_mergin_project()` (ligne 717-770)

```
FLUX:
├─ Sélectionner endpoints à exporter
│  └─ get_requested_endpoints()
│     ├─ Si endpoint spécifié: [endpoint]
│     └─ Sinon: Toutes les couches du projet
│
├─ Pour chaque endpoint
│  ├─ Charger données: postgrest.select(endpoint)
│  └─ Construire payload
│
├─ Créer projet Mergin
│  ├─ project_name: 'mergin_YYYYMMDD_HHMMSS'
│  ├─ description: "Collecte terrain - Table1, Table2..."
│  └─ self.current_project_id = UUID généré
│
├─ Sauvegarder données
│  ├─ mergin_manager.save_exported_data()
│  └─ Fichier: {project_id}/exported_data.json
│
└─ Notification utilisateur
   └─ "Prêt pour Mergin Map!"
```

**Code clé (mrv_teraka.py:732-744):**
```python
export_payload = {}
for layer_name, mapping in requested_endpoints.items():
    endpoint_value = mapping['endpoint']
    export_payload[endpoint_value] = self.postgrest.select(endpoint_value)

project_name = 'mergin_' + datetime.now().strftime('%Y%m%d_%H%M%S')
self.current_project_id = self.mergin_manager.create_project(
    project_name,
    ','.join([mapping['endpoint'] for mapping in requested_endpoints.values()]),
    project_description
)
```

---

### 7️⃣ VALIDATION DES DONNÉES (Dialog)

**Fichiers:** `validation_dialog.py`  
**Classe:** `DataValidationDialog` (4 onglets)

```
ONGLETS:

1️⃣ VUE D'ENSEMBLE
   ├─ Statistiques
   │  ├─ Nombre de nouveaux enregistrements
   │  ├─ Nombre modifiés
   │  └─ Nombre supprimés
   ├─ Recommandations auto
   └─ Visuel: Progress bar

2️⃣ DONNÉES COLLECTÉES
   ├─ Tableau complet des données
   ├─ Tous les champs affichés
   ├─ Éditable
   └─ Export possible

3️⃣ COMPARAISON
   ├─ Données originales vs collectées
   ├─ Mise en évidence des différences
   ├─ Code couleur:
   │  ├─ Vert: Identiques
   │  ├─ Orange: Modifiés
   │  ├─ Bleu: Nouveaux
   │  └─ Rouge: Supprimés

4️⃣ VALIDATION (Ligne par ligne)
   ├─ Formulaire detail pour chaque ligne
   ├─ Champs automatiquement remplis
   ├─ Modifier si nécessaire
   ├─ Accepter/Refuser ligne
   └─ Détection conflits auto

BOUTONS:
├─ 🔄 Fusion Automatique (stratégie par défaut)
├─ 👁️ Révision Manuelle (validation complète)
├─ 📊 Exporter Rapport (JSON)
├─ [Annuler]
└─ [✓ Valider et Fusionner]
```

**Code clé (validation_dialog.py:19-100):**
```python
class DataValidationDialog(QDialog):
    def __init__(self, parent=None, collected_data=None, original_data=None):
        self.collected_data = collected_data or []
        self.original_data = original_data or []
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_overview_tab(), "Vue d'ensemble")
        self.tabs.addTab(self.create_collected_tab(), "Données Collectées")
        self.tabs.addTab(self.create_comparison_tab(), "Comparaison")
        self.tabs.addTab(self.create_validation_tab(), "Validation")
```

---

### 8️⃣ FUSION INTELLIGENTE

**Fichiers:** `mrv_teraka.py`, `mergin_workflow_manager.py`  
**Méthode:** `merge_validated_data()` (ligne 909-947)

```
FLUX DE FUSION:
├─ Charger données originales
│  └─ exported_data.json (backup)
│
├─ Détecter conflicts
│  ├─ MerginDataMerger.detect_conflicts()
│  ├─ Comparer par pk_field (id)
│  ├─ Catégoriser:
│  │  ├─ ADDED: ID dans validated mais pas original
│  │  ├─ DELETED: ID dans original mais pas validated
│  │  ├─ MODIFIED: ID existe mais attributs changés
│  │  └─ UNCHANGED: Identiques
│  │
│  └─ Retourner liste conflicts
│
├─ Afficher résumé
│  ├─ "🆕 Ajoutés: 45"
│  ├─ "✏️ Modifié: ID 123"
│  ├─ "🗑️ Supprimés: 2"
│  └─ "Procéder? [Oui] [Non]"
│
├─ Si Oui
│  ├─ MerginDataMerger.merge()
│  ├─ Pour chaque conflit
│  │  ├─ INSERT: postgrest.insert()
│  │  ├─ UPDATE: postgrest.update()
│  │  ├─ DELETE: postgrest.delete()
│  │  └─ Log action
│  │
│  ├─ Backup original
│  │  └─ backend_backup_{timestamp}.json
│  │
│  ├─ Générer rapport
│  │  ├─ merge_results.json
│  │  ├─ Lists modifications
│  │  └─ Statut succès
│  │
│  └─ Afficher résultats
│     └─ "Fusion réussie! 127 actions"
│
└─ Si Non
   └─ Annuler et revenir
```

**Code clé (mrv_teraka.py:909-941):**
```python
def merge_validated_data(self, mapping, original, validated):
    table = mapping.get('endpoint')
    pk_field = mapping.get('pk_field', 'id')
    merger = MerginDataMerger(self.postgrest)
    
    # Détect conflicts
    conflicts = merger.detect_conflicts(original, validated, pk_field=pk_field)
    
    # Afficher résumé
    summary = self.generate_merge_summary(conflicts)
    
    reply = QMessageBox.question(
        self.iface.mainWindow(),
        "Confirmation Fusion",
        f"Résumé des changements:\n{summary}\n\nProcéder?"
    )
    
    if reply == QMessageBox.Yes:
        merge_results = merger.merge(table, original, validated, strategy='merge')
```

---

## 🎯 INTERACTIONS CLÉ

### Flux: Utilisateur charge TOUTES les données

```
Utilisateur clique "Charger données DB"
    ↓
load_database_data()
    ↓
get_requested_endpoints()
    ├─ endpoint_text vide?
    │   └─ Oui: get_project_layer_endpoints()
    │           └─ Retourner toutes les couches (76)
    │   └─ Non: Endpoint spécifique
    │
├─ Pour chaque endpoint
│   ├─ postgrest.select(endpoint)
│   ├─ create_vector_layer_from_json()
│   ├─ setCustomProperty('postgrest:endpoint', endpoint)
│   └─ QgsProject.instance().addMapLayer(layer)
│
└─ Afficher: "Des couches API ont été chargées"
```

### Flux: Utilisateur lance Mergin

```
Clic: [Préparer données Mergin]
    ↓
prepare_mergin_project()
    ↓
get_requested_endpoints()
    ├─ Récupérer todos endpoints
    │
├─ Créer payload export
│   ├─ Pour chaque endpoint
│   └─ fetch + assemble JSON
│
├─ MerginWorkflowManager.create_project()
│   ├─ Générer UUID: current_project_id
│   │
│   └─ Créer dossier:
│       mergin_workflows/projects/{project_id}/
│
├─ save_exported_data()
│   └─ Sauvegarder: exported_data.json
│
└─ Message envoyé:
   "Prêt pour terrain! ID: {UUID}"
```

### Flux: Utilisateur valide après terrain

```
Clic: [Charger collectes]
    ↓
load_collected_data()
    ↓
├─ Charger imported_data.json
│   └─ Données retour du terrain
│
├─ Charger exported_data.json
│   └─ Données pré-terrain (backup)
│
├─ Afficher DataValidationDialog
│   ├─ Onglet 1: Vue d'ensemble
│   ├─ Onglet 2: Données collectées
│   ├─ Onglet 3: Comparaison
│   └─ Onglet 4: Validation
│
├─ Utilisateur validates
│   └─ Clique [✓ Valider et Fusionner]
│
├─ Dialog.accept() → get self.validated_data
│
├─ merge_validated_data()
│   ├─ detect_conflicts()
│   ├─ Afficher résumé
│   ├─ Demander confirmation
│   ├─ Si Oui:
│   │   ├─ POST/PATCH/DELETE via API
│   │   ├─ Sauvegarder rapport
│   │   └─ "Fusion réussie!"
│   └─ sync_to_api()
│
└─ État API mis à jour!
```

---

## 📁 STRUCTURE FICHIERS GÉNÉRÉS

```
Plugin Directory
├─ Q_v17_7_7_ITASY2026_WP.qgz  ← Projet QGIS chargé auto
├─ layer_table_mapping.json    ← 76 tables mappées
├─ config_postgrest.py         ← Normalisation
│
└─ mergin_workflows/           ← Générés au runtime
   ├─ projects/
   │   └─ {project_id}/        ← UUID unique
   │       ├─ metadata.json
   │       ├─ exported_data.json
   │       ├─ imported_data.json
   │       ├─ validation_results.json
   │       ├─ merge_results.json
   │       └─ sync_results.json
   │
   └─ backups/
       └─ {project_id}/
           ├─ exported_data_backup.json
           └─ backend_backup_YYYYMMDD_HHMMSS.json
```

---

## 🔐 SÉCURITÉ & PERSISTANCE

### Token Management
```
Sauvegarde: QSettings('iTeraka', 'MrvTeraka')
├─ platform: Windows → HKEY_CURRENT_USER\...\MrvTeraka
├─ platform: Linux → ~/.config/iTeraka/MrvTeraka.conf
├─ platform: macOS → ~/Library/Preferences/com.iTeraka.MrvTeraka.plist

Clés:
├─ token/jwt → Token JWT (28800s = 8h)
├─ token/url → URL API
├─ token/mode → 'django' ou 'standalone'
├─ token/expiry → Timestamp
├─ auth/last_username → Dernier user (pour UI)
└─ auth/remember_me → Boolean

Validation:
├─ is_token_valid()
│  ├─ Token existe?
│  ├─ Pas expiré? (check timestamp)
│  └─ Retourner bool
│
└─ Si expiré
   └─ Demander re-auth
```

---

## 🚀 CAS D'USAGE COMPLETS

### Cas 1: Collecte Arbre (3-Arbre table)

```
SETUP:
├─ Table: 3-Arbre → endpoint: 3_arbre
├─ 1000 arbres en base
├─ CRS: EPSG:32738

WORKFLOW:
1. Bureau (initGui)
   ├─ load_saved_token()
   ├─ open_default_qgis_project()
   ├─ migrate_project_layers_to_api()
   └─ UI Dock affiche "● Connecté"

2. Bureau (Préparation)
   ├─ Clic: "Charger données DB"
   ├─ Charge toutes 76 tables
   ├─ Visualise "3-Arbre" layer
   └─ 1000 points affichés

3. Bureau (Export)
   ├─ Clic: "Préparer données Mergin"
   ├─ Crée projet: mergin_20260427_143022
   ├─ Export: 1000 arbres
   └─ Prêt terrain

4. Terrain (Mergin Map)
   ├─ Sync bidi avec API
   ├─ Collecte:
   │   ├─ Modification: Arbre #42 → diamètre changé
   │   ├─ Suppression: Arbre #99 supprimé
   │   └─ Ajout: 5 nouveaux arbres
   ├─ Photos géolocalisées
   └─ Sync nuages

5. Bureau (Import)
   ├─ Clic: "Charger collectes"
   ├─ Import: 1005 arbres (orig: 1000)
   !== Status: 5 nouveaux, 1 modifié, 1 supprimé

6. Bureau (Validation)
   ├─ Affiche DataValidationDialog
   ├─ Onglet Stats: +5 ajoutés, ✏️ 1 modifié, 🗑️ 1 supprimé
   ├─ Onglet Données: Tableau complet
   ├─ Onglet Comparaison: Visuels changements
   ├─ Onglet Validation: Chaque ligne à signer
   └─ Clic: "Fusion Automatique"

7. Bureau (Fusion)
   ├─ DetectConflicts:
   │   ├─ 5 INSERT
   │   ├─ 1 UPDATE
   │   └─ 1 DELETE
   ├─ Affiche résumé
   ├─ Confirmation: [Oui]
   ├─ Merge:
   │   ├─ POST /api/3_arbre (5 nouveaux)
   │   ├─ PATCH /api/3_arbre (ID 42)
   │   ├─ DELETE /api/3_arbre (ID 99)
   │   └─ Backup créé
   └─ "Fusion réussie! 7 actions"

8. Backend Sync
   └─ API mise à jour → 1005 arbres
```

---

## 🔧 MAINTENANCE & DEBUG

### Vérification Mappings
```python
# Charger manual
from config_postgrest import load_layer_mapping
mappings = load_layer_mapping('/path/to/plugin')
print(f"Loaded: {len(mappings)} tables")

# Voir mapping d'une table
mapping = mappings.get("3-Arbre")
print(f"Endpoint: {mapping['endpoint']}")
print(f"GeomField: {mapping['geom_field']}")
print(f"PKField: {mapping['pk_field']}")
```

### Vérification Token
```python
# Charger manuel
from token_manager import TokenManager
mgr = TokenManager()
token, url, mode = mgr.load_token()
print(f"Token valide: {mgr.is_token_valid()}")
print(f"URL: {url}")
print(f"Mode: {mode}")
```

### Test API
```python
# Tester connection
from postgrest_client import PostgREST, PostgRESTMode
pg = PostgREST('http://localhost:8000', mode=PostgRESTMode.DJANGO)
pg.set_auth_token(token)
data = pg.select('3_arbre', limit=5)
print(f"Got {len(data)} records")
```

---

## 📊 STATISTIQUES ACTUELLES

| Métrique | Valeur |
|----------|--------|
| **Tables mappées** | 76 |
| **Projet QGIS** | 1 (Q_v17_7_7_ITASY2026_WP.qgz) |
| **Étapes workflow** | 7 |
| **Onglets validation** | 4 |
| **Lignes code** | 980+ (mrv_teraka.py) |
| **Modes API** | 2 (Django/PostgREST) |
| **CRS détectés** | Dynamique (dans data) |
| **Backup auto** | Oui |
| **Transactions API** | Batch support |

---

## ✅ CHECKLIST LOGIQUES

- ✅ Authentification JWT complète
- ✅ Chargement projet auto
- ✅ 76 tables mappées
- ✅ Migration auto vers API
- ✅ Créations couches dynamiques
- ✅ Détection CRS auto
- ✅ Workflow Mergin 7 étapes
- ✅ Validation 4 onglets
- ✅ Détection conflits auto
- ✅ Fusion multi-stratégies
- ✅ Backup automatique
- ✅ Support Django & PostgREST
- ✅ Persistance QSettings
- ✅ Rapport JSON

---

## 🎯 PROCHAINES OPTIMISATIONS POSSIBLES

1. **Cache des données** (Redis)
2. **Pagination automatique** (tables > 10k lignes)
3. **Export template** (Mergin)
4. **Webhooks** (notifications temps réel)
5. **Historique complet** (version control)
6. **Multi-utilisateur** (gestion sessions)
7. **Performance** (parallel API calls)

---

**FIN DE L'ANALYSE**

---

*Plugin MrvTeraka - Logiques Complètes*  
*2026-04-27 - Analyse v2.0*

