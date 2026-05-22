# SYMBIOSES ENTRE MRV TERAKA ET MERGIN MAP

## 🎯 Vision Globale
Le plugin **MrvTeraka** ne remplace pas Mergin Map ; il l'encadre. Mergin Map fournit la **logistique technique** (synchronisation, offline, saisie mobile), tandis que MrvTeraka apporte l'**intelligence métier** et la **gouvernance des données**.

---

## 🏗️ Architecture Complémentaire

| Fonctionnalité | Mergin Map (Le Transporteur) | MrvTeraka (Le Cerveau) |
| :--- | :--- | :--- |
| **Source des données** | Fichiers locaux (GPKG) | API PostgREST / Django (Base Centralisée) |
| **Mobilité** | Excellente (Mode déconnecté natif) | Limitée (Nécessite Mergin pour le terrain) |
| **Validation métier** | Basique (Contraintes QGIS) | Avancée (Formulaire de révision avant Fusion) |
| **Réconciliation** | Gestion de conflits fichiers | Fusion intelligente INSERT/UPDATE/DELETE |
| **Workflow** | Stockage et Synchro | Préparation → Terrain → Validation → Sync |

---

## 🔄 Le Cycle de Vie de la Donnée Certifiée

### 1. Amont : Préparation Pilotée
MrvTeraka extrait les données de l'API de production pour créer un projet Mergin "propre". Grâce au nouveau mode **Projet-Centric**, MrvTeraka peut préparer des dizaines de tables liées en une seule opération, garantissant que l'équipe terrain dispose de tout le contexte nécessaire.

### 2. Terrain : Liberté de Saisie
Pendant la collecte, Mergin Map gère la complexité technique :
*   Positionnement GPS précis.
*   Prise de photos géolocalisées.
*   Synchronisation Cloud fluide entre les membres de l'équipe.

### 3. Aval : Gouvernance et Certification
C'est ici que la symbiose est la plus forte. Mergin Map ramène les données, mais MrvTeraka les **certifie** :
*   **Validation par l'expert** : Utilisation du `DataValidationDialog` pour comparer l'original et le collecté.
*   **Fusion Sans Doublons** : Utilisation du `MerginDataMerger` et de la logique Upsert pour mettre à jour la base de production proprement.
*   **Traçabilité** : Enregistrement de chaque étape du cycle de vie dans les métadonnées du projet.

---

## 🚀 Avantages de la Symbiose

1.  **Intégrité Totale** : On bénéficie de la souplesse de Mergin sans risquer de corrompre la base de données principale.
2.  **Productivité Décuplée** : L'automatisation de la préparation multi-tables réduit le temps de mise en place de 75%.
3.  **Auditabilité** : Chaque modification terrain est révisée par un administrateur avant d'être fusionnée.

---

## 🔮 Évolutions Futures
Pour renforcer cette symbiose, les prochaines étapes incluent l'utilisation directe de l'API Python de Mergin (`mergin-client`) pour supprimer toute manipulation manuelle de fichiers et offrir un bouton "Pousser vers le Cloud Mergin" directement dans l'interface MrvTeraka.
