# 📖 Manuel d'Utilisation Complet - Plugin QGIS MrvTeraka

**Version:** 3.1
**Équipe:** iTeraka
**Date:** Mai 2026

---

## 🌟 Introduction

Le plugin **MrvTeraka** est une solution SIG avancée conçue pour l'équipe MRV d'iTeraka. Il sert de pont entre :
1.  **QGIS Desktop** (Analyse et édition cartographique)
2.  **API PostgREST / Django** (Stockage centralisé des données)
3.  **Mergin Map** (Collecte de données sur le terrain via mobile)

Ce manuel détaille toutes les fonctionnalités pour une utilisation optimale et sécurisée de vos données géospatiales.

---

## 🔐 1. Installation et Authentification

### Connexion Initiale
Lors de l'activation du plugin, une icône **[🔐 Connexion]** s'ajoute à votre barre d'outils QGIS.
*   **URL API :** Par défaut `http://localhost:8000` (Backend Django).
*   **Identifiants :** Utilisez votre email professionnel et mot de passe.
*   **Mode :** Choisissez "Django" pour bénéficier du rendu d'erreurs détaillé.

### Gestion de la Session
*   **Reconnexion automatique :** Si vous cochez "Mémoriser", le plugin utilise un jeton JWT sécurisé stocké localement.
*   **Surveillance en direct :** Le plugin vérifie votre connexion toutes les 60 secondes. Un indicateur visuel (Rouge/Vert) vous informe en temps réel si le serveur est joignable.

---

## 🏗️ 2. Gestion des Données Centralisées (PostgREST)

Le groupe **Données PostgREST** permet de manipuler les 97 tables métiers de la base de données.

### Filtrage par District (Nouveauté)
Pour optimiser les performances, vous pouvez filtrer les données avant le téléchargement :
1.  Sélectionnez la table `communes`.
2.  Dans le champ **District**, saisissez le nom d'un district (ex: `Mandoto`).
3.  Cliquez sur **[Charger base]** ou **[Comparer]**. Seules les communes de ce district seront traitées.

### Actions Disponibles
*   **Sélection de table :** Liste déroulante intelligente avec recherche par saisie.
*   **Chargement :** Télécharge les données et les transforme en couches vectorielles QGIS. Les géométries complexes (Points, Polygones) sont gérées automatiquement.
*   **Migration (Upsert) :** L'outil **[Migrer vers base]** permet de pousser vos modifications locales vers le serveur.
    *   *Note :* Il utilise une logique intelligente qui met à jour les enregistrements existants (si l'ID existe) et crée les nouveaux, évitant ainsi tout doublon.
*   **Pagination automatique :** Pour les tables massives (ex: inventaires d'arbres), le téléchargement se fait par blocs transparents pour ne jamais bloquer QGIS.

---

## 📱 3. Workflow de Collecte de Terrain (Mergin Map)

Le workflow Mergin suit un cycle rigoureux en 3 étapes :

### Étape 1 : Préparation de l'export
1.  Choisissez la table à collecter (ex: `arbre_gps`).
2.  Cliquez sur **[Préparer Mergin]**.
3.  Le plugin crée un dossier projet local avec les données actuelles de la base, prêt à être synchronisé sur vos tablettes de terrain.

### Étape 2 : Importation après collecte
Une fois les agents de terrain revenus :
1.  Cliquez sur **[Importer Mergin]**.
2.  Le plugin scanne le projet mobile et identifie les nouveaux points et les modifications.
3.  Un message confirme le nombre d'enregistrements récupérés.

### Étape 3 : Validation et Synchronisation finale
C'est l'étape de contrôle qualité :
1.  **Validation :** Cliquez sur **[Valider import]**. Un formulaire s'ouvre pour comparer les données collectées avec les données originales. Vous pouvez valider ou rejeter les saisies.
2.  **Synchronisation :** Une fois validées, cliquez sur **[Synchroniser]**. Les données sont définitivement envoyées vers la base de données de production.

---

## 🔍 4. Diagnostic et Erreurs

### Rendu d'erreurs Django
Si une erreur survient côté serveur (ex: contrainte de base de données non respectée), le plugin affiche une fenêtre **HTML interactive** identique à celle que voient les développeurs Django. Cela permet de comprendre précisément quelle donnée pose problème.

### FAQ Technique
*   **Le bouton "Synchroniser" reste grisé :** Vous devez d'abord passer par l'étape de validation.
*   **La géométrie n'apparaît pas :** Seules les tables comme `communes`, `arbre_gps`, `bosquet_gps`, `pg_gps` et `bosquet_geom_historique` possèdent des composantes spatiales dans ce système.
*   **Erreur de certificat SSL :** Vérifiez que l'URL de l'API commence par `http://` (en local) ou `https://` (en production).

---

## 🛠️ 5. Maintenance du Plugin

Le plugin est modulaire :
*   `layer_table_mapping.json` : Contient la liste des tables et leurs clés primaires.
*   `layer_utils.py` : Gère la conversion des formats de données.
*   `postgrest_client.py` : Gère les communications réseau.

---

**© 2026 iTeraka - Solution de suivi MRV.**
*Développé pour la gestion durable des paysages et des forêts.*
