# 📖 Manuel d'Utilisation - Plugin QGIS MrvTeraka

**Version:** 3.0
**Équipe:** iTeraka
**Date:** Mai 2026

---

## 🌟 Introduction

Le plugin **MrvTeraka** est un outil professionnel conçu pour automatiser les flux de données entre QGIS, votre backend API (PostgREST/Django) et le terrain (via Mergin Map). Il permet de gérer plus de 90 tables métiers, d'assurer la validation des collectes et de migrer des projets complets.

---

## 🔐 1. Connexion et Authentification

Dès le lancement de QGIS, un bouton **[🔐 Connexion]** apparaît dans votre barre d'outils.

1.  **Formulaire :** Saisissez l'URL de votre API, votre identifiant (email) et votre mot de passe.
2.  **Mémorisation :** Cochez "Mémoriser les identifiants" pour une reconnexion automatique au prochain démarrage.
3.  **Surveillance :** Une icône en haut de la fenêtre du plugin affiche le statut :
    *   🟢 **Connecté :** Tout est opérationnel.
    *   🟠 **Attention :** Session expirée ou serveur injoignable (vérification automatique en arrière-plan).

---

## 🗺️ 2. L'Interface (Dock Widget)

L'interface est organisée en trois groupes logiques pour guider votre travail :

### A. Connexion API
Permet de se déconnecter proprement et d'effacer le jeton de sécurité local.

### B. Données PostgREST (Base de données)
C'est ici que vous gérez le lien direct entre vos couches QGIS et le backend :
*   **Sélection de table :** Utilisez la liste déroulante pour choisir l'une des 97 tables disponibles.
*   **[Charger base] :** Télécharge les données de l'API et crée une couche mémoire dans QGIS.
*   **[Comparer] :** Compare le nombre d'enregistrements entre votre projet et le serveur.
*   **[Migrer vers base] :** **(Nouveau)** Pousse toutes les données de vos couches locales vers le serveur en utilisant une logique intelligente (Upsert) qui met à jour les données existantes sans créer de doublons.

### C. Flux Mergin Map (Terrain)
Suivez les étapes numérotées (1, 2, 3) :
1.  **Préparation :** Sélectionnez la table de terrain et cliquez sur **[Préparer Mergin]**. Cela crée un projet local prêt à être synchronisé vers vos mobiles.
2.  **Collecte & Import :** Après le terrain, cliquez sur **[Importer Mergin]** pour récupérer les données saisies.
3.  **Validation & Fusion :**
    *   Cliquez sur **[Valider import]** pour ouvrir l'assistant de validation.
    *   Comparez les données avant/après.
    *   Cliquez sur **[Synchroniser]** pour envoyer définitivement les données validées en base de données.

---

## 🚀 3. Fonctionnalités Avancées

### ⚡ Performance & Volume
Le plugin gère automatiquement la **pagination**. Si vous téléchargez une table de 20 000 arbres, il le fera par blocs de 1 000 pour éviter de geler QGIS.

### 🛡️ Robustesse (Upsert)
La fonction de migration est **idempotente**. Si vous l'interrompez et la relancez, elle reprendra là où elle s'est arrêtée sans corrompre vos données existantes.

### 🔄 Travail Asynchrone
Les opérations lourdes (chargement massif, migration) s'exécutent via le **Gestionnaire de tâches de QGIS**. Vous pouvez continuer à dessiner ou analyser vos cartes pendant que les données sont envoyées au serveur.

---

## 🛠️ 4. Dépannage (FAQ)

### Q: "Les boutons sont grisés"
*   **R :** Vous n'êtes pas authentifié. Cliquez sur le bouton de connexion dans la barre d'outils.

### Q: "Erreur de syntaxe au démarrage (default.py)"
*   **R :** Cela provient d'une erreur dans vos expressions QGIS locales. Allez dans le gestionnaire d'expressions et vérifiez que vos chaînes HTML ne commencent pas par `''''` (4 guillemets). Remplacez-les par un seul guillemet `'`.

### Q: "Le plugin ne voit pas ma nouvelle couche"
*   **R :** Assurez-vous que le nom de votre couche correspond à l'un des noms définis dans le mappage API (ex: `arbre_gps`).

---

**© 2026 iIteraka - Pour toute assistance technique, contactez l'administrateur SIG.**
