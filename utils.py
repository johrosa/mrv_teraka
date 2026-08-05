# -*- coding: utf-8 -*-
import json
import re


class Utils:
    DIALOG_MESSAGE_MAX_LENGTH = 1200
    DIALOG_MESSAGE_DETAIL_MAX_LENGTH = 4000

    @staticmethod
    def compact_dialog_message(message, max_length=None):
        """Prépare un message court pour QMessageBox en masquant les géométries volumineuses."""
        max_length = max_length or Utils.DIALOG_MESSAGE_MAX_LENGTH
        text = str(message or "")

        stripped = text.strip()
        if stripped.startswith(("{", "[")):
            try:
                text = json.dumps(Utils._mask_coordinates(json.loads(stripped)), ensure_ascii=False)
            except Exception:
                pass

        text = re.sub(
            r'("coordinates"\s*:\s*)\[[\s\S]{120,}?\](?=\s*[,}])',
            r'\1[coordonnées masquées]',
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r'\b(MULTIPOLYGON|POLYGON|MULTILINESTRING|LINESTRING|MULTIPOINT)\s*\(\s*\([^)]{120,}',
            r'\1(coordonnées masquées',
            text,
            flags=re.IGNORECASE,
        )

        if len(text) <= max_length:
            return text

        return (
            text[:max_length].rstrip()
            + f"\n\n... message tronqué ({len(text)} caractères au total). "
              "Voir le journal ou le panneau de résultats pour le détail complet."
        )

    @staticmethod
    def compact_dialog_detail(message):
        return Utils.compact_dialog_message(message, Utils.DIALOG_MESSAGE_DETAIL_MAX_LENGTH)

    @staticmethod
    def _mask_coordinates(value):
        if isinstance(value, dict):
            return {
                key: "[coordonnées masquées]" if str(key).lower() == "coordinates" else Utils._mask_coordinates(val)
                for key, val in value.items()
            }
        if isinstance(value, list):
            return [Utils._mask_coordinates(item) for item in value]
        return value

    @staticmethod
    def resolve_postgrest_geom_field(mapping_geom_field, layer_is_spatial):
        """Retourne le nom du champ géométrie à envoyer vers PostgREST, ou None si la couche est alphanumérique."""
        if not layer_is_spatial:
            return None

        value = str(mapping_geom_field or "").strip()
        if not value:
            return 'geom'
        return value.lower()

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
