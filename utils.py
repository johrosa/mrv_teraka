# -*- coding: utf-8 -*-
import re


class Utils:
    @staticmethod
    def flatten_json(data, parent_key='', sep='_'):
        """Aplatit un dictionnaire JSON récursivement."""
        if not isinstance(data, dict):
            return data
        res = {}
        for k, v in data.items():
            key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict) and 'type' not in v:
                res.update(Utils.flatten_json(v, key, sep))
            elif isinstance(v, list) and v and isinstance(v[0], dict):
                res.update(Utils.flatten_json(v[0], key, sep))
            else:
                res[key] = v
        return res

    @staticmethod
    def is_html_content(text):
        """Détecte si le texte contient du HTML."""
        if not text or not isinstance(text, str):
            return False
        return bool(re.search(r'<(?:!doctype|html|head|body|div|span|p|h[1-6]|br|strong|em|ul|ol|li|table|tr|td|th)', text, re.IGNORECASE))

    @staticmethod
    def is_geojson(data):
        """Détecte si les données sont au format GeoJSON."""
        return isinstance(data, dict) and data.get('type') in ['FeatureCollection', 'Feature']

    @staticmethod
    def normalize_uuid(value):
        """
        Nettoie un UUID en enlevant les accolades QGIS {} et en mettant en minuscule.
        """
        if not value or not isinstance(value, str):
            return value
        
        # Enlever les accolades { }
        cleaned = value.strip().replace('{', '').replace('}', '')
        
        # Vérifier si c'est un format UUID (8-4-4-4-12 hex chars)
        if re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', cleaned, re.IGNORECASE):
            return cleaned.lower()
            
        return value