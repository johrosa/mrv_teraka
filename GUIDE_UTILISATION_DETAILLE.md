# 🚀 Guide Utilisateur Détaillé : Flux de Données MrvTeraka

Ce guide décrit le cycle de vie complet de la donnée dans le plugin MrvTeraka, de la préparation du projet à la validation finale en base de données.

---

## 🎯 Objectif du Plugin
Sécuriser et automatiser la collecte de données terrain pour garantir que seules des données validées et conformes atteignent la base de données de production.

---

## 🛠 Étape 1 : Préparation et Configuration (Bureau)

Avant de partir sur le terrain, vous devez configurer votre environnement QGIS.

1.  **Connexion :** Cliquez sur l'icône 🔐 dans la barre d'outils. Authentifiez-vous.
    *   *⚠️ Erreur à éviter :* Utiliser une URL d'API incorrecte. Vérifiez que vous pointez sur le serveur de production ou de test selon votre mission.
2.  **Sélection du Projet :** Dans le panneau "1. Sélection du Projet", choisissez un projet existant ou créez-en un nouveau en cliquant sur **Enregistrer**.
    *   Un "Projet" regroupe toutes les tables nécessaires à une mission spécifique (ex: Inventaire Arbres Itasy).
3.  **Filtrage par District :** Si vous travaillez sur une zone précise, saisissez le nom du district dans le champ **District** (ex: `Mandoto`). Cela filtrera les données téléchargées et les futures collectes.
4.  **Mapping des couches :** Si vos couches locales n'ont pas les mêmes noms que l'API, utilisez le bouton **Associer les couches (Mapping)** pour lier manuellement chaque couche QGIS à un endpoint API.

---

## 📱 Étape 2 : Cycle de Collecte Terrain (Mergin Map)

Une fois le projet configuré, passez au panneau "3. Cycle Terrain".

1.  **Préparation :** Cliquez sur **Préparer**. Le plugin exporte les données actuelles de la base (filtrées par district) vers un dossier local Mergin.
2.  **Synchronisation Mergin :** Utilisez le plugin Mergin Map standard pour pousser ces données vers le cloud, puis téléchargez-les sur votre application mobile **Mergin Maps** (Input).
3.  **Collecte :** Réalisez vos saisies sur le terrain.
4.  **Retour de mission :** Synchronisez votre mobile vers le cloud, puis cliquez sur **Actualiser** (B) dans le plugin MrvTeraka pour récupérer les nouvelles saisies.

---

## 🛡 Étape 3 : Validation des Données (Étape Critique)

C'est l'étape la plus importante pour garantir la qualité.

1.  **Importation :** Cliquez sur **Importer**. Le plugin charge les données collectées et détecte les différences avec la base de données originale.
2.  **Ouverture du Formulaire :** Cliquez sur **Valider**. Une fenêtre s'ouvre.
    *   **Légende des couleurs :**
        *   🟢 **Vert :** Nouvel enregistrement.
        *   🟡 **Jaune :** Enregistrement existant modifié.
        *   🔴 **Rouge :** Enregistrement supprimé.
3.  **Révision :** Parcourez chaque ligne. Vous pouvez modifier les valeurs directement si vous détectez une erreur de saisie évidente.
4.  **Application des règles :** Le plugin surligne en rouge les champs qui ne respectent pas les règles métier (ex: diamètre d'arbre incohérent).
5.  **Validation :** Une fois la revue terminée, cliquez sur **Approuver les modifications**.

*⚠️ **Piège à éviter :** Sauter la validation et synchroniser directement. Prenez le temps de vérifier les géométries (en regardant sur la carte QGIS derrière) et les attributs.*

---

## 📤 Étape 4 : Synchronisation vers le Backend

1.  **Envoi :** Le bouton **Synchroniser vers API** devient actif. Cliquez dessus.
2.  **Résumé de Fusion :** Un résumé s'affiche (ex: "15 ajouts, 3 modifications"). Vérifiez une dernière fois.
3.  **Confirmation :** Validez. Le plugin utilise la méthode "Upsert" : les nouveaux IDs sont créés, et les IDs existants sont mis à jour proprement.

---

## 🛑 Erreurs de manipulation courantes

| Erreur | Conséquence | Solution |
| :--- | :--- | :--- |
| **Modification des IDs manuellement** | Conflits de fusion et doublons. | Ne touchez jamais à la colonne `id`. Laissez le plugin et la base les gérer. |
| **Pousser des données sans filtrage de colonnes** | Erreur 400 (Bad Request) de l'API. | Le plugin filtre maintenant les colonnes automatiquement. Assurez-vous d'utiliser le bouton "Migrer Projet". |
| **Oubli du District** | Téléchargement de données trop lourdes (>50k lignes). | Utilisez toujours le filtre District pour travailler sur des zones gérables. |
| **Fermer QGIS pendant une tâche** | Perte de la synchronisation en cours. | Vérifiez le "Gestionnaire de tâches" en bas à droite de QGIS avant de quitter. |
| **Travailler sur une couche "Jointe" SQL** | Impossible de sauvegarder les changements. | Consultez le `GUIDE_JOINTURES_API.md` pour utiliser des Vues Updatable avec Triggers. |

---

**Astuce Pro :** Utilisez l'outil **Comparer** régulièrement pour vérifier que votre projet local est bien synchrone avec le serveur. Si les chiffres diffèrent, un "Actualiser" est peut-être nécessaire.
