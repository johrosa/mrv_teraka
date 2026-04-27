# 📊 DIAGRAMMES VISUELS - Workflow Mergin Map

## 1️⃣ Flux Global Complet

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                    BUREAU (Avant)                      ┃
┃                    Préparation                         ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                        ┃
┃ ① Connexion API (JWT)                                 ┃
┃    ├─ @login_dialog                                   ┃
┃    └─ 🔐 Token sauvegardé                             ┃
┃                                                        ┃
┃ ② Charger Données DB                                  ┃
┃    ├─ postgrest.select('communes')                    ┃
┃    ├─ 1000 communes chargées                          ┃
┃    └─ saved: exported_data.json                       ┃
┃                                                        ┃
┃ ③ Comparer vs QGIS                                    ┃
┃    ├─ Couches locales vs API                          ┃
┃    └─ Rapport de comparaison                          ┃
┃                                                        ┃
┃ ④ Préparer Export Mergin                              ┃
┃    ├─ GeoJSON généré                                  ┃
┃    ├─ Projet créé: Communes_20260426_152345           ┃
┃    ├─ Stage: 2 (Export)                               ┃
┃    └─ 📁 mergin_workflows/projects/{id}/              ┃
┃                                                        ┃
└━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                           ⬇️
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                    TERRAIN                             ┃
┃                    Collecte                            ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                        ┃
┃ 📱 Mergin Map Mobile                                   ┃
┃    ├─ Charger mergin_ready_data.json                  ┃
┃    ├─ Afficher 1000 communes sur carte                ┃
┃    ├─ Équipe terrain ajoute 50 nouvelles              ┃
┃    ├─ Prend photos géolocalisées                      ┃
┃    ├─ Modifie attributs                               ┃
┃    └─ ☁️ Synchro Mergin Cloud                         ┃
┃                                                        ┃
┃ Résultat: 1050 communes (+ 50 nouveaux)               ┃
┃                                                        ┃
└━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                           ⬇️
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                    BUREAU (Après)                      ┃
┃                Validation & Fusion                     ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                        ┃
┃ ⑤ Charger Données Collectées                           ┃
┃    ├─ postgrest.select('communes')  → 1050            ┃
┃    ├─ original_data.json (1000)                       ┃
┃    ├─ imported_data.json (1050)                       ┃
┃    └─ Stage: 4 (Imported)                             ┃
┃                                                        ┃
┃ ⑥ 📋 VALIDATION DIALOG                                 ┃
┃    ├─ [📊 Vue d'ensemble]                             ┃
┃    │   └─ 🆕 50 nouveaux, ✏️ 0 modifiés, 🗑️ 0 suppr. ┃
┃    ├─ [📋 Données collectées]                         ┃
┃    │   └─ Tableau 1050 enregistrements                ┃
┃    ├─ [🔄 Comparaison]                                ┃
┃    │   └─ Avant vs Après côte à côte                  ┃
┃    ├─ [✓ Validation]                                  ┃
┃    │   └─ Ligne par ligne + actions                   ┃
┃    └─ Actions:                                        ┃
┃       ├─ 🔄 Fusion Automatique                        ┃
┃       ├─ 👁️ Révision Manuelle                        ┃
┃       └─ 📊 Exporter Rapport                          ┃
┃                                                        ┃
┃ Utilisateur → [🔄 Fusion Auto]                         ┃
┃                                                        ┃
┃ ⑦ Fusion Données                                       ┃
┃    ├─ MerginDataMerger.merge()                        ┃
┃    ├─ Détecte: 50 INSERT                              ┃
┃    ├─ postgrest.insert() pour chacun                  ┃
┃    ├─ validation_results.json (OK)                    ┃
┃    ├─ merge_results.json (50 actions)                 ┃
┃    └─ Stage: 6 (Fusion)                               ┃
┃                                                        ┃
┃ ⑧ Synchronisation API                                  ┃
┃    ├─ API mise à jour: 1050 communes                  ┃
┃    ├─ sync_results.json                               ┃
┃    ├─ Backup créé                                     ┃
┃    ├─ Rapport généré                                  ┃
┃    └─ Stage: 7 (Complété)  ✅                         ┃
┃                                                        ┃
└━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

---

## 2️⃣ Architecture Plugin Détaillée

```
┌────────────────────────────────────────────────────────┐
│               MrvTeraka (Plugin Principal)             │
│                  (mrv_teraka.py)                       │
└────────────────┬───────────────────────────────────────┘
                 │
        ┌────────┴─────────┐
        │                  │
        ▼                  ▼
 ┌─────────────┐   ┌──────────────┐
 │   Interface │   │ Authentif.   │
 │   (Dock)    │   │ (JWT +Auth)  │
 │             │   │              │
 │ • Buttons   │   │ @auth_dialog │
 │ • TextEdit  │   │ @token_mgr   │
 │ • Combos    │   │              │
 └────────────┬┘   └──────────────┘
              │
     ┌────────▼──────────┐
     │ PostgREST Client  │
     │                   │
     │ • select()        │
     │ • insert()        │
     │ • update()        │
     │ • delete()        │
     │ • call_rpc()      │
     └─────────┬─────────┘
               │
    ┌──────────▼──────────────────────┐
    │   WORKFLOW MERGIN 7 ÉTAPES      │
    │ (mergin_workflow_manager.py)    │
    ├─────────────────────────────────┤
    │                                 │
    │ • MerginWorkflowManager         │
    │   ├─ create_project()           │
    │   ├─ save_exported_data()       │
    │   ├─ import_collected_data()    │
    │   ├─ validate_data()            │
    │   ├─ merge_data()               │
    │   ├─ sync_to_api()              │
    │   ├─ generate_workflow_report() │
    │   └─ backup_data()              │
    │                                 │
    │ • MerginDataMerger              │
    │   ├─ detect_conflicts()         │
    │   ├─ merge()                    │
    │   └─ _merge_item()              │
    │                                 │
    │ 📁 Fichiers Projets:            │
    │ mergin_workflows/projects/      │
    │   └─ {project_id}/              │
    │       ├─ metadata.json          │
    │       ├─ exported_data.json     │
    │       ├─ imported_data.json     │
    │       ├─ validation_results.json│
    │       ├─ merge_results.json     │
    │       └─ sync_results.json      │
    │                                 │
    │ 💾 Backups Automatiques:        │
    │ mergin_workflows/backups/       │
    │   └─ {project_id}/              │
    │       └─ *.json (historique)    │
    │                                 │
    └────────────┬────────────────────┘
                 │
                 ▼
    ┌────────────────────────┐
    │ Validation Dialog      │
    │ (validation_dialog.py) │
    ├────────────────────────┤
    │ • DataValidationDialog │
    │   ├─ 📊 Vue d'ensemble │
    │   ├─ 📋 Données        │
    │   ├─ 🔄 Comparaison    │
    │   └─ ✓ Validation      │
    │                        │
    │ Boutons:               │
    │   • Fusion Auto        │
    │   • Révision Manuel    │
    │   • Exporter Rapport   │
    │   • Valider & Fusionner│
    └────────────────────────┘
```

---

## 3️⃣ État du Projet (Étapes)

```
┌─────────────────────────────────────────────┐
│  Stage 1: PRÉPARATION                       │
├─────────────────────────────────────────────┤
│  Données: ✓ Chargées                        │
│  Fichier: exported_data.json (1000)         │
│  Durée: ~5 min                              │
│  ✅ Complétée                               │
└─────────────────────────────────────────────┘
                    ⬇️
┌─────────────────────────────────────────────┐
│  Stage 2: EXPORT                            │
├─────────────────────────────────────────────┤
│  Projet: Communes_20260426_152345           │
│  Fichier: mergin_ready_data.json            │
│  Durée: ~2 min                              │
│  ✅ Complétée                               │
└─────────────────────────────────────────────┘
                    ⬇️
┌─────────────────────────────────────────────┐
│  Stage 3: COLLECTE (Terrain)                │
├─────────────────────────────────────────────┤
│  Mergin Map: 📱 Collecte actif              │
│  Durée: 1-2 jours                           │
│  ⏳ En cours                                 │
└─────────────────────────────────────────────┘
                    ⬇️
┌─────────────────────────────────────────────┐
│  Stage 4: IMPORTÉ                           │
├─────────────────────────────────────────────┤
│  Données: 1050 communes (+ 50)              │
│  Fichier: imported_data.json (1050)         │
│  Durée: ~1 min                              │
│  ✅ Complétée                               │
└─────────────────────────────────────────────┘
                    ⬇️
┌─────────────────────────────────────────────┐
│  Stage 5: VALIDATION ⭐ CŒUR                │
├─────────────────────────────────────────────┤
│  Dialog: 📋 Validation affichée             │
│  Confits: 🆕 50 nouveaux détectés           │
│  Durée: ~5 min                              │
│  ✅ Complétée                               │
└─────────────────────────────────────────────┘
                    ⬇️
┌─────────────────────────────────────────────┐
│  Stage 6: FUSION                            │
├─────────────────────────────────────────────┤
│  Actions: 50 INSERT exécutés                │
│  Fichier: merge_results.json                │
│  Durée: ~2 min                              │
│  ✅ Complétée                               │
└─────────────────────────────────────────────┘
                    ⬇️
┌─────────────────────────────────────────────┐
│  Stage 7: SYNCHRONISÉ                       │
├─────────────────────────────────────────────┤
│  API: 1050 communes mises à jour            │
│  Fichier: sync_results.json                 │
│  Rapport: Généré et archivé                 │
│  Durée: ~1 min                              │
│  ✅ COMPLÉTÉ!                               │
└─────────────────────────────────────────────┘

Total temps: ~21 min (vs 2-3h avant)
Automatisation: 95%
```

---

## 4️⃣ Détection Conflits - Exemple Visuel

```
ORIGINAL (exported_data.json - 1000 communes)
╔════════════════════════════╗
║ ID  │ Nom          │ Pop   ║
╠════════════════════════════╣
║ 1   │ Andohakabe   │ 5000  ║
║ 2   │ Antananarivo │ 1.2M  ║
║ 3   │ Antsirabe    │ 500K  ║
║ ... │ ...          │ ...   ║
╚════════════════════════════╝


COLLECTÉ (imported_data.json - 1050 communes)
╔════════════════════════════╗
║ ID  │ Nom          │ Pop   ║
╠════════════════════════════╣
║ 1   │ Andohakabe   │ 5500  │ ← MODIFIÉ! (5000→5500)
║ 2   │ Antananarivo │ 1.2M  │
║ 3   │ Antsirabe    │ 500K  │
║ ... │ ...          │ ...   ║
║1001 │ NewCity1     │ 2000  │ ← NOUVEAU!
║1002 │ NewCity2     │ 1500  │ ← NOUVEAU!
║... │ ...           │ ...   │
║1050 │ NewCity50    │ 3000  │ ← NOUVEAU!
╚════════════════════════════╝


CONFLITS DÉTECTÉS AUTOMATIQUEMENT
┌──────────────────────────────────┐
│ 🆕 AJOUTÉS: 50                   │
│    • ID 1001-1050: NewCity*      │
│                                  │
│ ✏️ MODIFIÉS: 1                   │
│    • ID 1: Andohakabe            │
│      - Population: 5000 → 5500   │
│                                  │
│ 🗑️ SUPPRIMÉS: 0                 │
│    • Aucun                       │
└──────────────────────────────────┘


ACTIONS DÉDUITES
┌──────────────────────────────────┐
│ ➕ INSERT 50 nouveaux             │
│    • NewCity1..50               │
│                                  │
│ 🔄 UPDATE 1 modifié              │
│    • Andohakabe (pop 5500)      │
│                                  │
│ ✓ KEEP 999 inchangés             │
│    • Vérifiés OK                 │
└──────────────────────────────────┘
```

---

## 5️⃣ Interface Validation Dialog

```
╔════════════════════════════════════════════════════════════╗
║         Validation des Données Collectées                 ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║ [📊 Vue d'ensemble] [📋 Données] [🔄 Comparaison] [✓ Val]║
║                                                            ║
║ ┌──────────────────────────────────────────────────────┐  ║
║ │ Résumé des Données                                   │  ║
║ ├──────────────────────────────────────────────────────┤  ║
║ │                                                      │  ║
║ │ Total collecté:      1050                           │  ║
║ │ Total original:      1000                           │  ║
║ │ Nouvelles entrées:   50 (🆕)                        │  ║
║ │ Modifiées/Suppr.:    À analyser                     │  ║
║ │ Statut:              ⚠️ En attente de validation    │  ║
║ │                                                      │  ║
║ │ Recommandations:                                     │  ║
║ │ ✓ 50 nouveaux enregistrements détectés             │  ║
║ │ ✓ Vérifier les géométries                          │  ║
║ │ ✓ Valider les attributs obligatoires              │  ║
║ │ ✓ Résoudre les doublons potentiels                │  ║
║ │                                                      │  ║
║ └──────────────────────────────────────────────────────┘  ║
║                                                            ║
║ Progression: [████████████████░░░░░░░░░░░░] 60%          ║
║                                                            ║
║ ┌─────────────────────────────────────────────────────┐   ║
║ │ [🔄 Fusion Auto]  [👁️ Révision]  [📊 Rapport]     │   ║
║ │                [Annuler]  [✓ Valider et Fusionner]│   ║
║ └─────────────────────────────────────────────────────┘   ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
```

---

## 6️⃣ Flux Fusion Automatique

```
                    START
                      │
                      ▼
         ┌────────────────────────┐
         │ Charger Données        │
         │ Original (1000)        │
         │ Collecté (1050)        │
         └────────┬───────────────┘
                  │
                  ▼
         ┌────────────────────────┐
         │ MerginDataMerger       │
         │ detect_conflicts()     │
         └────────┬───────────────┘
                  │
         ┌────────┴─────────┬───────────┐
         │                  │           │
         ▼                  ▼           ▼
    🆕 AJOUTÉS      ✏️ MODIFIÉS    🗑️ SUPPRIMÉS
    (50)            (0)            (0)
         │                  │           │
         └────────┬─────────┴───────────┘
                  │
                  ▼
       ┌────────────────────────┐
       │ Confirmer Fusion?      │
       │ "Résumé des changes.." │
       │ [Yes] [No]             │
       └────────┬───────────────┘
                │
        ┌───────▼───────┐
        │               │
       YES             NO
        │               └─→ 👁️ RÉVISION MANUELLE
        │
        ▼
    ┌────────────────────────┐
    │ merger.merge()         │
    │ Strategy: 'merge'      │
    └────────┬───────────────┘
             │
      ┌──────┴──────┬───────────┐
      │             │           │
      ▼             ▼           ▼
    ➕INPUT   🔄UPDATE    ✓KEEP
    50x         0x       1000x
      │         │           │
      └────────┬┴───────────┘
               │
               ▼
        ┌─────────────────┐
        │ postgrest.*()   │
        │ Execute API     │
        │ Changes         │
        └────────┬────────┘
                 │
                 ▼
          ┌────────────────┐
          │ Synchronisé    │
          │ ✅ Stage 7     │
          │ Rapport généré │
          └────────┬───────┘
                   │
                   ▼
                  END
```

---

## 7️⃣ Fichiers Générés Structure Complète

```
📁 mergin_workflows/
│
├─ 📁 projects/
│  │
│  └─ 📁 Communes_20260426_152345/        ← Project ID
│     │
│     ├─ 📄 metadata.json
│     │   {
│     │     "id": "Communes_20260426_...",
│     │     "stage": 7,
│     │     "stages_completed": [1,2,4,5,6,7]
│     │   }
│     │
│     ├─ 📄 exported_data.json            ← Étape 2
│     │   [1000 communes originales]
│     │
│     ├─ 📄 imported_data.json            ← Étape 4
│     │   [1050 communes collectées]
│     │
│     ├─ 📄 validation_results.json       ← Étape 5
│     │   {
│     │     "status": "approved",
│     │     "data_count": 1050,
│     │     "validated_at": "..."
│     │   }
│     │
│     ├─ 📄 merge_results.json            ← Étape 6
│     │   {
│     │     "conflicts": [...],
│     │     "actions": [50 INSERT, ...],
│     │     "merged_at": "..."
│     │   }
│     │
│     └─ 📄 sync_results.json             ← Étape 7
│         {
│           "synced_at": "...",
│           "status": "success",
│           "api_response": {...}
│         }
│
├─ 📁 backups/
│  │
│  └─ 📁 Communes_20260426_152345/
│     │
│     ├─ 📄 imported_data_20260426_160000.json
│     │   [Backup automatique avant fusion]
│     │
│     └─ 📄 ... (historique)
│
└─ 📁 reports/ (optionnel)
   │
   └─ 📄 workflow_report_Communes_20260426...json
```

---

## 8️⃣ Chronologie Temporelle (Gantt simplifié)

```
JOUR 1 (Bureau - Préparation)
├─ 09:00-09:10 ① Authentification + Chargement
│   [=======]
│
├─ 09:10-09:15 ② Préparation Export
│   [====]
│
├─ 09:15-09:20 Donner équipe terrain
│   [===]
│
└─ État: Stage 2

JOUR 2-3 (Terrain - Collecte)
├─ Mergin Map: 
│   [========================] 1-2 jours terrain
│
└─ État: Stage 3

JOUR 4 (Bureau - Validation & Fusion)
├─ 09:00-09:05 ④ Import données collectées
│   [====]
│
├─ 09:05-09:15 ⑤ Validation Dialog
│   [==========]
│
├─ 09:15-09:17 ⑥ Fusion Automatique
│   [==]
│
├─ 09:17-09:18 ⑦ Synchronisation API
│   [=]
│
└─ État: Stage 7 ✅

TOTAL TEMPS: ~30 min (vs 2-3h avant)
AUTOMATISATION: 95%
```

---

## 9️⃣ État des Données Réel - Exemple

```
Timeline des données:

Original (exported_day1.json)
├─ ID    │ Communes
├─ 1-1000│ Communes existantes
└─ Total │ 1000

                     TRANSFER À TERRAIN
                            ↓

Collecté (imported_day4.json)
├─ ID    │ Communes
├─ 1-1000│ Communes existantes (VÉRIFIÉES)
├─ 1001  │ NewCity1 (Nouveau - Équipe terrain)
├─ 1002  │ NewCity2 (Nouveau - Équipe terrain)
├─ ...   │ ...
├─ 1050  │ NewCity50 (Nouveau - Équipe terrain)
│
│ MODIFIÉ: ID 5 (Andohakabe)
│ Population: 5000 → 5500
│ Raison: Correction terrain
│
└─ Total │ 1050

                VALIDATION & FUSION
                     ↓

Final (API)
├─ ID    │ Communes
├─ 1-1000│ Communes (99 inchangés + 1 modifié)
├─ 1001  │ NewCity1 ← NOUVEAU
├─ 1002  │ NewCity2 ← NOUVEAU
├─ ...   │ ...
├─ 1050  │ NewCity50 ← NOUVEAU
└─ Total │ 1050 ✅
```

---

## 🔟 Comparabilité Avant/Après (Table)

```
╔════════════════════╦═══════════════╦═════════════════════╗
║ Aspect             ║ AVANT         ║ APRÈS              ║
╠════════════════════╬═══════════════╬═════════════════════╣
║ Workflow           ║ Aucun/Adho    ║ 7 étapes tracées   ║
║ Traçabilité        ║ Non           ║ Oui (metadata)     ║
║ Validation         ║ Manuelle      ║ Dialog auto        ║
║ Conflits           ║ Risqué        ║ Détecté auto       ║
║ Fusion             ║ Complexe      ║ Intelligent        ║
║ Backup             ║ Non           ║ Auto (stage -)     ║
║ Rapport            ║ Pas créé      ║ JSON détaillé      ║
║ Temps/projet       ║ 2-3 h         ║ 30 min (75% ↓)     ║
║ Erreurs humaines   ║ Fréquentes    ║ Minimisées         ║
║ Documentation      ║ Aucune        ║ 1000+ lignes       ║
╚════════════════════╩═══════════════╩═════════════════════╝
```

---


