# -*- coding: utf-8 -*-
"""
Utilitaires pour la gestion des couches QGIS et conversion JSON/GeoJSON.
"""

import json
from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    QgsVectorLayer, QgsField, QgsFeature,
    QgsGeometry, QgsCoordinateReferenceSystem, QgsJsonUtils
)

def is_geojson(data):
    """
    Vérifie si les données sont au format GeoJSON (Feature ou FeatureCollection).

    Args:
        data: Données à vérifier.

    Returns:
        bool: True si c'est du GeoJSON.
    """
    return isinstance(data, dict) and data.get('type') in ['FeatureCollection', 'Feature']

def _extract_geometry(value):
    """Extrait un objet géométrie d'une valeur (dict ou string JSON)."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return None
    return None

def _detect_crs(geom_obj, fallback_crs="EPSG:4326"):
    """
    Détecte le CRS à partir d'un objet géométrie ou utilise un fallback.

    Args:
        geom_obj: Objet géométrie (dict).
        fallback_crs: CRS à utiliser si non détecté.

    Returns:
        str: Chaîne de définition du CRS (ex: 'EPSG:4326').
    """
    if not isinstance(geom_obj, dict):
        return fallback_crs

    # Recherche dans l'objet géométrie (format PostGIS GeoJSON)
    crs_info = geom_obj.get("crs")
    if crs_info and crs_info.get("type") == "name":
        try:
            crs_name = crs_info["properties"]["name"]
            if "EPSG" in crs_name.upper():
                code = crs_name.split(":")[-1]
                return f"EPSG:{code}"
        except Exception:
            pass

    # Validation via QgsCoordinateReferenceSystem si possible (serait mieux mais on reste simple ici)
    return fallback_crs

def _detect_geom_type(geom_obj):
    """Détecte le type de géométrie QGIS à partir d'un objet GeoJSON."""
    if not isinstance(geom_obj, dict):
        return "Point"

    g_type = geom_obj.get('type', 'Point')
    if 'Polygon' in g_type:
        return "Polygon"
    if 'Line' in g_type:
        return "LineString"
    return "Point"

def create_vector_layer(data, layer_name, geom_field='geom', default_crs='EPSG:4326'):
    """
    Crée une couche mémoire QGIS à partir d'une liste de dictionnaires.

    Args:
        data: Liste de dictionnaires contenant les données.
        layer_name: Nom de la couche à créer.
        geom_field: Nom du champ contenant la géométrie.
        default_crs: CRS par défaut si non détecté.

    Returns:
        QgsVectorLayer: La couche créée ou None en cas d'erreur.
    """
    if not data:
        return None

    items = data if isinstance(data, list) else [data]
    if not items or not isinstance(items[0], dict):
        return None

    sample = items[0]
    geom_keys = [geom_field, 'geom', 'geometry']
    actual_geom_key = next((k for k in geom_keys if k in sample), None)

    # --- Analyse du premier élément pour configuration ---
    crs = default_crs
    geom_type = "Point"

    if actual_geom_key:
        geom_val = _extract_geometry(sample.get(actual_geom_key))
        if geom_val:
            crs = _detect_crs(geom_val, default_crs)
            geom_type = _detect_geom_type(geom_val)

    uri = f"{geom_type}?crs={crs}"
    layer = QgsVectorLayer(uri, layer_name, "memory")
    if not layer.isValid():
        return None

    pr = layer.dataProvider()

    # --- Configuration des champs ---
    # On exclut le champ géométrie des attributs
    attribute_keys = [k for k in sample.keys() if k != actual_geom_key]
    fields = [QgsField(k, QVariant.String) for k in attribute_keys]
    pr.addAttributes(fields)
    layer.updateFields()

    # --- Création des entités ---
    features = []
    for item in items:
        fet = QgsFeature(layer.fields())

        # Attributs
        attrs = [str(item.get(k, '')) for k in attribute_keys]
        fet.setAttributes(attrs)

        # Géométrie
        if actual_geom_key:
            geom_obj = _extract_geometry(item.get(actual_geom_key))
            if geom_obj:
                try:
                    # QGIS 3.x >= 3.10 has QgsGeometry.fromGeoJson
                    # But some versions might differ or we use OGR as backup
                    geom = QgsGeometry.fromGeoJson(json.dumps(geom_obj))
                except AttributeError:
                    # Fallback OGR/WKT for very specific environments
                    from osgeo import ogr
                    ogr_geom = ogr.CreateGeometryFromJson(json.dumps(geom_obj))
                    if ogr_geom:
                        geom = QgsGeometry.fromWkt(ogr_geom.ExportToWkt())
                    else:
                        geom = None

                if geom and not geom.isNull():
                    fet.setGeometry(geom)

        features.append(fet)

    pr.addFeatures(features)
    layer.updateExtents()
    return layer

def layer_to_list_of_dicts(layer, geom_field='geom'):
    """
    Convertit une couche QGIS en liste de dictionnaires pour insertion API.

    Args:
        layer: QgsVectorLayer source.
        geom_field: Nom du champ de géométrie attendu par le backend.

    Returns:
        list: Liste de dictionnaires (attributs + géométrie GeoJSON).
    """
    data_list = []
    for feature in layer.getFeatures():
        # Export des attributs en JSON
        attrs_json = QgsJsonUtils.exportAttributes(feature)
        item = json.loads(attrs_json)

        # Ajout de la géométrie si elle existe
        if layer.isSpatial() and feature.hasGeometry():
            geom = feature.geometry()
            if not geom.isNull():
                item[geom_field] = json.loads(geom.asJson())

        data_list.append(item)
    return data_list
