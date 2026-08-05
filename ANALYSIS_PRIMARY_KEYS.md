# Analyse: Clés Primaires par Défaut dans les Mappings Couches-Endpoints

## Résumé

**❌ NON**, la clé primaire par défaut dans les mappings couches-endpoints n'est **PAS** `uuid_endpointsname`.

## Findings

### 1. Clé Primaire par Défaut
- **Définie dans**: `config_postgrest.py`, ligne 13
- **Valeur**: `'id'`
- **Code**:
```python
DEFAULT_PK_FIELD = 'id'
```

### 2. Utilisation dans les Mappings
- **Fichier**: `layer_table_mapping.json`
- **Tous les 90+ mappings** utilisent `"pk_field": "id"`
- Exemple:
```json
{
    "answer_nuisible_bosquet_baseline": {
        "endpoint": "answer_nuisible_bosquet_baseline",
        "pk_field": "id",  // <-- Toujours 'id'
        "columns": [...]
    }
}
```

### 3. Pattern `uuid_<endpoint>` 
Le pattern `uuid_<endpoint>` est utilisé différemment:

**Fonction**: `_infer_uuid_conflict_field()` dans `postgrest_client.py`, lignes 150-168
- Cherche dynamiquement un champ `uuid_<endpoint>` ou `uuid_<endpoint_name>` (sans 's')
- C'est un champ de **conflit pour les upserts**, PAS la clé primaire
- Utilisé pour les opérations de synchronisation (Mergin Maps)

**Code**:
```python
def _infer_uuid_conflict_field(self, endpoint: str, payload: List[Dict[str, Any]]) -> Optional[str]:
    """Retourne uuid_<endpoint> si ce champ est présent dans le payload."""
    endpoint_name = endpoint.strip('/').split('/')[-1].lower()
    candidates = [f'uuid_{endpoint_name}']
    if endpoint_name.endswith('s'):
        candidates.append(f'uuid_{endpoint_name[:-1]}')
    
    for candidate in candidates:
        if candidate in payload_columns:
            return candidate
    return None
```

## Conclusion

| Aspect | Valeur |
|--------|--------|
| **Clé primaire par défaut** | `'id'` |
| **Pattern uuid** | `uuid_<endpoint>` (champ de conflit seulement) |
| **Fichier config** | `config_postgrest.py` |
| **Fichier mappings** | `layer_table_mapping.json` |

---
**Généré le**: 2026-07-01 14:29:05
