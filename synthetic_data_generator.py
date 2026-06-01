# -*- coding: utf-8 -*-
"""
A helper module to create synthetic QGIS layers for MrvTeraka testing.

The generated layers use endpoint-style names and minimal sample fields so
that the plugin can exercise its project import / validation / merge UI.
"""

import random
import uuid
from datetime import datetime
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsField,
    QgsFeature,
    QgsGeometry,
)
from qgis.PyQt.QtCore import QVariant


DEFAULT_CENTER = (47.0, -18.9)


def _make_point_wkt(x, y):
    return f"POINT({x} {y})"


def _random_point(center=DEFAULT_CENTER, radius=0.05):
    cx, cy = center
    return cx + (random.random() - 0.5) * radius, cy + (random.random() - 0.5) * radius


def _make_field(name, py_type):
    field_type = QVariant.String
    if py_type is int:
        field_type = QVariant.Int
    elif py_type is float:
        field_type = QVariant.Double
    elif py_type is bool:
        field_type = QVariant.Bool
    return QgsField(name, field_type)


def _make_value(name, py_type, index):
    if py_type is int:
        return index + 1
    if py_type is float:
        return round(1.0 + index * 0.5, 2)
    if py_type is bool:
        return index % 2 == 0
    if name.lower().endswith('date'):
        return datetime.now().isoformat()
    if 'uuid' in name.lower():
        return str(uuid.uuid4())
    if 'nom' in name.lower() or 'name' in name.lower():
        return f"Test_{name}_{index + 1}"
    if 'operateur' in name.lower():
        return f"OP{1000 + index}"
    if 'c_com' == name.lower():
        return 1
    return f"value_{index + 1}"


def _create_memory_layer(layer_name, fields, geom_type=None, feature_count=5):
    uri = f"{geom_type}?crs=EPSG:4326" if geom_type else "NoGeometry"
    layer = QgsVectorLayer(uri, layer_name, "memory")
    if not layer.isValid():
        return None

    pr = layer.dataProvider()
    qgs_fields = [_make_field(name, py_type) for name, py_type in fields]
    pr.addAttributes(qgs_fields)
    layer.updateFields()

    features = []
    for idx in range(feature_count):
        fet = QgsFeature(layer.fields())
        attrs = [_make_value(name, py_type, idx) for name, py_type in fields]
        fet.setAttributes(attrs)

        if geom_type:
            gtype = geom_type.lower()
            geom = None
            if 'point' in gtype:
                x, y = _random_point()
                geom = QgsGeometry.fromWkt(_make_point_wkt(x, y))
            elif 'line' in gtype:
                pts = [_random_point() for _ in range(2 + random.randint(0, 3))]
                wkt = 'LINESTRING(' + ','.join(f"{x} {y}" for x, y in pts) + ')'
                geom = QgsGeometry.fromWkt(wkt)
            elif 'polygon' in gtype:
                pts = [_random_point() for _ in range(3 + random.randint(0, 3))]
                if pts[0] != pts[-1]:
                    pts.append(pts[0])
                wkt = 'POLYGON((' + ','.join(f"{x} {y}" for x, y in pts) + '))'
                geom = QgsGeometry.fromWkt(wkt)
            else:
                # fallback to point
                x, y = _random_point()
                geom = QgsGeometry.fromWkt(_make_point_wkt(x, y))

            if geom and not geom.isNull():
                fet.setGeometry(geom)

        features.append(fet)

    pr.addFeatures(features)
    layer.updateExtents()
    return layer


DEFAULT_ENDPOINTS = {
    'communes': {
        'geom_type': 'Point',
        'fields': [
            ('id', int),
            ('c_com', int),
            ('nom_commun', str),
        ]
    },
    'bosquet_gps': {
        'geom_type': 'Point',
        'fields': [
            ('id', int),
            ('uuid_bosquet_gps', str),
            ('operateur_id', str),
            ('c_com', int),
        ]
    },
    'bosquet_baseline': {
        'geom_type': None,
        'fields': [
            ('id', int),
            ('uuid_bosquet_baseline', str),
            ('uuid_bosquet_gps', str),
            ('operateur_id', str),
            ('c_com', int),
            ('date_baseline', str),
        ]
    },
    'arbre_gps': {
        'geom_type': 'Point',
        'fields': [
            ('id', int),
            ('uuid_arbre_gps', str),
            ('uuid_bosquet_gps', str),
            ('c_com', int),
            ('hauteur', float),
        ]
    },
    'membre_suivi': {
        'geom_type': None,
        'fields': [
            ('id', int),
            ('uuid_membre_suivi', str),
            ('c_com', int),
            ('prenom', str),
            ('nom', str),
        ]
    },
    # Additional backend lookup tables required by dependencies
    'membre': {
        'geom_type': None,
        'fields': [
            ('id', int),
            ('uuid_membre', str),
            ('c_com', int),
            ('nom_membre', str),
        ]
    },
    'pg_infos': {
        'geom_type': None,
        'fields': [
            ('id', int),
            ('uuid_pg', str),
            ('code_pg', str),
            ('nom_pg', str),
            ('c_com', int),
        ]
    },
    'sol_couleurs': {
        'geom_type': None,
        'fields': [
            ('id', int),
            ('uuid_sol_couleur', str),
            ('nom', str),
        ]
    },
    'sol_types': {
        'geom_type': None,
        'fields': [
            ('id', int),
            ('uuid_sol_type', str),
            ('nom', str),
        ]
    },
    'topographies': {
        'geom_type': None,
        'fields': [
            ('id', int),
            ('uuid_topo', str),
            ('nom', str),
        ]
    },
    'users': {
        'geom_type': None,
        'fields': [
            ('id', int),
            ('uuid_user', str),
            ('email', str),
            ('nom', str),
        ]
    },
}


def generate_dummy_test_layers(endpoints=None, feature_count=5):
    """Create synthetic QGIS test layers named like PostgREST endpoints."""
    if endpoints is None:
        endpoints = list(DEFAULT_ENDPOINTS.keys())

    project = QgsProject.instance()
    created = []
    for endpoint in endpoints:
        config = DEFAULT_ENDPOINTS.get(endpoint)
        if not config:
            continue

        layer = _create_memory_layer(endpoint, config['fields'], geom_type=config['geom_type'], feature_count=feature_count)
        if not layer:
            continue

        layer.setCustomProperty('postgrest:endpoint', endpoint)
        layer.setCustomProperty('postgrest:geom_field', 'geom' if config['geom_type'] else '')
        layer.setCustomProperty('postgrest:pk_field', 'id')

        # Remove existing layers with the same name before adding
        for existing in project.mapLayersByName(endpoint):
            project.removeMapLayer(existing.id())

        project.addMapLayer(layer)
        created.append(endpoint)

    return created


def create_synthetic_project_data():
    """Add a default synthetic test dataset to the current QGIS project."""
    endpoints = generate_dummy_test_layers()
    return endpoints
