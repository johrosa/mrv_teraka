# 💡 Recommandations Techniques et Opérationnelles - MrvTeraka

Suite à la refonte majeure du plugin vers une architecture centrée sur le **Projet**, voici les recommandations pour garantir la stabilité et l'évolution du système.

## 1. Gestion de la Base de Données (Backend)
*   **Vues Updatable :** Privilégiez systématiquement l'utilisation de vues PostgreSQL avec triggers `INSTEAD OF` pour les jointures complexes. Cela déporte la logique métier vers le serveur et garde le plugin QGIS léger et générique.
*   **Documentation OpenAPI :** Le plugin s'appuie sur `fetch_schema()`. Assurez-vous que PostgREST expose correctement le schéma (vérifiez les permissions `USAGE` sur le schéma `api` et les commentaires de table qui servent de métadonnées).
*   **Indexation :** Avec l'augmentation du volume de données, assurez-vous que les colonnes utilisées pour les filtres (comme `district`) sont indexées dans PostgreSQL.

## 2. Performance et Expérience Utilisateur (UX)
*   **Filtres de Zone :** Formez les utilisateurs à **toujours** utiliser le filtre par District. Charger l'intégralité de la base de données de Madagascar dans QGIS via une API reste techniquement possible mais ralentira considérablement le rendu cartographique et la validation.
*   **Validation Asynchrone :** Pour les projets dépassant 5000 entités, le formulaire de validation peut devenir lent. Recommandez aux utilisateurs de subdiviser leurs missions Mergin en zones plus petites.

## 3. Maintenance du Code
*   **Séparation des préoccupations :** Continuez à utiliser `layer_utils.py` pour toute manipulation de géométrie. Évitez d'ajouter de la logique de conversion directement dans `mrv_teraka.py`.
*   **Tests Unitaires :** Les tests actuels ont montré des limites dans l'environnement de sandbox (absence de fournisseur Postgres, problèmes de plateforme headless). Il est fortement recommandé de mettre en place une **CI (GitHub Actions/GitLab CI)** avec un conteneur incluant QGIS et une instance PostGIS réelle pour des tests d'intégration complets.
*   **Gestion des Dépendances :** Le plugin dépend de `osgeo` (GDAL/OGR) comme fallback. Assurez-vous que les postes de déploiement disposent d'une installation QGIS complète incluant ces bibliothèques Python.

## 4. Sécurité
*   **Gestion des Jetons :** Les jetons JWT sont stockés via `QSettings`. Bien que pratique, ce n'est pas un coffre-fort sécurisé. Pour des environnements très sensibles, envisagez l'intégration de `QgsAuthManager`.
*   **Permissions API :** Utilisez le principe du moindre privilège. L'utilisateur "Terrain" ne devrait avoir accès qu'aux tables nécessaires à sa collecte, ce que le plugin gère désormais dynamiquement.

## 5. Déploiement
*   **Nettoyage :** Avant chaque publication de version (`.zip`), lancez le script de nettoyage pour supprimer les fichiers `__pycache__`, `.pyc` et les résidus de tests, afin de garder le package léger (actuellement réduit de ~60% grâce au nettoyage des docs et binaires).
