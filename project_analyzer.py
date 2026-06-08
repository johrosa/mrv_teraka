# -*- coding: utf-8 -*-
from qgis.core import QgsProject, QgsMapLayer
import re

class ProjectAnalyzer:
    """Analyse automatiquement le projet QGIS pour le mapping API et la santé des données."""

    def __init__(self, layer_mappings):
        self.mappings = layer_mappings # Dict from layer_table_mapping.json or API

    def analyze_active_project(self):
        """
        Analyse les couches du projet actuel.
        Retourne un rapport de santé et des suggestions de mapping.
        """
        report = {
            'layers': [],
            'errors': [],
            'ready_for_terrain': False
        }

        layers = QgsProject.instance().mapLayers().values()
        for layer in layers:
            if layer.type() != QgsMapLayer.VectorLayer:
                continue

            info = {
                'id': layer.id(),
                'name': layer.name(),
                'mapping': None,
                'status': 'unknown',
                'is_spatial': layer.isSpatial()
            }

            # 1. Vérifier les propriétés existantes
            endpoint = layer.customProperty('postgrest:endpoint')
            if endpoint:
                info['mapping'] = self.resolve_mapping_endpoint(endpoint)
                info['status'] = 'mapped'
            else:
                # 2. Tentative de mapping automatique par nom
                match = self.find_best_match(layer.name())
                if match:
                    info['mapping'] = match
                    info['status'] = 'suggested'

            report['layers'].append(info)

        # Vérifier si on a au moins une couche mappée
        mapped_count = sum(1 for l in report['layers'] if l['mapping'])
        if mapped_count > 0:
            report['ready_for_terrain'] = True

        return report

    def find_best_match(self, name):
        """Trouve le meilleur endpoint pour un nom de couche donné."""
        if name in self.mappings:
            return self.mappings[name].get('endpoint', name)

        norm_name = self.normalize_name(name)

        # Match exact
        if norm_name in self.mappings:
            return self.mappings[norm_name].get('endpoint', norm_name)

        for mapping_name, mapping in self.mappings.items():
            endpoint = mapping.get('endpoint', mapping_name)
            norm_mapping_name = self.normalize_name(mapping_name)
            norm_endpoint = self.normalize_name(endpoint)

            if norm_mapping_name == norm_name or norm_endpoint == norm_name:
                return endpoint

        # Match partiel
        for mapping_name, mapping in self.mappings.items():
            endpoint = mapping.get('endpoint', mapping_name)
            norm_mapping_name = self.normalize_name(mapping_name)
            norm_endpoint = self.normalize_name(endpoint)

            if (
                norm_mapping_name in norm_name
                or norm_name in norm_mapping_name
                or norm_endpoint in norm_name
                or norm_name in norm_endpoint
            ):
                return endpoint

        return None

    def resolve_mapping_endpoint(self, value):
        """Retourne le vrai endpoint si value est une cle/alias de mapping."""
        if value in self.mappings:
            return self.mappings[value].get('endpoint', value)

        norm_value = self.normalize_name(value)
        for mapping_name, mapping in self.mappings.items():
            endpoint = mapping.get('endpoint', mapping_name)
            if (
                self.normalize_name(mapping_name) == norm_value
                or self.normalize_name(endpoint) == norm_value
            ):
                return endpoint

        return value

    def normalize_name(self, name):
        """Normalise les noms de couches et endpoints pour la comparaison."""
        value = str(name or '').strip().lower()
        value = value.replace(' ', '_').replace('-', '_')
        value = re.sub(r'[^a-z0-9_]', '_', value)
        value = re.sub(r'__+', '_', value)
        return value.strip('_')
