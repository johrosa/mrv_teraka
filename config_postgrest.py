# -*- coding: utf-8 -*-
"""
Configuration des correspondances couche QGIS -> endpoint PostgREST.
"""

import json
import os
import re
from typing import Dict

MAPPING_FILENAME = 'layer_table_mapping.json'
DEFAULT_GEOM_FIELD = None
DEFAULT_PK_FIELD = 'id'


def normalize_layer_name_to_endpoint(layer_name: str) -> str:
    """Normalise un nom de couche QGIS en endpoint compatible PostgREST."""
    value = layer_name.strip().lower()
    value = value.replace(' ', '_').replace('-', '_')
    value = re.sub(r'[^a-z0-9_]', '_', value)
    value = re.sub(r'__+', '_', value)
    return value.strip('_')


def _infer_pk_from_columns(endpoint: str, columns: list) -> str:
    """
    Infère la clé primaire à partir des colonnes disponibles.
    
    Logique:
    1. Si uuid_{endpoint_name} existe dans les colonnes -> c'est la PK
    2. Sinon, si uuid_{endpoint_name_singular} existe -> c'est la PK (au cas où endpoint au pluriel)
    3. Sinon, retourner 'id' (défaut)
    
    Note: Les autres colonnes uuid_[other_name] sont des clés étrangères, pas la PK.
    """
    if not columns:
        return DEFAULT_PK_FIELD
    
    columns_lower = [col.lower() for col in columns]
    endpoint_name = endpoint.strip('/').split('/')[-1].lower()
    
    if not endpoint_name:
        return DEFAULT_PK_FIELD
    
    # Candidats pour la clé primaire UUID
    candidates = [f'uuid_{endpoint_name}']
    
    # Si l'endpoint se termine par 's', essayer sans le 's' (pluriel)
    if endpoint_name.endswith('s'):
        candidates.append(f'uuid_{endpoint_name[:-1]}')
    
    # Chercher un match exact dans les colonnes
    for candidate in candidates:
        if candidate in columns_lower:
            # Retourner le nom original (avec la casse correcte)
            for col in columns:
                if col.lower() == candidate:
                    return col
    
    # Aucun uuid_endpoint trouvé, utiliser 'id' par défaut
    return DEFAULT_PK_FIELD


def normalize_layer_mapping(layer_name: str, mapping) -> Dict[str, str]:
    """Retourne une structure de mapping normalisée pour une couche."""
    if isinstance(mapping, str):
        return {
            'endpoint': mapping,
            'geom_field': DEFAULT_GEOM_FIELD,
            'pk_field': DEFAULT_PK_FIELD
        }

    if isinstance(mapping, dict):
        endpoint = str(mapping.get('endpoint', normalize_layer_name_to_endpoint(layer_name)))
        columns = mapping.get('columns', [])
        
        # Déterminer la PK avec priorité à uuid_{endpoint_name} si elle existe:
        # 1. Essayer d'inférer uuid_{endpoint} depuis les colonnes
        # 2. Si trouvée, l'utiliser
        # 3. Sinon, utiliser la valeur explicite du JSON si présente
        # 4. Sinon, utiliser le défaut 'id'
        
        inferred_uuid_pk = _infer_pk_from_columns(endpoint, columns)
        
        if inferred_uuid_pk and inferred_uuid_pk != DEFAULT_PK_FIELD:
            # UUID matching found, use it as PK
            pk_field = inferred_uuid_pk
        elif 'pk_field' in mapping and mapping.get('pk_field'):
            # Use explicit pk_field from JSON
            pk_field = str(mapping.get('pk_field'))
        else:
            # Use default
            pk_field = DEFAULT_PK_FIELD
        
        normalized = {
            'endpoint': endpoint,
            'geom_field': mapping.get('geom_field') if mapping.get('geom_field') is not None else None,
            'pk_field': pk_field
        }
        if isinstance(columns, list):
            normalized['columns'] = columns
        if isinstance(mapping.get('field_map'), dict):
            normalized['field_map'] = mapping['field_map']
        return normalized

    return {
        'endpoint': normalize_layer_name_to_endpoint(layer_name),
        'geom_field': DEFAULT_GEOM_FIELD,
        'pk_field': DEFAULT_PK_FIELD
    }


def load_layer_mapping(plugin_dir: str) -> Dict[str, Dict[str, str]]:
    """
    Charge les correspondances depuis le fichier JSON.
    Inclut une validation de base pour s'assurer que le format est correct.
    """
    config_path = os.path.join(plugin_dir, MAPPING_FILENAME)
    if not os.path.exists(config_path):
        # Logique de repli ou création par défaut si nécessaire
        return {}

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            content = json.load(f)
            raw_mappings = content.get('mappings', {})
            normalized = {}
            for layer_name, mapping in raw_mappings.items():
                norm = normalize_layer_mapping(str(layer_name), mapping)
                normalized[str(layer_name)] = norm
            return normalized
    except Exception as e:
        # En cas d'erreur JSON, on retourne un dictionnaire vide pour éviter le crash
        print(f"Erreur lors du chargement du mapping : {e}")
        return {}

def get_geometric_mappings(mappings: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    """Retourne uniquement les tables ayant un champ géométrie configuré."""
    return {
        name: config
        for name, config in mappings.items()
        if config.get('geom_field')
    }
