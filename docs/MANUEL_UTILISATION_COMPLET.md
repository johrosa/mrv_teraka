# Manuel d'utilisation complet - MRV Teraka

Version du manuel : 2026-06-23  
Plugin : MRV Teraka pour QGIS  
Public : operateurs terrain, validateurs MRV, superviseurs, administrateurs et support technique.

## 1. Objectif du plugin

MRV Teraka est un plugin QGIS destine a l'equipe MRV iTeraka. Il sert a charger les donnees de l'API Teraka, preparer des missions terrain Mergin Maps, recuperer les donnees collectees, les controler, les valider et publier les donnees finales dans le backend Django/PostgREST.

Le principe central est simple : les donnees terrain ne doivent pas partir directement en production sans validation. Le plugin organise donc un cycle complet :

1. Connexion a l'API.
2. Chargement ou analyse des couches QGIS.
3. Mapping couche QGIS -> endpoint API.
4. Filtrage par region, district et communes.
5. Preparation d'une mission terrain Mergin Maps.
6. Recuperation des donnees collectees.
7. Validation metier et comparaison avec la base.
8. Fusion et publication vers l'API Teraka.

## 2. Methode anti-oubli utilisee pour ce manuel

Pour eviter d'omettre une fonctionnalite, ce manuel a ete construit a partir de quatre sources :

- L'interface du dock principal : onglets, boutons, champs et journaux.
- Les dialogues secondaires : authentification, assistant projet, mapping de champs, validation, selection de tables.
- Les fonctions metier du plugin : chargement API, migration, mission Mergin, validation, synchronisation, mappings.
- Les fichiers de support : client PostgREST, gestion JWT, bridge Mergin, moteur de regles metier, utilitaires de couches.

La section 18 contient une matrice de couverture. Chaque action visible y est associee a son effet. Utilisez cette matrice comme checklist de relecture avant de livrer la documentation a une equipe.

## 3. Prerequis

### 3.1 Logiciels

- QGIS 3.36 minimum, selon `metadata.txt`.
- Plugin MRV Teraka installe dans le profil QGIS.
- Acces a une API Teraka compatible Django/PostgREST.
- Optionnel mais recommande : plugin officiel Mergin Maps installe et connecte dans QGIS.
- Optionnel : dossier local "Mergin Projects" ou dossier configure par le plugin officiel Mergin Maps.

### 3.2 Comptes et droits

- Un compte API Teraka avec identifiant et mot de passe.
- Des droits de lecture pour charger les donnees.
- Des droits d'ecriture pour migrer ou publier vers l'API.
- Un role validateur, administrateur, superviseur, `mrv_l3` ou `mrv` pour valider et publier les collectes.
- Optionnel : un compte Mergin Maps si la mission doit etre envoyee dans le cloud Mergin.

### 3.3 Donnees attendues

Les couches QGIS doivent etre des couches vectorielles valides. Les fournisseurs reconnus dans plusieurs chemins du plugin sont notamment :

- `ogr`
- `postgres`
- `memory`

Les couches systeme `spatial_ref_sys` et `geometry_columns` sont ignorees dans les migrations.

## 4. Ouverture du plugin

Dans QGIS, le plugin ajoute :

- Une entree de menu : `MRV Teraka`.
- Une barre d'outils : `MrvTeraka`.
- Un bouton de connexion.
- Un bouton principal `iTeraka` qui ouvre le panneau lateral.

Lorsque le panneau est ouvert, il affiche :

- Un en-tete avec l'etat de connexion.
- Le nom de l'utilisateur, son role et l'URL API si connecte.
- Le bouton `Quitter` pour se deconnecter.
- L'onglet `Missions`.
- L'onglet `Reglages`.

Si aucun jeton valide n'est disponible, les groupes de travail sont desactives. Il faut se connecter avant de charger, comparer, deployer, valider ou publier.

## 5. Connexion et deconnexion

### 5.1 Ouvrir le dialogue de connexion

Cliquez sur le bouton de connexion dans la barre d'outils. Le dialogue `Authentification MrvTeraka` apparait.

Champs disponibles :

- `Mode API` : choisir entre `Django` et `PostgREST (Standalone)`.
- `URL API` : URL de base, par exemple `http://localhost:8050`.
- `Email/Utilisateur` : identifiant API.
- `Mot de passe` : mot de passe API.
- `Afficher le mot de passe` : rend le mot de passe visible temporairement.
- `Memoriser les identifiants` : sauvegarde l'URL, le mode et le nom utilisateur. Le mot de passe n'est pas sauvegarde.

Actions :

- `Se connecter` : lance l'authentification.
- `Annuler` : ferme le dialogue sans connexion.

### 5.2 Modes API

En mode `Django`, l'URL est normalisee vers le proxy de donnees :

- `http://serveur` devient `http://serveur/api/data/`.
- `http://serveur/api` devient `http://serveur/api/data/`.
- `http://serveur/api/data` est conserve.

En mode `PostgREST (Standalone)`, le plugin utilise l'URL comme base PostgREST directe.

### 5.3 Jeton JWT

Apres connexion, le jeton JWT est stocke dans `QSettings` avec :

- le jeton,
- l'URL API,
- le mode API,
- la date d'expiration.

Le plugin relit le jeton au demarrage et le verifie. Si le jeton est expire ou refuse par le serveur, il est supprime et l'utilisateur doit se reconnecter.

### 5.4 Roles

Le plugin lit le role dans le JWT a partir de champs courants comme `role`, `roles`, `group`, `groups` ou `is_validator`.

Les actions de validation et de publication sont reservees aux profils dont le role contient notamment :

- `validator`
- `validateur`
- `admin`
- `superviseur`
- `mrv_l3`
- `mrv`

### 5.5 Deconnexion

Cliquez sur `Quitter`. Le plugin demande confirmation, supprime le jeton stocke, desactive les groupes de travail et remet l'etat a `Deconnecte`.

## 6. Panneau principal - Onglet Missions

L'onglet `Missions` contient trois groupes :

- `Projets de Suivi`
- `Outils de Donnees`
- `Cycle des Missions Teraka`

Il contient aussi une barre de progression et un journal de mission.

## 7. Projets de Suivi

### 7.1 Liste des projets

La liste des projets est remplie depuis :

- les projets locaux enregistres par le plugin officiel Mergin Maps,
- le dossier `Mergin/lastUsedDownloadDir` si disponible,
- le dossier `~/Mergin Projects` en fallback,
- les dossiers contenant un fichier `.qgs` ou `.qgz`.

### 7.2 Ouvrir

Le bouton `Ouvrir` charge le projet QGIS selectionne. Si le chargement reussit, le plugin lance l'assistant projet pour analyser les couches et proposer les mappings.

### 7.3 Nouveau

Le bouton `Nouveau` demande un nom de projet, cree un dossier Mergin local, ecrit le projet QGIS courant dans ce dossier et cree une entree de workflow interne. Si le plugin officiel Mergin Maps est connecte, le projet est aussi cree et pousse vers Mergin Maps.

Le projet contient les tables mappées detectees dans le projet QGIS courant.

## 8. Filtres geographiques

Les filtres geographiques se trouvent dans `Outils de Donnees`.

### 8.1 Region

La liste `Region` est remplie a partir de la table `communes`, si les colonnes disponibles le permettent. Le plugin cherche des valeurs de region dans les donnees API.

### 8.2 District

La liste `District` depend de la region selectionnee. Elle permet de restreindre les donnees a charger, comparer, importer ou publier.

### 8.3 Communes

La liste des communes depend du district selectionne. Chaque commune est cochable. La case `Toutes les communes` coche ou decoche toutes les communes visibles.

### 8.4 Effet des filtres

Les filtres sont appliques aux endpoints qui contiennent des colonnes compatibles, notamment `c_com` ou des colonnes de secteur comme :

- `secteur`
- `district`
- `nom_secteur`
- `nom_district`
- `commune`

Si des communes sont selectionnees, le plugin construit un filtre PostgREST de type `c_com=in.(...)`. Si aucune commune n'est selectionnee mais qu'un district est defini, le plugin peut interroger `communes` pour deduire les codes communes.

## 9. Outils de Donnees

### 9.1 Couche

Le champ `Couche` est un combo editable. Il liste les endpoints ou mappings disponibles. Il peut aussi recevoir un endpoint saisi manuellement.

### 9.2 Charger

`Charger` recupere les donnees de l'endpoint choisi depuis l'API.

Comportement :

- Si un endpoint est saisi, il charge cet endpoint.
- Si aucun endpoint n'est saisi, il charge les couches mappées du projet.
- Les filtres region, district et communes sont appliques si possible.
- Si les donnees sont GeoJSON, une couche QGIS est creee depuis un fichier temporaire.
- Sinon, une couche memoire QGIS est creee a partir de la liste de dictionnaires.
- Les proprietes de couche suivantes sont renseignees : `postgrest:endpoint`, `postgrest:geom_field`, `postgrest:pk_field`.

### 9.3 Verifier

`Verifier` compare le projet courant avec la base.

Le rapport affiche :

- l'URL API connectee,
- le filtre secteur s'il existe,
- le nombre de communes selectionnees,
- le nombre d'enregistrements par endpoint,
- le nombre de couches vectorielles locales detectees.

Cette action ne modifie pas les donnees.

### 9.4 Actualiser

`Actualiser` recharge les donnees depuis l'API. Cette action remet a zero les donnees validees en attente et desactive la publication jusqu'a une nouvelle validation.

### 9.5 Assistant Projet

`Assistant Projet` analyse toutes les couches vectorielles du projet courant. Il detecte :

- les couches deja mappées via `postgrest:endpoint`,
- les mappings suggeres par ressemblance de nom,
- les couches spatiales et alphanumeriques.

Il ouvre ensuite le dialogue `Analyse et Actions du Projet`.

## 10. Assistant Projet et mappings

### 10.1 Tableau d'analyse

Le dialogue affiche une ligne par couche QGIS avec :

- une case de selection,
- le nom de la couche,
- le type : `Spatial` ou `Alphanumerique`,
- la table API / endpoint,
- un bouton de configuration des field mappings.

Les endpoints peuvent etre choisis dans une liste ou saisis manuellement.

### 10.2 Field mappings

Le bouton `Configurer...` ouvre le dialogue de mapping des champs.

Chaque champ QGIS peut etre :

- inclus,
- exclu,
- conserve avec le meme nom,
- renomme vers une colonne API.

Si le schema API est connu, le dialogue propose les colonnes API attendues. Ce mapping est applique avant les envois API et avant la validation des donnees locales.

### 10.3 Actions disponibles

L'assistant propose quatre actions :

- `Migration Initiale` : pousser les donnees locales vers l'API.
- `Workflow de Collecte` : preparer une mission terrain Mergin Maps.
- `Mise a jour / Rafraichir` : telecharger les donnees API vers les couches QGIS existantes.
- `Mettre a jour le mapping local` : enregistrer les correspondances dans `layer_table_mapping.json`.

### 10.4 Mise a jour du mapping local

Cette action ecrit les correspondances selectionnees dans `layer_table_mapping.json`, avec :

- l'endpoint,
- le champ geometrie,
- la cle primaire,
- les colonnes connues,
- le field map s'il existe.

Elle renseigne aussi les proprietes personnalisées des couches QGIS.

## 11. Cycle des Missions Teraka

Le cycle est represente par quatre boutons :

1. `Preparer Terrain (Mergin Maps)`
2. `Recuperer Donnees`
3. `Valider Collecte`
4. `Publier vers l'API Teraka`

Une barre de progression indique l'etat du traitement. Le journal de mission affiche les messages, erreurs et confirmations.

## 12. Preparer Terrain (Mergin Maps)

### 12.1 But

Cette action cree une mission terrain exploitable dans Mergin Maps.

### 12.2 Selection des couches

Si des mappings sont deja disponibles, le plugin les reutilise. Sinon il ouvre l'assistant projet pour confirmer les correspondances.

Si aucune couche mappée n'est selectionnee, la preparation s'arrete.

### 12.3 Nom de mission

Le plugin propose un nom du type :

- `mission_<district>_<timestamp>` si un district est selectionne,
- `mission_<timestamp>` sinon.

Un dialogue permet de confirmer ou modifier le nom. Le nom doit rester compatible avec un dossier et un projet Mergin : caracteres alphanumeriques, tirets ou underscores.

### 12.4 Creation du workflow local

Le plugin cree une entree de workflow interne avec :

- un identifiant de projet,
- le nom de la mission,
- la liste des endpoints sources,
- l'etape de workflow.

Les fichiers sont stockes dans `mergin_workflows/projects/<project_id>/`.

### 12.5 GeoPackage

Le plugin exporte les couches vers `mission_data.gpkg`.

Il exporte :

- les couches mappées, avec un nom de couche GeoPackage base sur l'endpoint,
- les couches vectorielles non mappées comme couches de support, pour conserver les formulaires ou relations utiles.

Les noms sont normalises et rendus uniques.

### 12.6 Projet QGIS de mission

Le plugin cree un projet `.qgz` de mission dans le dossier du workflow. Il copie :

- le CRS du projet courant,
- les couches exportees depuis le GeoPackage,
- les styles,
- l'etiquetage,
- l'opacite,
- la configuration des formulaires,
- les widgets editeurs,
- les references de formulaires entre couches,
- l'arborescence des groupes et la visibilite des couches.

Si le projet courant contient un fond `Google Hybrid` avec l'URL XYZ attendue, le plugin l'ajoute aussi au projet de mission.

### 12.7 Remplissage automatique de l'operateur

Si la table contient `uuid_operateur` et que le JWT contient l'UUID utilisateur, le projet de mission configure une valeur par defaut pour renseigner automatiquement `uuid_operateur` lors de la saisie.

### 12.8 Snapshot d'origine

Le plugin sauvegarde les donnees exportees dans `exported_data.json`. Ce snapshot sert a comparer les donnees terrain avec l'etat initial au retour de mission.

### 12.9 Envoi vers Mergin Maps

Trois cas existent :

- Plugin officiel Mergin Maps connecte : le plugin cree le projet et pousse le dossier local via le client Mergin officiel.
- Client API Mergin natif disponible avec jeton : le plugin cree le projet et uploade le GeoPackage et le projet QGIS.
- Aucun client Mergin connecte : le projet reste local et un message indique que Mergin Maps n'est pas connecte.

## 13. Recuperer Donnees

`Recuperer Donnees` analyse le projet QGIS actif apres retour terrain.

Comportement :

1. Analyse des couches vectorielles du projet.
2. Selection des couches ayant un mapping.
3. Extraction des entites locales.
4. Application du field map local si configure.
5. Construction d'un payload par endpoint.
6. Chargement des donnees originales depuis l'API avec les filtres geographiques.
7. Activation de la validation.
8. Ouverture automatique de la validation.

Si aucune couche mappée n'est trouvee, le plugin affiche un avertissement.

## 14. Valider Collecte

### 14.1 Acces reserve

Cette action est reservee aux validateurs. Si l'utilisateur n'a pas le bon role, le plugin affiche `Acces refuse`.

### 14.2 Ouverture automatique

Si aucune donnee n'est prete, le plugin lance d'abord `Recuperer Donnees`. Sinon il ouvre le dialogue `Validation des Donnees Collectees`.

### 14.3 Multi-table

Le dialogue accepte une seule table ou plusieurs endpoints. En multi-table, un selecteur `Table a valider` permet de passer d'une table a l'autre.

### 14.4 Onglet Vue d'ensemble

Cet onglet affiche :

- les regles metier a executer,
- le bouton `Lancer verification`,
- le total collecte,
- le total original,
- le nombre de nouvelles entrees,
- le statut de validation,
- les recommandations.

### 14.5 Regles metier

Le moteur `BusinessRulesEngine` contient des regles pour certaines tables :

- `arbre_gps` : diametre positif, hauteur realiste, espece renseignee.
- `bosquet_gps` : nom bosquet present, `c_com` valide.
- `communes` : nom present, code commune valide.
- `pg_gps` : code PG present, commune valide.
- `membre` : UUID membre present, nom membre present.
- `parcelle` : surface positive, proprietaire renseigne.

Lorsqu'une anomalie est trouvee :

- la ligne est marquee en orange,
- le commentaire de ligne recoit le message d'erreur,
- un tooltip detaille les anomalies,
- l'onglet Validation est affiche,
- les recommandations sont completees.

### 14.6 Onglet Donnees

Cet onglet contient deux sous-onglets :

- `Donnees Originales (Base)` : donnees chargees depuis l'API ou snapshot initial.
- `Donnees Collectees (Terrain)` : donnees issues des couches terrain.

Les listes et objets complexes sont tronques pour l'affichage.

### 14.7 Onglet Comparaison

Cet onglet permet de comparer un enregistrement a la fois.

Colonnes :

- `Champ`
- `Base`
- `Terrain`
- `Valeur finale`

L'utilisateur peut choisir la valeur de base ou la valeur terrain via les cases a cocher, ou modifier manuellement la valeur finale. La donnee collectee est mise a jour en memoire.

### 14.8 Onglet Validation

Cet onglet affiche une ligne par enregistrement avec :

- `ID`
- `Statut` : Valide, A reviser, Rejeter, Nouveau.
- `Changements`
- `Type` : Nouveau, Modifie, Inchange.
- `Action` : Fusionner, Remplacer, Archiver, Manuel.
- `Commentaire`

En selectionnant une ligne, le detail affiche les champs modifies avec valeur avant et apres.

### 14.9 Boutons du dialogue de validation

- `Fusion Automatique` : confirme puis marque toutes les donnees comme pretes a fusionner.
- `Revision Manuelle` : bascule vers l'onglet Validation.
- `Exporter Rapport` : cree un fichier `validation_report.json` dans le dossier temporaire systeme.
- `Annuler` : ferme sans validation.
- `Valider et Fusionner` : accepte les donnees courantes comme validees.

### 14.10 UUID verificateur

Au moment de l'acceptation, si l'UUID utilisateur est disponible, le plugin renseigne `uuid_verificateur` dans les donnees validees.

## 15. Publier vers l'API Teraka

### 15.1 Acces reserve

La publication est reservee aux validateurs. Sans role compatible, le plugin bloque l'action.

### 15.2 Donnees requises

Il faut avoir des donnees validees. Sinon le plugin indique qu'aucune donnee validee n'est disponible.

### 15.3 Fusion

Pour chaque endpoint valide :

1. Le plugin prepare les lignes selon les colonnes attendues.
2. Il ajoute `uuid_verificateur` si applicable.
3. Il charge les donnees originales depuis `exported_data.json` ou depuis l'API.
4. Il detecte les conflits selon le champ `pk_field`.
5. Il affiche un resume de fusion.
6. Si l'utilisateur confirme, il applique les actions.

Types detectes :

- Supprimes : presents dans l'original, absents de la collecte.
- Ajoutes : presents dans la collecte, absents de l'original.
- Modifies : meme identifiant, contenu different.

Actions :

- insertion des ajouts,
- mise a jour des modifications,
- suppression des elements supprimes si la strategie de merge l'applique.

### 15.4 Resultats de synchronisation

Si un projet de workflow est actif, le plugin ecrit :

- `merge_results.json`
- `sync_results.json`

Le bouton de publication est ensuite desactive et les donnees validees en memoire sont remises a zero.

## 16. Migration initiale vers l'API

La migration initiale est accessible depuis l'assistant projet avec l'action `Migration Initiale`.

### 16.1 Preparation

Le plugin :

- recupere les couches selectionnees,
- applique les field mappings,
- filtre les colonnes selon le schema API,
- convertit la geometrie vers GeoJSON,
- remplace les chaines vides par `None`,
- renseigne `uuid_operateur` si possible,
- nettoie certains champs UUID invalides,
- respecte un ordre de priorite pour certaines tables.

Ordre prioritaire :

1. `communes`
2. `pg_gps`
3. `pg_infos`
4. `membre`
5. `bosquet_gps`
6. `arbre_gps`
7. `arbre_baseline`

### 16.2 Upsert et conflits

Les donnees sont envoyees par paquets de 5000 lignes. L'envoi utilise l'upsert PostgREST avec `Prefer: resolution=merge-duplicates`.

Le champ `on_conflict` est choisi ainsi :

- priorite a `uuid_<endpoint>` si la colonne existe,
- tentative simple au singulier si l'endpoint finit par `s`,
- sinon fallback sur `pk_field`, souvent `id`.

Cela permet d'eviter les doublons quand les tables possedent un UUID metier propre.

### 16.3 Journal et erreurs

La migration tourne dans une tache QGIS. Les erreurs par paquet sont ajoutees au journal. Les erreurs PostgREST/Django sont affichees avec leur code, message et detail quand ils sont disponibles.

## 17. Onglet Reglages

L'onglet `Reglages` contient `Synchronisation API`.

### 17.1 Synchroniser les Listes

Le bouton `Synchroniser les Listes` interroge le schema API, reconstruit les mappings locaux et met a jour :

- la liste des couches/endpoints,
- les regions,
- le fichier `layer_table_mapping.json`.

Le plugin detecte aussi le champ geometrie parmi :

- un champ au format `geojson`,
- `geom`,
- `geometry`,
- `the_geom`.

## 18. Matrice de couverture des fonctionnalites

Cette matrice sert de checklist pour verifier que le manuel couvre l'interface.

| Zone | Element | Fonction utilisateur | Effet principal |
| --- | --- | --- | --- |
| Barre d'outils | Connexion | Se connecter a l'API | Ouvre le dialogue d'authentification |
| Barre d'outils | iTeraka | Ouvrir le plugin | Affiche le dock MRV Teraka |
| En-tete dock | Statut | Voir connexion | Affiche connecte/deconnecte |
| En-tete dock | Quitter | Se deconnecter | Supprime le jeton et desactive les outils |
| Missions / Projets | Liste projets | Choisir projet local Mergin | Liste les projets detectes |
| Missions / Projets | Ouvrir | Charger un projet QGIS | Charge le projet et lance l'analyse |
| Missions / Projets | Nouveau | Creer projet Mergin local/cloud | Ecrit le projet et cree le workflow |
| Missions / Filtres | Region | Restreindre zone | Filtre les districts/communes |
| Missions / Filtres | District | Restreindre zone | Filtre les communes et les requetes |
| Missions / Filtres | Toutes les communes | Cocher/decocher communes | Selection groupée |
| Missions / Donnees | Couche | Choisir endpoint | Determine ce qui sera charge |
| Missions / Donnees | Charger | Charger donnees API | Cree ou met a jour des couches QGIS |
| Missions / Donnees | Verifier | Comparer projet/base | Affiche des compteurs |
| Missions / Donnees | Actualiser | Recharger depuis API | Recharge et remet la validation a zero |
| Missions / Donnees | Assistant Projet | Diagnostiquer le projet | Ouvre mapping/action |
| Assistant Projet | Selection | Choisir couches | Controle quelles couches seront traitees |
| Assistant Projet | Endpoint | Mapper couche -> API | Definit la table API cible |
| Assistant Projet | Configurer | Mapper champs | Renomme/exclut/inclut les champs |
| Assistant Projet | Migration Initiale | Envoyer local vers API | Lance upsert par endpoint |
| Assistant Projet | Workflow Collecte | Creer mission terrain | Lance preparation Mergin |
| Assistant Projet | Rafraichir | API vers QGIS | Remplace les entites locales |
| Assistant Projet | Mettre a jour mapping | Sauvegarder mapping | Ecrit `layer_table_mapping.json` |
| Cycle Mission | 1. Preparer Terrain | Generer mission Mergin | Cree GPKG, projet QGIS, snapshot, push si possible |
| Cycle Mission | 2. Recuperer Donnees | Importer retour terrain | Lit couches locales et charge original API |
| Cycle Mission | 3. Valider Collecte | Controler donnees | Ouvre dialogue de validation |
| Cycle Mission | 4. Publier API | Finaliser | Fusionne et ecrit dans l'API |
| Validation | Vue d'ensemble | Voir stats et regles | Lance controles metier |
| Validation | Donnees | Voir base/terrain | Affiche les tableaux |
| Validation | Comparaison | Resoudre champ par champ | Choix base/terrain/final |
| Validation | Validation | Revue ligne par ligne | Statut, action, commentaire |
| Validation | Fusion Automatique | Preparer tout a fusionner | Accepte les donnees |
| Validation | Revision Manuelle | Revoir les lignes | Va a l'onglet Validation |
| Validation | Exporter Rapport | Sortir rapport JSON | Ecrit `validation_report.json` temporaire |
| Validation | Valider et Fusionner | Confirmer validation | Renseigne `uuid_verificateur` |
| Reglages | Synchroniser les Listes | Mettre a jour schema/mappings | Recharge endpoints, colonnes, regions |

## 19. Fichiers crees ou utilises

### 19.1 Configuration

- `layer_table_mapping.json` : mappings couche/endpoint/colonnes/champs.
- `QSettings iTeraka/MrvTeraka` : URL, mode, nom utilisateur, jeton JWT et expiration.
- `QSettings Mergin/...` : chemins et projets locaux du plugin officiel Mergin Maps.

### 19.2 Workflow mission

Dans `mergin_workflows/projects/<project_id>/` :

- `metadata.json` : identite du projet et etapes terminees.
- `mission_data.gpkg` : GeoPackage terrain.
- `<nom_mission>.qgz` : projet QGIS de mission.
- `exported_data.json` : snapshot initial.
- `imported_data.json` : donnees importees.
- `validation_results.json` : resultat de validation.
- `merge_results.json` : resultat de fusion.
- `sync_results.json` : resultat de publication.

Dans `mergin_workflows/backups/<project_id>/` :

- sauvegardes horodatees des donnees importees.

### 19.3 Rapport temporaire

- `validation_report.json` dans le dossier temporaire systeme.

## 20. Gestion des erreurs

### 20.1 Erreurs Django/PostgREST

Si une erreur HTTP contient une page HTML Django, le plugin essaie d'afficher un viewer d'erreur lisible. Sinon il affiche le texte brut dans une boite de dialogue.

### 20.2 Token invalide

Si le token est absent, expire ou refuse, le plugin demande une nouvelle authentification.

### 20.3 Projet Mergin introuvable

Si aucun projet Mergin local n'est trouve, verifier :

- que le plugin officiel Mergin Maps est installe,
- que les projets ont ete telecharges localement,
- que le dossier `Mergin Projects` existe,
- que les dossiers contiennent un fichier `.qgs` ou `.qgz`.

### 20.4 Aucune couche mappée

Utiliser `Assistant Projet`, choisir les endpoints et enregistrer le mapping local si besoin.

### 20.5 Validation bloquee

Verifier :

- que les donnees ont ete recuperees,
- que l'utilisateur a un role validateur,
- que le bouton `Valider Collecte` est active,
- que le JWT contient un role reconnu.

### 20.6 Publication impossible

Verifier :

- que les donnees ont ete validees,
- que l'utilisateur est validateur,
- que l'API accepte INSERT/UPDATE/DELETE,
- que les champs obligatoires sont presents,
- que `on_conflict` pointe vers un champ unique existant.

## 21. Bonnes pratiques

- Toujours se connecter avant de charger ou preparer une mission.
- Synchroniser les listes API apres evolution du schema backend.
- Utiliser les filtres district/communes pour eviter de charger trop de donnees.
- Utiliser `Assistant Projet` avant une migration initiale.
- Verifier les field mappings quand les noms QGIS ne correspondent pas aux colonnes API.
- Ne pas modifier manuellement les identifiants techniques si ce n'est pas necessaire.
- Valider les donnees avant publication, surtout les geometries et champs obligatoires.
- Lire le journal de mission apres chaque action longue.
- En cas de doute, utiliser `Verifier` avant `Publier vers l'API Teraka`.

## 22. Parcours utilisateur recommandes

### 22.1 Charger des donnees depuis l'API

1. Se connecter.
2. Choisir region, district et communes si besoin.
3. Choisir une couche / endpoint.
4. Cliquer `Charger`.
5. Controler la couche creee dans QGIS.

### 22.2 Rafraichir des couches existantes

1. Se connecter.
2. Ouvrir le projet QGIS.
3. Cliquer `Assistant Projet`.
4. Verifier les mappings.
5. Choisir `Mise a jour / Rafraichir`.
6. Confirmer.

### 22.3 Creer une mission terrain

1. Se connecter.
2. Ouvrir ou preparer le projet QGIS source.
3. Choisir les filtres geographiques.
4. Cliquer `Assistant Projet` ou `Preparer Terrain`.
5. Confirmer les mappings.
6. Donner un nom a la mission.
7. Attendre la creation du GeoPackage et du projet QGIS.
8. Verifier si le projet a ete pousse vers Mergin Maps ou seulement cree localement.

### 22.4 Recuperer et valider une mission

1. Ouvrir le projet terrain revenu de Mergin Maps.
2. Cliquer `Recuperer Donnees`.
3. Laisser le plugin analyser les couches mappées.
4. Dans le dialogue de validation, consulter Vue d'ensemble, Donnees, Comparaison et Validation.
5. Lancer les regles metier.
6. Corriger ou commenter les anomalies.
7. Cliquer `Valider et Fusionner`.

### 22.5 Publier en production

1. S'assurer que la validation est terminee.
2. Cliquer `Publier vers l'API Teraka`.
3. Lire le resume de fusion.
4. Confirmer uniquement si les ajouts, modifications et suppressions sont attendus.
5. Verifier le message final.

### 22.6 Faire une migration initiale

1. Ouvrir le projet contenant les donnees locales source.
2. Cliquer `Assistant Projet`.
3. Mapper les couches vers les endpoints.
4. Configurer les field mappings.
5. Choisir `Migration Initiale`.
6. Confirmer le nombre de couches.
7. Attendre la fin de la tache QGIS.
8. Lire les erreurs eventuelles par paquet.

## 23. Notes pour le support

- Le plugin s'appuie sur le schema OpenAPI/PostgREST quand il est disponible.
- Les mappings locaux peuvent completer ou remplacer les mappings recuperes.
- Les donnees API sont paginees par defaut par pages de 1000 lignes.
- Les migrations initiales envoient par paquets de 5000 lignes.
- Les UUID sont normalises avant l'envoi et dans certains filtres.
- Les erreurs HTML Django peuvent etre affichees dans un viewer specialise.
- Le bridge Mergin privilegie le plugin officiel Mergin Maps deja connecte dans QGIS.

## 24. Limites connues

- Certaines regles metier ne couvrent qu'une partie des tables et doivent etre etendues dans `business_rules.py`.
- Le dialogue de validation compare principalement par position et par champ, tandis que la fusion utilise le `pk_field`.
- Si le role du JWT utilise un nom non reconnu, les boutons de validation/publication peuvent rester desactives.
- Si le schema API ne fournit pas les colonnes, le filtrage strict des champs est moins precis.
- Si Mergin Maps n'est pas connecte, la mission peut etre creee localement mais pas publiee automatiquement.

## 25. Checklist finale avant depart terrain

- Connexion API valide.
- Plugin officiel Mergin Maps connecte si publication cloud requise.
- Region/district/communes selectionnes.
- Couches source presentes et valides.
- Mappings couche -> endpoint verifies.
- Field mappings verifies.
- Formulaires QGIS et styles controles.
- Mission creee avec GeoPackage.
- Projet Mergin ouvert/teste avant depart.
- Journal de mission sans erreur critique.

## 26. Checklist finale avant publication API

- Donnees retour terrain importees.
- Regles metier executees.
- Anomalies corrigees ou commentees.
- Comparaison base/terrain relue.
- `uuid_verificateur` ajoute automatiquement si disponible.
- Resume de fusion coherent.
- Droits API verifies.
- Publication terminee sans erreur.

