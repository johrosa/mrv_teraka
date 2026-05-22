# ANALYSE COMPARATIVE ET PROPOSITIONS D'AMÉLIORATIONS

## 📊 État des Lieux
L'extension **MrvTeraka** occupe un segment spécifique : le pilotage métier de la collecte de données via API. Voici comment elle se compare aux extensions de référence.

### 1. Mergin Maps (Plugin Officiel)
*   **Forces** : Synchronisation Cloud native, gestion de versions, stabilité éprouvée.
*   **Lacunes** : Pas de logique de validation métier post-collecte, pas d'intégration directe avec des API de production (PostgREST/Django).
*   **Leçon pour MrvTeraka** : Le plugin officiel excelle dans l'UI/UX de synchronisation. MrvTeraka doit s'en inspirer pour simplifier le transfert des données vers le Cloud.

### 2. Model Baker
*   **Forces** : Génération automatique de projets QGIS basés sur des schémas de base de données PostgreSQL. Supporte les formulaires complexes (QWidgets).
*   **Lacunes** : Orienté bureau uniquement. Pas de gestion du cycle de vie terrain.
*   **Leçon pour MrvTeraka** : MrvTeraka pourrait bénéficier d'une découverte dynamique des tables via l'API, plutôt que d'utiliser un fichier de mapping statique.

### 3. QGIS Data Reviewer
*   **Forces** : Moteur de règles puissant pour valider la qualité des attributs et la topologie.
*   **Lacunes** : Outil autonome, non intégré dans un flux de données (pas de sync).
*   **Leçon pour MrvTeraka** : Intégrer un mini-moteur de règles (Python expressions) dans le formulaire de validation de MrvTeraka.

---

## 💡 Propositions d'Améliorations à Haute Valeur Ajoutée

### A. Pilotage API Mergin Cloud (Priorité Haute)
Utiliser le paquet `mergin-client` pour automatiser la création des projets sur le serveur Mergin.
*   **Action** : Ajouter un bouton "Déployer sur Mergin Cloud" qui envoie les données préparées directement, sans manipulation de fichiers locale.

### B. Moteur de Validation par Expressions (Priorité Haute)
Permettre de définir des règles de validation simples directement dans QGIS.
*   **Action** : Ajouter un onglet "Règles" dans MrvTeraka où l'administrateur peut saisir des expressions QGIS (ex: `diametre > 0`). Lors de la validation, les lignes ne respectant pas ces règles sont marquées en rouge.

### C. Découverte de Schéma Dynamique (Priorité Moyenne)
Supprimer le besoin du fichier `layer_table_mapping.json`.
*   **Action** : Interroger l'endpoint Root `/` de PostgREST pour récupérer la liste des tables et colonnes disponibles. Configurer dynamiquement le plugin.

### D. Tableau de Bord (Dashboard) de Suivi (Priorité Moyenne)
Offrir une vue d'ensemble sur l'état des missions terrain.
*   **Action** : Nouvel onglet affichant une barre de progression pour chaque projet (Préparation 25% -> Collecte 50% -> Validation 75% -> Terminé).

### E. Emprise de Travail Spatiale (Priorité Basse)
Éviter d'exporter toute la base de données.
*   **Action** : Permettre à l'utilisateur de dessiner un rectangle sur la carte. N'exporter vers Mergin que les données situées à l'intérieur de cette zone.

---

## 🎯 Conclusion
MrvTeraka a le potentiel de devenir la **plateforme de gouvernance de données** de référence pour les entreprises utilisant Mergin Map. En intégrant l'automatisation Cloud et un moteur de règles, elle surclassera les outils existants par son intégration verticale unique (Base de données <-> Terrain).
