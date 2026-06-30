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


def normalize_layer_mapping(layer_name: str, mapping) -> Dict[str, str]:
    """Retourne une structure de mapping normalisée pour une couche."""
    if isinstance(mapping, str):
        return {
            'endpoint': mapping,
            'geom_field': DEFAULT_GEOM_FIELD,
            'pk_field': DEFAULT_PK_FIELD
        }

    if isinstance(mapping, dict):
        normalized = {
            'endpoint': str(mapping.get('endpoint', normalize_layer_name_to_endpoint(layer_name))),
        'geom_field': mapping.get('geom_field') if mapping.get('geom_field') is not None else None,
            'pk_field': str(mapping.get('pk_field', DEFAULT_PK_FIELD))
        }
        if isinstance(mapping.get('columns'), list):
            normalized['columns'] = mapping['columns']
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
