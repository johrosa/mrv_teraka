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
                info['mapping'] = endpoint
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
        norm_name = name.lower().replace(' ', '_')

        # Match exact
        for mapping_name, mapping in self.mappings.items():
            norm_mapping_name = str(mapping_name).lower().replace(' ', '_')
            endpoint = mapping.get('endpoint') if isinstance(mapping, dict) else mapping_name
            if norm_mapping_name == norm_name:
                return endpoint

        # Match partiel
        for mapping_name, mapping in self.mappings.items():
            endpoint = mapping.get('endpoint') if isinstance(mapping, dict) else mapping_name
            norm_mapping_name = str(mapping_name).lower().replace(' ', '_')
            norm_endpoint = str(endpoint).lower()
            if (
                norm_mapping_name in norm_name
                or norm_name in norm_mapping_name
                or norm_endpoint in norm_name
                or norm_name in norm_endpoint
            ):
                return endpoint

        return None
