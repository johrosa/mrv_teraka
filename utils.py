# -*- coding: utf-8 -*-
import re

# Pre-compiled regular expression for HTML tag detection to avoid repeated compilation overhead.
_HTML_TAG_RE = re.compile(
    r'<(?:!doctype|html|head|body|div|span|p|h[1-6]|br|strong|em|ul|ol|li|table|tr|td|th)',
    re.IGNORECASE
)


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
        # Fast exit if text is empty, not a string, or contains no '<' character
        if not text or not isinstance(text, str) or '<' not in text:
            return False
        return bool(_HTML_TAG_RE.search(text))

    @staticmethod
    def is_geojson(data):
        """Détecte si les données sont au format GeoJSON."""
        return isinstance(data, dict) and data.get('type') in ['FeatureCollection', 'Feature']