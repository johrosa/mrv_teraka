# -*- coding: utf-8 -*-
"""
Configuration des correspondances couche QGIS -> endpoint PostgREST.
"""

import json
import os
import re
from typing import Dict

MAPPING_FILENAME = 'layer_table_mapping.json'
DEFAULT_GEOM_FIELD = 'geom'
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
        return {
            'endpoint': str(mapping.get('endpoint', normalize_layer_name_to_endpoint(layer_name))),
            'geom_field': str(mapping.get('geom_field', DEFAULT_GEOM_FIELD)),
            'pk_field': str(mapping.get('pk_field', DEFAULT_PK_FIELD))
        }

    return {
        'endpoint': normalize_layer_name_to_endpoint(layer_name),
        'geom_field': DEFAULT_GEOM_FIELD,
        'pk_field': DEFAULT_PK_FIELD
    }


def load_layer_mapping(plugin_dir: str) -> Dict[str, Dict[str, str]]:
    """Charge les correspondances depuis un fichier JSON optionnel."""
    config_path = os.path.join(plugin_dir, MAPPING_FILENAME)
    if not os.path.exists(config_path):
        return {}

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            content = json.load(f)
            raw_mappings = content.get('mappings', {})
            normalized = {}
            for layer_name, mapping in raw_mappings.items():
                normalized[str(layer_name)] = normalize_layer_mapping(str(layer_name), mapping)
            return normalized
    except Exception:
        return {}
