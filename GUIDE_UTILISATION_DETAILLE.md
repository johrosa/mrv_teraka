# 🚀 Guide Utilisateur Détaillé : Flux de Données MrvTeraka

Ce guide décrit le cycle de vie complet de la donnée dans le plugin MrvTeraka, de la préparation du projet à la validation finale en base de données.

---

## 🎯 Objectif du Plugin
Sécuriser et automatiser la collecte de données terrain pour garantir que seules des données validées et conformes atteignent la base de données de production.

---

## 🛠 Étape 1 : Initialisation Automatisée (Bureau)

Avant de partir sur le terrain, vous devez configurer votre mission.

1.  **Connexion Unifiée :** Cliquez sur l'icône 🔐. Saisissez vos identifiants API **ET** vos identifiants Mergin Maps.
    *   *Avantage :* Le plugin gérera automatiquement les transferts Cloud pour vous.
2.  **Analyse Intelligente :** Cliquez sur **Traiter le Projet**. Le plugin analyse vos couches QGIS, suggère les correspondances API et vérifie la santé de vos données.
    *   *Option Mise à jour :* Vous pouvez rafraîchir vos données locales à tout moment en sélectionnant l'option **Mise à jour / Rafraîchir**. Cela téléchargera les dernières modifications du serveur sans modifier votre projet.
3.  **Filtrage Spatial :** Saisissez le district cible. Toutes les données seront packagées automatiquement.

---

## 📱 Étape 2 : Cycle Automatisé des Missions

Passez au panneau "3. Cycle Automatisé des Missions".

1.  **Déploiement Terrain (1-clic) :** Cliquez sur **1. Déploiement Terrain**.
    *   Le plugin crée un **GeoPackage (GPKG)** optimisé.
    *   Il crée automatiquement le projet sur votre compte Mergin Maps Cloud.
    *   Il uploade les données.
2.  **Collecte :** Réalisez vos saisies sur votre mobile (Mergin Maps Input).
3.  **Retour de Mission :** Cliquez sur **2. Retour de Mission**. Le plugin récupère les modifications du Cloud et les importe localement.

---

## 🛡 Étape 3 : Validation Métier Automatisée

1.  **Lancement :** Cliquez sur **3. Validation Métier**.
    *   Le **Moteur de Règles iTeraka** analyse chaque ligne.
    *   Les erreurs (ex: diamètre invalide) sont surlignées automatiquement.
2.  **Révision :** Une fenêtre s'ouvre.
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
