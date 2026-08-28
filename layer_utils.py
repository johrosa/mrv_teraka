# -*- coding: utf-8 -*-
"""
Utilitaires pour la gestion des couches QGIS et conversion JSON/GeoJSON.
"""

import json
import os
import tempfile
from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    QgsVectorLayer, QgsField, QgsFeature,
    QgsGeometry, QgsCoordinateReferenceSystem, QgsJsonUtils,
    QgsVectorFileWriter, QgsProject
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

    is_spatial = False
    if actual_geom_key:
        geom_val = _extract_geometry(sample.get(actual_geom_key))
        if geom_val:
            crs = _detect_crs(geom_val, default_crs)
            geom_type = _detect_geom_type(geom_val)
            is_spatial = True

    if is_spatial:
        uri = f"{geom_type}?crs={crs}"
    else:
        uri = "NoGeometry"
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

def _qgis_value_to_python(value):
    """Convertit les valeurs QGIS nulles en None pour pandas/OGR."""
    if value is None:
        return None
    if hasattr(value, "isNull") and value.isNull():
        return None
    return value

def _ogr_safe_value(value):
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return value

def _shapely_from_wkb(wkb):
    try:
        from shapely import from_wkb
        return from_wkb(wkb)
    except ImportError:
        from shapely.wkb import loads
        return loads(wkb)

def _shapely_from_geojson(geom_obj):
    from shapely.geometry import shape
    return shape(geom_obj)

def _layer_to_pyogrio_dataframe(layer):
    import geopandas as gpd
    import pandas as pd

    fields = layer.fields()
    field_names = [field.name() for field in fields]
    rows = []
    geometries = []
    is_spatial = layer.isSpatial()

    for feature in layer.getFeatures():
        attrs = feature.attributes()
        rows.append({
            name: _qgis_value_to_python(attrs[index])
            for index, name in enumerate(field_names)
        })

        if is_spatial:
            geometry = None
            if feature.hasGeometry():
                qgis_geometry = feature.geometry()
                if qgis_geometry and not qgis_geometry.isNull():
                    geometry = _shapely_from_wkb(bytes(qgis_geometry.asWkb()))
            geometries.append(geometry)

    if is_spatial:
        crs = layer.crs().authid() if layer.crs().isValid() else None
        return gpd.GeoDataFrame(rows, geometry=geometries, crs=crs)

    return pd.DataFrame(rows, columns=field_names)

def _rows_to_pyogrio_dataframe(data, geom_field='geom', default_crs='EPSG:4326'):
    import geopandas as gpd
    import pandas as pd

    items = data if isinstance(data, list) else [data]
    if not items or not isinstance(items[0], dict):
        return None

    sample = items[0]
    geom_keys = [geom_field, 'geom', 'geometry', 'the_geom']
    actual_geom_key = next((k for k in geom_keys if k and k in sample), None)
    attribute_keys = [k for k in sample.keys() if k != actual_geom_key]

    rows = []
    geometries = []
    is_spatial = False
    crs = default_crs

    for item in items:
        rows.append({
            key: _ogr_safe_value(item.get(key))
            for key in attribute_keys
        })

        if actual_geom_key:
            geom_obj = _extract_geometry(item.get(actual_geom_key))
            if geom_obj:
                is_spatial = True
                crs = _detect_crs(geom_obj, default_crs)
                geometries.append(_shapely_from_geojson(geom_obj))
            else:
                geometries.append(None)

    if is_spatial:
        return gpd.GeoDataFrame(rows, geometry=geometries, crs=crs)

    return pd.DataFrame(rows, columns=attribute_keys)

def _geojson_to_pyogrio_dataframe(data, default_crs='EPSG:4326'):
    import geopandas as gpd

    features = data.get('features', [data]) if data.get('type') == 'FeatureCollection' else [data]
    rows = []
    geometries = []
    crs = _detect_crs(data, default_crs)

    for feature in features:
        if not isinstance(feature, dict):
            continue
        properties = feature.get('properties') or {}
        rows.append({
            key: _ogr_safe_value(value)
            for key, value in properties.items()
        })
        geom_obj = feature.get('geometry')
        geometries.append(_shapely_from_geojson(geom_obj) if geom_obj else None)

    return gpd.GeoDataFrame(rows, geometry=geometries, crs=crs)

def _export_to_geopackage_pyogrio(layers_map, output_path, continue_on_error=False):
    import pyogrio

    expected_layers = set(layers_map.keys())
    if os.path.exists(output_path):
        os.remove(output_path)

    errors = []
    for name, layer in layers_map.items():
        try:
            dataframe = _layer_to_pyogrio_dataframe(layer)
            pyogrio.write_dataframe(
                dataframe,
                output_path,
                layer=name,
                driver="GPKG",
                encoding="UTF-8",
                use_arrow=True
            )
        except Exception as exc:
            errors.append("{}: {}".format(name, exc))
            if not continue_on_error:
                return False, str(exc)

    if os.path.exists(output_path) and expected_layers:
        written_layers = set(str(row[0]) for row in pyogrio.list_layers(output_path))
        missing_layers = expected_layers - written_layers
        if missing_layers and not continue_on_error:
            return False, "Couches absentes du GeoPackage pyogrio: {}".format(
                ", ".join(sorted(missing_layers))
            )
        if missing_layers:
            errors.extend("{}: couche absente après écriture pyogrio".format(name) for name in missing_layers)

    if errors:
        detail = "; ".join(errors[:5])
        if len(errors) > 5:
            detail += "; ... {} autre(s)".format(len(errors) - 5)
        return False, detail

    return True, "Export GeoPackage réussi avec pyogrio"

def create_vector_layer_fast(data, layer_name, geom_field='geom', default_crs='EPSG:4326'):
    """
    Crée une couche QGIS via un GeoPackage temporaire écrit par pyogrio.

    Retourne None si les dépendances rapides ne sont pas disponibles ou si
    l'écriture échoue, afin de permettre un fallback vers create_vector_layer.
    """
    if not data:
        return None

    try:
        import pyogrio
    except ImportError:
        return None

    temp_path = None
    try:
        if is_geojson(data):
            dataframe = _geojson_to_pyogrio_dataframe(data, default_crs=default_crs)
        else:
            dataframe = _rows_to_pyogrio_dataframe(data, geom_field=geom_field, default_crs=default_crs)

        if dataframe is None:
            return None

        fd, temp_path = tempfile.mkstemp(suffix='.gpkg')
        os.close(fd)
        if os.path.exists(temp_path):
            os.remove(temp_path)

        pyogrio.write_dataframe(
            dataframe,
            temp_path,
            layer=layer_name,
            driver="GPKG",
            encoding="UTF-8",
            use_arrow=True
        )

        layer = QgsVectorLayer("{}|layername={}".format(temp_path, layer_name), layer_name, "ogr")
        if not layer.isValid():
            os.unlink(temp_path)
            return None

        layer.setCustomProperty('mrv:temp_gpkg_path', temp_path)
        return layer
    except Exception:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass
        return None

def _export_to_geopackage_qgis(layers_map, output_path, continue_on_error=False):
    """
    Exporte une collection de couches vers un GeoPackage via le writer QGIS.
    """
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"

    first = True
    errors = []
    for name, layer in layers_map.items():
        options.layerName = name
        if first:
            options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
        else:
            options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer

        # Robust export: try V3 first (QGIS 3.10+), fallback to V2
        if hasattr(QgsVectorFileWriter, 'writeAsVectorFormatV3'):
            res = QgsVectorFileWriter.writeAsVectorFormatV3(
                layer,
                output_path,
                QgsProject.instance().transformContext(),
                options
            )
            error = res[0]
            error_msg = res[1] if len(res) > 1 else "Erreur inconnue"
        else:
            # Fallback for older QGIS 3.x
            error = QgsVectorFileWriter.writeAsVectorFormat(
                layer,
                output_path,
                "UTF-8",
                layer.crs(),
                "GPKG",
                False,
                None,
                options.layerName,
                options.actionOnExistingFile
            )
            error_msg = "Erreur lors de l'export GeoPackage (V2)"

        if error == QgsVectorFileWriter.NoError:
            first = False
            continue

        errors.append("{}: {}".format(name, error_msg))
        if not continue_on_error:
            return False, error_msg

    if errors:
        detail = "; ".join(errors[:5])
        if len(errors) > 5:
            detail += "; ... {} autre(s)".format(len(errors) - 5)
        return False, detail

    return True, "Export réussi"

def export_to_geopackage(layers_map, output_path, continue_on_error=False):
    """
    Exporte une collection de couches vers un GeoPackage.

    Args:
        layers_map: Dict {layer_name: QgsVectorLayer}
        output_path: Chemin du fichier .gpkg
    """
    try:
        success, message = _export_to_geopackage_pyogrio(
            layers_map,
            output_path,
            continue_on_error=continue_on_error
        )
        if success:
            return success, message
    except ImportError:
        pass
    except Exception:
        pass

    return _export_to_geopackage_qgis(
        layers_map,
        output_path,
        continue_on_error=continue_on_error
    )
