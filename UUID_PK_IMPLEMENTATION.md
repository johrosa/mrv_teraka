# Implémentation: UUID comme Clé Primaire dans les Mappings

## Résumé

✅ **FAIT**: La logique d'inférence de clé primaire a été mise à jour pour utiliser automatiquement `uuid_{endpoint_name}` comme clé primaire (PK) si elle est disponible dans les colonnes du mapping.

## Changements Effectués

### 1. Nouvelle Fonction: `_infer_pk_from_columns()` 
**Fichier**: `config_postgrest.py` (lignes 15-50)

**Logique**:
- Cherche `uuid_{endpoint_name}` dans les colonnes disponibles
- Si endpoint termine par 's' (pluriel), essaie aussi `uuid_{endpoint_name[:-1]}` (singulier)
- Retourne la UUID matching si trouvée, sinon retourne `'id'` (défaut)

**Remarque Importante**: Les autres colonnes UUID (e.g., `uuid_bosquet_baseline`, `uuid_nuisible`) sont ignorées car elles sont clairement des clés étrangères (FK), pas la clé primaire de la table.

### 2. Mise à Jour: `normalize_layer_mapping()`
**Fichier**: `config_postgrest.py` (lignes 65-98)

**Nouvelle Logique de Priorité**:
1. ✅ Essayer d'inférer `uuid_{endpoint_name}` depuis les colonnes
2. ✅ Si trouvée, **l'utiliser comme PK** (nouvelle priorité)
3. ⚠️ Sinon, utiliser la valeur explicite du JSON si présente
4. 🔄 Sinon, utiliser le défaut `'id'`

**Avant**:
```python
if 'pk_field' in mapping and mapping.get('pk_field'):
    pk_field = str(mapping.get('pk_field'))  # JSON priority
else:
    pk_field = _infer_pk_from_columns(endpoint, columns)
```

**Après**:
```python
inferred_uuid_pk = _infer_pk_from_columns(endpoint, columns)
if inferred_uuid_pk and inferred_uuid_pk != DEFAULT_PK_FIELD:
    pk_field = inferred_uuid_pk  # UUID priority
elif 'pk_field' in mapping and mapping.get('pk_field'):
    pk_field = str(mapping.get('pk_field'))
else:
    pk_field = DEFAULT_PK_FIELD
```

## Résultats

### Chiffres
- **Total des mappings**: 106
- **Mappings avec UUID comme PK**: 41 (↑ de 0 précédemment)
- **Mappings restant avec 'id'**: 65 (car pas de uuid_{endpoint_name})

### Exemples de UUID PKs Détectées
1. `bosquet_baseline` → `uuid_bosquet_baseline`
2. `bosquet_suivi` → `uuid_bosquet_suivi`
3. `lutte_nuisibles` → `uuid_lutte_nuisible` (singulier)
4. `formations` → `uuid_formation`
5. `invasifs` → `uuid_invasif`

### Cas Correctement Gérés
✅ **answer_nuisible_bosquet_baseline**:
- Colonnes: `id`, `uuid_bosquet_baseline` (FK), `uuid_nuisible` (FK)
- PK retenue: `id` ✓ (pas de `uuid_answer_nuisible_bosquet_baseline`)
- Les autres UUIDs restent des FK

✅ **answer_sourcing_graine_arbre_baseline**:
- Colonnes: `uuid_answer_sourcing_graine_arbre_baseline` (PK), `uuid_arbre_baseline` (FK), `uuid_sourcing_graine` (FK)
- PK retenue: `uuid_answer_sourcing_graine_arbre_baseline` ✓

## Tests

### Tests Unitaires ✅
- `test_pk_inference.py`: 5/5 tests passés
- Cas avec UUID exact
- Cas avec UUID singulier (pluriel endpoint)
- Cas avec FKs uniquement (pas d'UUID matching)
- Cas sans UUID (défaut 'id')
- Cas avec UUID comme seule colonne

### Tests d'Intégration ✅
- `test_uuid_pk_real.py`: Chargement des vrais mappings
  - 41 UUIDs correctement détectées
  - FKs correctement distinguées
- `test_real_mappings_pk.py`: Analyse complète des mappings
  - 90 mappings avec FKs identifiés
  - 0 conflits d'UUID

## Comportement par Défaut

| Scenario | PK Utilisée |
|----------|-----------|
| UUID matching trouvée | `uuid_{endpoint_name}` ✅ |
| UUID matching + explicit JSON | `uuid_{endpoint_name}` (UUID prioritaire) ✅ |
| Pas d'UUID, explicit JSON | `{explicit_pk}` ✅ |
| Pas d'UUID, pas d'explicit | `'id'` (défaut) ✅ |

## Fichiers Modifiés
- ✏️ `config_postgrest.py` (nouvelles fonctions + logique mise à jour)

## Fichiers Ajoutés (Tests)
- ✨ `test_pk_inference.py`
- ✨ `test_real_mappings_pk.py`
- ✨ `test_uuid_pk_real.py`

---
**Date**: 2026-07-01  
**Status**: ✅ COMPLET ET TESTÉ
