# WORKFLOW MERGIN MAP - Documentation Complète

## 🎯 Objectif

Automatiser la préparation, le déploiement, et la synchronisation d'un projet **Mergin Map** pour la collecte de données terrain.

```
BUREAU (Avant)   →   TERRAIN (Collecte)   →   BUREAU (Après)
  Préparation    →   Mergin Map (mobile)  →   Validation & Fusion
```

---

## 📋 Workflow en 4 Étapes

### ÉTAPE 1: PRÉPARATION (Bureau)

**Objectif**: Préparer un projet Mergin et exporter les données

```
1. Authentification
   ✓ Se connecter à l'API (Django/PostgREST)
   ✓ Jeton JWT sauvegardé

2. Charger les données
   ✓ Endpoint: data/communes (ou autre table)
   ✓ Données chargées comme couches QGIS

3. Vérifier les données
   ✓ Comparer couches locales vs. base
   ✓ Voir nombre d'enregistrements

4. Préparer Mergin
   ✓ Créer un projet Mergin
   ✓ Exporter données en GeoJSON
   ✓ Créer le formulaire mobile
   ✓ Préparer pour le terrain
```

**Code**:
```python
# 1. Charger données
mgr = MerginWorkflowManager(plugin_dir)
project_id = mgr.create_project("Communes_2026", "communes", "Pointage communes")

# 2. Récupérer données API
communes = postgrest.select('communes')

# 3. Sauvegarder pour export
mgr.save_exported_data(project_id, communes)
```

---

### ÉTAPE 2: EXPORT & MERGIN SETUP

**Objectif**: Préparer le projet Mergin pour le terrain

```
1. Exporter GeoJSON
   communes.geojson → Projet Mergin

2. Configurer formulaire mobile
   ✓ Champs modifiables (nom, etc)
   ✓ Ajouter photos
   ✓ GPS activé

3. Préparer pour terrain
   ✓ QR code du projet
   ✓ Instructions pour équipe terrain
   ✓ Liste de vérification

4. Déployer sur Mergin Cloud
```

**Fichiers générés**:
```
mergin_workflows/projects/{project_id}/
├── metadata.json          (Info projet)
├── exported_data.json     (Données initiales)
├── communes.geojson       (Export GeoJSON)
└── mergin_config.json     (Config mobile)
```

---

### ÉTAPE 3: COLLECTE (Terrain)

**Objectif**: Collecte de données avec Mergin Map

```
Équipe terrain avec Mergin Map:
✓ Charger le projet
✓ Collecter/modifier données
✓ Prendre photos
✓ Valider géométries
✓ Synchro Mergin Cloud

Données dans Mergin:
├── Points collectés (géométries)
├── Attributs modifiés
├── Albums photos
└── Journal de changements
```

**Pas d'action dans le plugin** - Équipe terrain gère

---

### ÉTAPE 4: VALIDATION & FUSION (Bureau)

**Objectif**: Vérifier et fusionner les données retournées

```
1. Charger les données collectées
   ✓ Télécharger de Mergin Cloud
   ✓ Chargées comme couche QGIS

2. FORMULAIRE DE VALIDATION
   ✓ Vue d'ensemble (nouveau, modifié, supprimé)
   ✓ Compar avant/après
   ✓ Validation ligne par ligne
   ✓ Résoudre conflits

3. Approuver les changements
   ✓ Sélectionner stratégie fusion
   ✓ Valider les données
   ✓ Générer rapport

4. FUSION avec base de données
   ✓ Insérer nouveaux enregistrements
   ✓ Mettre à jour modifiés
   ✓ Archiver supprimés
   ✓ Backup automatique

5. SYNCHRONISATION API
   ✓ Pousser vers Django/PostgREST
   ✓ Mettre à jour la base
   ✓ Générer rapport final
```

---

## 🔄 Flux Complet dans le Plugin

### Interface Dock Widget

```
┌─────────────────────────────────────┐
│  🔐 user@example.com @ localhost     │
├─────────────────────────────────────┤
│                                      │
│  WORKFLOW MERGIN MAP                 │
│  ════════════════════               │
│                                      │
│  [1] PRÉPARATION                     │
│  ├─ Endpoint: ........................ │
│  ├─ [📥 Charger données DB]         │
│  ├─ [🔄 Comparer couches/base]      │
│  └─ Résultats: .....................  │
│                                      │
│  [2] EXPORT MERGIN                   │
│  ├─ Endpoint Mergin: ................ │
│  ├─ [📤 Préparer Mergin]          │
│  └─ Statut: ......................... │
│                                      │
│  [3] COLLECTE TERRAIN                │
│  └─ Mergin Map (mobile)             │
│                                      │
│  [4] VALIDATION & FUSION             │
│  ├─ [📋 Charger données collectées]  │
│  ├─ [✓ Valider & Fusionner]        │
│  └─ Rapport: ........................ │
│                                      │
└─────────────────────────────────────┘
```

---

## 💻 Code d'Utilisation

### Initialisation

```python
from mergin_workflow_manager import MerginWorkflowManager, MerginDataMerger

# 1. Créer manager
mgr = MerginWorkflowManager(plugin_dir)

# 2. Créer project
project_id = mgr.create_project(
    "Communes",
    "communes",
    "Collecte communes 2026"
)
# → "Communes_20260426_152345"
```

### ÉTAPE 1: Préparation

```python
# Charger données API
communes = postgrest.select('communes')

# Sauvegarder pour export
mgr.save_exported_data(project_id, communes)
# → Stage 2: Export

# Dans metadata.json: stage = 2
```

### ÉTAPE 2: Export

```python
# Créer le fichier Mergin
export_file = os.path.join(plugin_dir, 'export.geojson')
with open(export_file, 'w') as f:
    json.dump(communes, f)

# Préparer pour Mergin Cloud
# (Actions manuelles ou via Mergin API)
```

### ÉTAPE 4: Validation & Fusion

```python
# 1. Charger les données collectées
from mergin_map_loader import load_mergin_project  # Hypothétique

collected = load_mergin_project(project_id)
mgr.import_collected_data(project_id, collected)
# → Stage 4: Imported

# 2. Afficher formulaire de validation
from validation_dialog import DataValidationDialog

dialog = DataValidationDialog(
    collected_data=collected,
    original_data=communes
)

if dialog.exec_():
    validated = dialog.validated_data
    
    # 3. Fusionner
    merger = MerginDataMerger(postgrest)
    results = merger.merge(
        'communes',
        communes,
        validated,
        strategy='merge'
    )
    mgr.merge_data(project_id, results)
    # → Stage 6: Fusion
    
    # 4. Synchroniser API
    for action in results['actions']:
        if action['type'] == 'updated':
            postgrest.update('communes', action['data'])
        elif action['type'] == 'inserted':
            postgrest.insert('communes', action['data'])
    
    mgr.sync_to_api(project_id, sync_results)
    # → Stage 7: Synchronisation
```

---

## 📊 Fichiers Générés

### Structure Répertoire

```
plugin_dir/
├── mergin_workflows/
│   ├── projects/
│   │   └── Communes_20260426_152345/
│   │       ├── metadata.json          ← Métadonnées projet
│   │       ├── exported_data.json     ← Données initiales
│   │       ├── imported_data.json     ← Données collectées
│   │       ├── validation_results.json ← Résultats validation
│   │       ├── merge_results.json     ← Résultats fusion
│   │       └── sync_results.json      ← Résultats API
│   └── backups/
│       └── Communes_20260426_152345/
│           ├── imported_data_20260426_160000.json
│           └── ...
└── mergin_ready_data.json
```

### Exemple metadata.json

```json
{
  "id": "Communes_20260426_152345",
  "name": "Communes",
  "source_table": "communes",
  "description": "Collecte communes 2026",
  "created": "2026-04-26T15:23:45",
  "stage": 7,
  "stages_completed": [1, 2, 4, 5, 6, 7]
}
```

---

## 🔍 Détection de Conflits

### Automatique

```
1. SUPPRIMÉS
   ID dans original mais PAS dans collected

2. AJOUTÉS
   ID dans collected mais PAS dans original

3. MODIFIÉS
   Même ID mais données différentes
```

### Exemple

```json
{
  "type": "modified",
  "id": 5,
  "original": {
    "id": 5,
    "nom": "ANDOHAKABE",
    "population": 5000
  },
  "collected": {
    "id": 5,
    "nom": "ANDOHAKABE",
    "population": 5500    ← CHANGÉ
  }
}
```

---

## ✅ Stratégies de Fusion

### 1. Merge (Recommandée)

```
Nouveau     → INSERT
Modifié     → UPDATE
Supprimé    → Archiver (soft delete)
```

### 2. Replace (Complète)

```
Tous anciens → DELETE
Tous nouveaux → INSERT
```

### 3. Manual (Cas par cas)

```
Humain décide pour chaque changement
```

---

## 📈 Workflow État Complet

```python
# Vérifier l'état d'un projet
info = mgr.get_project_info(project_id)
print(info['stage'])  # 1-7

# Lister tous les projets
projects = mgr.list_projects()
for p in projects:
    print(f"{p['name']}: Stage {p['stage']}")

# Générer rapport
report = mgr.generate_workflow_report(project_id)
print(json.dumps(report, indent=2))

# Exporter rapport
file = mgr.export_report_to_file(project_id)
```

---

## 🎓 Cas d'Usage

### Cas 1: Collecte Simples Communes

```
1. Bureau: Charger 1000 communes
2. Terrain: Vérifier 800, en ajouter 50
3. Bureau: Valider + fusionner 50 nouveaux
```

### Cas 2: Modification Massive Arbres

```
1. Bureau: Charger 5000 arbres
2. Terrain: Modifier 200 géométries + attributs
3. Bureau: Valider + mettre à jour DB
```

### Cas 3: Collecte Avec Photos

```
1. Bureau: Préparer formulaire + champs photos
2. Terrain: Collecter 500 points + photos
3. Bureau: Valider + archiver photos
```

---

## 🚨 Gestion des Erreurs

### Conflits de Fusion

```
SI conflit détecté:
  ✓ Affiche données conflictuelles
  ✓ Propose action (Keep/Replace/Manual)
  ✓ Utilisateur décide
  ✓ Procède exclusivité
```

### Sauvegarde Automatique

```
Avant chaque étape:
1. Backup données originales
2. Sauvegarder dans backups/
3. Permettre rollback
```

---

## 📞 Support

| Situation | Solution |
|-----------|----------|
| Données ne se chargent pas | Vérifier authentification + endpoint |
| Conflit de fusion | Afficher validation dialog |
| API refuse update | Vérifier permissions PostgREST |
| Photos non synchronisées | Vérifier Mergin Cloud |

---

## 🔗 Fichiers Liés

- `mergin_workflow_manager.py` - Logic Workflow
- `validation_dialog.py` - UI Validation
- `postgrest_client.py` - API Communications
- `mrv_teraka.py` - Plugin principal
- `mrv_teraka_dockwidget.py` - UI Dock


