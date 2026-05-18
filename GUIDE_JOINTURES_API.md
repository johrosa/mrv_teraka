# Guide de Gestion des Jointures avec l'API MrvTeraka

Ce guide explique comment manipuler des données issues de jointures complexes (plusieurs tables) tout en permettant leur mise à jour via l'API PostgREST et le plugin QGIS.

## Le Défi des Jointures

Dans un projet SIG, il est fréquent de vouloir afficher des informations provenant de plusieurs tables (ex: un `bosquet` avec le nom de sa `commune`).
Cependant :
1. Les jointures SQL classiques sont généralement **en lecture seule**.
2. L'API PostgREST expose des tables individuelles.
3. Envoyer un objet "joint" à un endpoint de table de base provoquera une erreur si des colonnes "étrangères" sont présentes.

## La Solution : Vues et Triggers PostgreSQL

La méthode recommandée pour gérer cela proprement est d'utiliser des **Vues Updatable** côté base de données.

### 1. Création de la Vue

Créez une vue qui rassemble les informations nécessaires :

```sql
CREATE VIEW api.bosquet_complet AS
SELECT
    b.*,
    c.nom AS commune_nom,
    c.district AS commune_district
FROM base.bosquet b
LEFT JOIN base.communes c ON b.commune_id = c.id;
```

### 2. Rendre la Vue Modifiable (Triggers INSTEAD OF)

Pour permettre à QGIS de modifier cette vue, on ajoute un trigger qui redirige les changements vers la table source (`bosquet`) en ignorant les colonnes informatives (`commune_nom`).

```sql
CREATE OR REPLACE FUNCTION api.trig_bosquet_complet_upsert()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO base.bosquet (id, nom, geom, commune_id, district)
    VALUES (
        COALESCE(NEW.id, nextval('base.bosquet_id_seq')),
        NEW.nom,
        NEW.geom,
        NEW.commune_id,
        NEW.district
    )
    ON CONFLICT (id) DO UPDATE SET
        nom = EXCLUDED.nom,
        geom = EXCLUDED.geom,
        commune_id = EXCLUDED.commune_id,
        district = EXCLUDED.district;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER t_upsert_bosquet_complet
INSTEAD OF INSERT OR UPDATE ON api.bosquet_complet
FOR EACH ROW EXECUTE FUNCTION api.trig_bosquet_complet_upsert();
```

## Fonctionnement dans le Plugin MrvTeraka

Le plugin facilite cette approche grâce à deux mécanismes :

### A. Filtrage Automatique à la Migration
Lorsque vous utilisez l'outil **"Migrer Projet"**, le plugin compare les colonnes de votre couche QGIS avec celles déclarées dans l'OpenAPI de l'endpoint.
- Si votre couche QGIS contient 15 colonnes mais que l'endpoint API n'en accepte que 10, le plugin **supprime automatiquement les 5 colonnes en trop** avant l'envoi.
- Cela permet de pousser une couche issue d'une jointure complexe vers une table de base simple sans erreur 400.

### B. Mapping Manuel
Si le nom de votre vue ou de votre couche locale ne correspond pas exactement à l'endpoint de base :
1. Utilisez le bouton **"Associer les couches (Mapping)"**.
2. Sélectionnez votre couche locale.
3. Choisissez l'endpoint cible (la table de base ou la vue avec trigger).

## Recommandations

1. **Préférez les vues avec Triggers** : C'est la méthode la plus robuste car elle garantit l'intégrité des données côté serveur.
2. **Utilisez des alias clairs** : Dans vos vues, nommez clairement les colonnes jointes pour éviter les conflits (ex: `commune_id` vs `commune_nom`).
3. **OpenAPI** : PostgREST génère automatiquement la documentation OpenAPI pour les vues. Le plugin l'utilise pour savoir quelles colonnes sont éligibles à l'envoi.
