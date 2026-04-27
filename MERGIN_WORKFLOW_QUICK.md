# 🎯 RÉSUMÉ RAPIDE - Workflow Mergin Map Plugin MrvTeraka

## Objectif Principal

**Automatiser le cycle complet de terrain Mergin Map:**

```
1. Bureau (Avant)   → 2. Terrain (Mergin)   → 3. Bureau (Après)
   Préparation         Collecte               Validation + Fusion
```

---

## ✨ Nouvelles Fonctionnalités Ajoutées

### 1️⃣ **Gestionnaire de Workflow Mergin** (`mergin_workflow_manager.py`)

Suivi automatique du projet à travers 7 étapes:

```
1. Préparation     → 2. Export         → 3. Collecte
                      ↓
4. Importé ← 5. Validation ← 6. Fusion ← 7. Synchronisé
```

**Code d'utilisation**:
```python
mgr = MerginWorkflowManager(plugin_dir)

# Créer un projet
project_id = mgr.create_project("Communes", "communes")

# Chaque étape
mgr.save_exported_data(project_id, data)     # Étape 2
mgr.import_collected_data(project_id, data)  # Étape 4
mgr.validate_data(project_id, results)       # Étape 5
mgr.merge_data(project_id, merge_results)    # Étape 6
mgr.sync_to_api(project_id, sync_results)    # Étape 7
```

**Fichiers générés**:
```
mergin_workflows/projects/{project_id}/
├── metadata.json
├── exported_data.json
├── imported_data.json
├── validation_results.json
├── merge_results.json
└── sync_results.json
```

---

### 2️⃣ **Formulaire de Validation Avancé** (`validation_dialog.py`)

Interface complète pour vérifier les données collectées:

```
┌─────────────────────────────────────┐
│ Validation des Données Collectées   │
├─────────────────────────────────────┤
│  📊 [Vue d'ensemble]                │
│  📋 [Données Collectées]            │
│  🔄 [Comparaison Avant/Après]       │
│  ✓ [Validation Détaillée]          │
├─────────────────────────────────────┤
│ Résumé:                            │
│ • 🆕 Ajoutés: 15                   │
│ • ✏️ Modifiés: 5                   │
│ • 🗑️ Supprimés: 2                  │
├─────────────────────────────────────┤
│ [🔄 Auto] [👁️ Manual] [📊 Report]   │
│ [❌ Cancel]         [✓ Valider]     │
└─────────────────────────────────────┘
```

**Onglets**:
- **Vue d'ensemble**: Statistiques, recommandations
- **Données collectées**: Tableau complet
- **Comparaison**: Avant vs Après
- **Validation**: Ligne par ligne + actions

---

### 3️⃣ **Merge Intelligent** (`MerginDataMerger`)

Détecte et fusionne intelligemment:

```python
merger = MerginDataMerger(postgrest)

# Détecter conflits
conflicts = merger.detect_conflicts(original, collected)
# → Retourne: supprimés, ajoutés, modifiés

# Fusionner
results = merger.merge(
    table='communes',
    original=original_data,
    collected=collected_data,
    strategy='merge'  # ou 'replace' ou 'manual'
)
# → Ajoute, Met à jour, Archive
```

**Stratégies**:
- `merge`: Fusionner intelligemment (défaut)
- `replace`: Remplacer tout
- `manual`: Cas par cas

---

### 4️⃣ **Nouvelles Méthodes Plugin**

Dans `mrv_teraka.py`:

```python
# Charger et valider les données collectées
plugin.load_collected_data()

# Fusionner après validation
plugin.merge_validated_data(table, original, validated)

# Générer résumé des changements
plugin.generate_merge_summary(conflicts)
```

---

## 🔄 Workflow Complet dans le Plugin

### ÉTAPE 1: PRÉPARATION (Bureau)

```
✓ Se connecter → API authentifiée
✓ Charger → Données de la table
✓ Comparer → Couches QGIS vs API
✓ Préparer → Export pour Mergin
```

**Dans le plugin**:
```python
1. Cliquer [Connexion]
2. Entrer identifiants
3. Cliquer [Charger données DB]
4. Cliquer [Comparer couches/base]
5. Cliquer [Préparer Mergin]
→ Fichier mergin_ready_data.json créé
→ Projet Mergin créé dans workflows/
```

---

### ÉTAPE 2-3: EXPORT & TERRAIN

```
✓ Exporter GeoJSON → Mergin Map
✓ Équipe terrain collecte en mobile
✓ Synchro Mergin Cloud
```

**Actions manuelles**:
- Télécharger `mergin_ready_data.json`
- Créer/charger projet dans Mergin Map
- Collecte sur le terrain
- Synchroniser collecte avec Mergin Cloud

---

### ÉTAPE 4: RETOUR & VALIDATION

```
✓ Charger données collectées → Formulaire validation
✓ Comparer avant/après → Détecter changements
✓ Valider ligne par ligne → Décider actions
✓ Fusionner → Mettre à jour API
```

**Dans le plugin**:
```python
1. Télécharger données collectées
2. Cliquer [Charger données collectées]
  → Formulaire validation
  → Affiche: Total, New, Modified, Deleted
  → Onglets: Vue d'ensemble, Comparaison, Validation
3. Choisir stratégie:
   - Fusion Auto (Recommandée)
   - Révision Manuelle
   - Exporter Rapport
4. Cliquer [Valider et Fusionner]
  → Données fusionnées dans API
  → Projet marqué comme complété
```

---

## 📊 Exemple Complet

### Scénario: Collecte 50 Nouvelles Communes

**AVANT (Bureau)**:
```python
# 1. Charger 1000 communes
communes = postgrest.select('communes')

# 2. Préparer Mergin
project_id = mgr.create_project("Communes_2026", "communes")
mgr.save_exported_data(project_id, communes)

# Exporter le JSON
# → Équipe terrain reçoit le fichier
```

**TERRAIN**:
```
Équipe terrain avec Mergin Map:
• Charge le projet
• Ajoute 50 nouvelles communes
• Prend photos
• Synchro Mergin Cloud
```

**APRÈS (Bureau)**:
```python
# 1. Charger les 50+1000 = 1050 communes collectées
collected = load_from_mergin()  # 1050 communes

# 2. Afficher validation
dialog = DataValidationDialog(collected, communes)
# Affiche:
#   🆕 Ajoutés: 50
#   ✓ Aucun changement: 1000
#   Statut: En attente de validation

# 3. L'utilisateur valide
# → Cliquer [Fusion Automatique]
# → "Ajouter 50 nouveaux enregistrements"

# 4. Fusion dans API
merger = MerginDataMerger(postgrest)
results = merger.merge('communes', communes, collected)
# For chaque nouveau:
#   postgrest.insert('communes', {new_commune_data})

# → 1050 communes maintenant dans la base!
# → Projet marqué comme "Synchronisé"
```

---

## 📁 Structure de Fichiers

```
mergin_workflows/
├── projects/
│   └── Communes_20260426_152345/
│       ├── metadata.json
│       │   {
│       │     "id": "Communes_...",
│       │     "name": "Communes",
│       │     "stage": 7,
│       │     "stages_completed": [1,2,4,5,6,7]
│       │   }
│       ├── exported_data.json      (1000 communes)
│       ├── imported_data.json      (1050 communes +50)
│       ├── validation_results.json ({status: approved})
│       ├── merge_results.json      ({50 insertés, 1000 OK})
│       └── sync_results.json       ({synced_at: ...})
└── backups/
    └── Communes_20260426_152345/
        └── imported_data_20260426_160000.json (backup)
```

---

## 🎓 Utilisation Pas à Pas

### Démarrage Rapide

```python
# 1. Initialiser (automatique)
plugin = MrvTeraka(iface)
mgr = plugin.mergin_manager

# 2. Créer projet
project_id = mgr.create_project("MonProjet", "ma_table", "Description")

# 3. Chaque étape finit par:
mgr.update_stage(project_id, 2)  # Étape 2
mgr.update_stage(project_id, 3)  # Étape 3
# ... etc

# 4. Vérifier progrès
info = mgr.get_project_info(project_id)
print(f"Stage: {info['stage']}/7")
print(f"Complété: {info['stages_completed']}")

# 5. Rapport final
report = mgr.generate_workflow_report(project_id)
mgr.export_report_to_file(project_id)
```

---

## 🔍 Détection de Conflits Automatique

```python
# Conflits détectés:
conflicts = [
    {
        'type': 'added',
        'count': 50,
        'ids': [1001, 1002, ..., 1050]
    },
    {
        'type': 'modified',
        'id': 5,
        'original': {'nom': 'Andohakabe', 'pop': 5000},
        'collected': {'nom': 'Andohakabe', 'pop': 5500}
    }
]

# Résumé pour l'utilisateur:
# 🆕 50 nouveaux
# ✏️ Modifié: ID 5 (population: 5000 → 5500)
# ✓ Pas de supprimés
```

---

## ✅ Checklist Workflow Complet

### Pour Chaque Projet Mergin:

1. ✓ Créer projet: `mgr.create_project(...)`
2. ✓ Exporter: `mgr.save_exported_data(...)`
3. ✓ Importer collectes: `mgr.import_collected_data(...)`
4. ✓ Valider: Dialog validation
5. ✓ Fusionner: `merger.merge(...)`
6. ✓ Synchro: `mgr.sync_to_api(...)`
7. ✓ Rapport: `mgr.export_report_to_file(...)`

---

## 🚀 Avantages de Cette Approche

| Avant | Après |
|--------|---------|
| ❌ Chargement JSON brut | ✅ Workflow structuré |
| ❌ Pas de suivi | ✅ 7 étapes tracées |
| ❌ Validation manuelle | ✅ Dialog validation auto |
| ❌ Fusion complexe | ✅ Merge intelligent |
| ❌ Pas de sauvegarde | ✅ Backups auto |
| ❌ Pas de rapport | ✅ Rapport détaillé |

---

## 📞 Besoin d'Aide?

| Question | Réponse |
|----------|---------|
| Comment créer un projet? | `mgr.create_project(...)` |
| Comment valider? | `DataValidationDialog(...)` |
| Fusion automatique? | `strategy='merge'` |
| Vérifier état? | `mgr.get_project_info(...)` |
| Exporter rapport? | `mgr.export_report_to_file(...)` |

---

## 🔗 Fichiers

- **`mergin_workflow_manager.py`**: Gestionnaire workflow
- **`validation_dialog.py`**: Formulaire validation
- **`mrv_teraka.py`**: Intégration plugin
- **`MERGIN_WORKFLOW.md`**: Doc complète

---

**Plugin MrvTeraka - Workflow Mergin Map Automatisé** ✅

