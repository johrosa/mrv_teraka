# -*- coding: utf-8 -*-
"""
Utilitaires pour la gestion des couches QGIS et conversion JSON/GeoJSON.
"""

import json
from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    QgsVectorLayer, QgsField, QgsFeature, QgsJsonUtils,
    QgsGeometry, QgsMapLayer
)

def is_geojson(data):
    """Vérifie si les données sont au format GeoJSON."""
    return isinstance(data, dict) and data.get('type') in ['FeatureCollection', 'Feature']

def create_vector_layer_from_json(data, layer_name, geom_field='geom'):
    """Crée une couche mémoire à partir d'un JSON avec détection du CRS."""
    if not data:
        return None

    items = data if isinstance(data, list) else [data]
    if not items or not isinstance(items[0], dict):
        return None

    sample = items[0]
    geom_keys = [geom_field, 'geom', 'geometry']
    geom_key = next((k for k in geom_keys if k in sample), None)

    # --- Détection du CRS ---
    crs = "EPSG:4326"  # fallback

    if geom_key and isinstance(sample.get(geom_key), dict):
        geom_obj = sample[geom_key]
        crs_info = geom_obj.get("crs")
        if crs_info and crs_info.get("type") == "name":
            try:
                crs_name = crs_info["properties"]["name"]
                if "EPSG" in crs_name.upper():
                    code = crs_name.split(":")[-1]
                    crs = f"EPSG:{code}"
            except Exception:
                pass
    elif isinstance(data, dict) and "crs" in data:
        try:
            crs_info = data["crs"]
            if crs_info.get("type") == "name":
                crs_name = crs_info["properties"]["name"]
                if "EPSG" in crs_name.upper():
                    code = crs_name.split(":")[-1]
                    crs = f"EPSG:{code}"
        except Exception:
            pass

    # --- Détection du type géométrique ---
    geom_type = "Point"
    if geom_key and isinstance(sample[geom_key], dict):
        g_type = sample[geom_key].get('type', 'Point')
        if 'Polygon' in g_type:
            geom_type = "Polygon"
        elif 'Line' in g_type:
            geom_type = "LineString"

    uri = f"{geom_type}?crs={crs}"
    layer = QgsVectorLayer(uri, layer_name, "memory")
    pr = layer.dataProvider()

    # --- Champs attributaires ---
    fields = [
        QgsField(k, QVariant.String)
        for k in sample.keys()
        if k not in geom_keys
    ]
    pr.addAttributes(fields)
    layer.updateFields()

    # --- Features ---
    features = []
    for item in items:
        fet = QgsFeature(layer.fields())
        attrs = [
            str(item.get(k, ''))
            for k in sample.keys()
            if k not in geom_keys
        ]
        fet.setAttributes(attrs)

        if geom_key and item.get(geom_key):
            geom_json = json.dumps(item[geom_key])
            geom = QgsJsonUtils.geometryFromGeoJson(geom_json)
            if geom and not geom.isNull():
                fet.setGeometry(geom)
        features.append(fet)

    pr.addFeatures(features)
    layer.updateExtents()
    return layer

def create_vector_layer_from_postgrest(data, layer_name, geom_field='geom', crs="EPSG:4326"):
    """Crée une couche QGIS à partir de données PostgREST avec ST_AsGeoJSON."""
    if not data:
        return None

    items = data if isinstance(data, list) else [data]
    if not items or not isinstance(items[0], dict):
        return None

    sample = items[0]
    geom_key = geom_field if geom_field in sample else 'geom'

    # --- Détection type géométrique ---
    geom_type = "Unknown"
    try:
        first_geom = json.loads(sample[geom_key])
        gtype = first_geom.get("type", "Point")
        if "Polygon" in gtype:
            geom_type = "Polygon"
        elif "Line" in gtype:
            geom_type = "LineString"
        elif "Point" in gtype:
            geom_type = "Point"
    except Exception:
        geom_type = "Point"

    uri = f"{geom_type}?crs={crs}"
    layer = QgsVectorLayer(uri, layer_name, "memory")
    if not layer.isValid():
        return None

    pr = layer.dataProvider()
    fields = [
        QgsField(k, QVariant.String)
        for k in sample.keys()
        if k != geom_key
    ]
    pr.addAttributes(fields)
    layer.updateFields()

    features = []
    for item in items:
        fet = QgsFeature(layer.fields())
        attrs = [str(item.get(k, "")) for k in sample.keys() if k != geom_key]
        fet.setAttributes(attrs)
        try:
            geom = QgsGeometry.fromGeoJson(item[geom_key])
            if geom and not geom.isNull():
                fet.setGeometry(geom)
        except Exception:
            continue
        features.append(fet)

    pr.addFeatures(features)
    layer.updateExtents()
    return layer
