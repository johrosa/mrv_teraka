# -*- coding: utf-8 -*-
import json
from qgis.core import (
    QgsVectorLayer, QgsField, QgsFeature, QgsJsonUtils, QgsGeometry, NULL
)
from qgis.PyQt.QtCore import QVariant

class LayerFactory:
    @staticmethod
    def  has_geometry_field(data, geom_field='geom'):
        """Détecte rapidement la présence de géométrie sans parsing JSON systématique."""
        if not data: return False
        items = data if isinstance(data, list) else [data]
        if not items or not isinstance(items[0], dict): return False
        sample = items[0]
        
        for key in [geom_field, 'geom', 'geometry']:
            val = sample.get(key)
            if val:
                if isinstance(val, dict) and 'type' in val: return True
                if isinstance(val, str) and val.strip().startswith('{"type"'): return True
        return False

    @staticmethod
    def create_vector_layer_from_json(data, layer_name, geom_field='geom'):
        """Crée une couche mémoire à partir d'un JSON avec détection du CRS."""
        if not data: return None
        items = data if isinstance(data, list) else [data]
        if not items or not isinstance(items[0], dict): return None

        sample = items[0]
        geom_keys = [geom_field, 'geom', 'geometry']
        geom_key = next((k for k in geom_keys if k in sample), None)
        
        # --- Détection du CRS ---
        crs = "EPSG:4326"  # fallback

        # 1. CRS dans la géométrie (priorité haute)
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

        # 2. CRS au niveau global (fallback secondaire)
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
        geom_type = "Point" # Default if no geometry or unknown
        if geom_key and isinstance(sample.get(geom_key), dict):
            g_type = sample[geom_key].get('type', 'Point')
            if 'Polygon' in g_type:
                geom_type = "Polygon"
            elif 'Line' in g_type:
                geom_type = "LineString"
            elif 'Point' in g_type:
                geom_type = "Point"
            elif 'MultiPolygon' in g_type:
                geom_type = "MultiPolygon"
            elif 'MultiLineString' in g_type:
                geom_type = "MultiLineString"
            elif 'MultiPoint' in g_type:
                geom_type = "MultiPoint"

        uri = f"{geom_type}?crs={crs}"

        layer = QgsVectorLayer(uri, layer_name, "memory")
        pr = layer.dataProvider()

        # --- Type Inference for Fields ---
        fields = []
        for k, v in sample.items():
            if k in geom_keys:
                continue
            
            field_type = QVariant.String
            if isinstance(v, bool):
                field_type = QVariant.Bool
            elif isinstance(v, int):
                field_type = QVariant.Int
            elif isinstance(v, float):
                field_type = QVariant.Double
            elif isinstance(v, dict) or isinstance(v, list):
                field_type = QVariant.String # JSON string fallback
                
            fields.append(QgsField(k, field_type))

        pr.addAttributes(fields)
        layer.updateFields()

        # --- Features ---
        features = []
        for item in items:
            fet = QgsFeature(layer.fields())

            attrs = []
            for k in sample.keys():
                if k in geom_keys: continue
                val = item.get(k)
                attrs.append(val if val is not None else NULL)
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

    @staticmethod
    def create_table_layer_from_json(data, layer_name):
        """Crée une couche table (sans géométrie) à partir d'un JSON."""
        if not data:
            return None

        items = data if isinstance(data, list) else [data]
        if not items or not isinstance(items[0], dict):
            return None

        sample = items[0]

        # URI pour une couche sans géométrie ("?" = aucune géométrie)
        uri = "?"
        layer = QgsVectorLayer(uri, layer_name, "memory")
        
        if not layer.isValid():
            return None

        pr = layer.dataProvider()

        # --- Tous les champs sont des attributs (pas de géométrie à exclure) ---
        fields = []
        for k, v in sample.items():
            field_type = QVariant.String
            if isinstance(v, bool):
                field_type = QVariant.Bool
            elif isinstance(v, int):
                field_type = QVariant.Int
            elif isinstance(v, float):
                field_type = QVariant.Double
            elif isinstance(v, dict) or isinstance(v, list):
                field_type = QVariant.String # JSON string fallback
            fields.append(QgsField(k, field_type))

        pr.addAttributes(fields)
        layer.updateFields()

        # --- Features sans géométrie ---
        features = []
        for item in items:
            fet = QgsFeature(layer.fields())

            attrs = []
            for k in sample.keys():
                val = item.get(k)
                attrs.append(val if val is not None else NULL)
            
            fet.setAttributes(attrs)

            features.append(fet)

        pr.addFeatures(features)
        layer.updateExtents()

        return layer

    @staticmethod
    def create_vector_layer_from_geojson(data, layer_name):
        """Crée une couche mémoire QGIS à partir d'un GeoJSON Feature ou FeatureCollection."""
        if not data:
            return None

        features_list = []
        if isinstance(data, dict):
            if data.get('type') == 'FeatureCollection':
                features_list = data.get('features', [])
            elif data.get('type') == 'Feature':
                features_list = [data]
            else:
                return None
        elif isinstance(data, list):
            # Assume it's a list of GeoJSON Features
            features_list = data
        else:
            return None

        if not features_list:
            # Create a valid empty layer for an empty FeatureCollection.
            geom_type = 'Point' # Default to Point for empty GeoJSON
            crs = "EPSG:4326"
            uri = f"{geom_type}?crs={crs}"
            layer = QgsVectorLayer(uri, layer_name, "memory")
            if not layer.isValid():
                return None
            pr = layer.dataProvider()
            pr.addAttributes([])
            layer.updateFields()
            return layer

        first_feature = features_list[0]
        if not isinstance(first_feature, dict) or first_feature.get('type') != 'Feature':
            return None

        # Determine geometry type from the first feature
        geom = first_feature.get('geometry', {})
        gtype = geom.get('type', 'Point') if isinstance(geom, dict) else 'Point'
        
        geom_type = 'Point'
        if 'MultiPolygon' in gtype:
            geom_type = 'MultiPolygon'
        elif 'Polygon' in gtype:
            geom_type = 'Polygon'
        elif 'MultiLineString' in gtype:
            geom_type = 'MultiLineString'
        elif 'LineString' in gtype:
            geom_type = 'LineString'
        elif 'MultiPoint' in gtype:
            geom_type = 'MultiPoint'
        elif 'Point' in gtype:
            geom_type = 'Point'
        elif 'GeometryCollection' in gtype:
            # For GeometryCollection, we might need to be more generic or pick a common type
            # For simplicity, let's default to Point or handle it more robustly if needed
            geom_type = 'Point' # Or handle more complex logic

        # Determine CRS from the GeoJSON (if present)
        crs = "EPSG:4326" # Default CRS
        if isinstance(data, dict) and "crs" in data:
            try:
                crs_info = data["crs"]
                if crs_info.get("type") == "name":
                    crs_name = crs_info["properties"]["name"]
                    if "EPSG" in crs_name.upper():
                        code = crs_name.split(":")[-1]
                        crs = f"EPSG:{code}"
            except Exception:
                pass
        elif isinstance(first_feature, dict) and "crs" in first_feature.get('geometry', {}):
             try:
                crs_info = first_feature['geometry']["crs"]
                if crs_info.get("type") == "name":
                    crs_name = crs_info["properties"]["name"]
                    if "EPSG" in crs_name.upper():
                        code = crs_name.split(":")[-1]
                        crs = f"EPSG:{code}"
             except Exception:
                pass

        uri = f"{geom_type}?crs={crs}"
        layer = QgsVectorLayer(uri, layer_name, "memory")
        if not layer.isValid():
            return None

        pr = layer.dataProvider()

        # Collect all unique property keys to define fields
        field_names = set()
        for feature in features_list:
            props = feature.get('properties', {})
            if isinstance(props, dict):
                field_names.update(props.keys())

        # Infer field types from the first feature's properties
        fields = []
        if features_list:
            first_props = features_list[0].get('properties', {})
            for k in sorted(field_names):
                v = first_props.get(k)
                field_type = QVariant.String
                if isinstance(v, bool):
                    field_type = QVariant.Bool
                elif isinstance(v, int):
                    field_type = QVariant.Int
                elif isinstance(v, float):
                    field_type = QVariant.Double
                fields.append(QgsField(k, field_type))
        
        pr.addAttributes(fields)
        layer.updateFields()

        layer_features = []
        for feature in features_list:
            props = feature.get('properties', {})
            if not isinstance(props, dict):
                props = {}

            fet = QgsFeature(layer.fields())
            
            # Populate attributes, converting to string for now
            attr_values = []
            for k in sorted(field_names):
                value = props.get(k, '')
                if isinstance(value, (dict, list)): # Handle nested JSON in properties
                    attr_values.append(json.dumps(value))
                else:
                    attr_values.append(str(value))

            fet.setAttributes(attr_values)

            geometry = feature.get('geometry')
            if geometry:
                geom_json = json.dumps(geometry)
                geom_obj = QgsJsonUtils.geometryFromGeoJson(geom_json)
                if geom_obj and not geom_obj.isNull():
                    fet.setGeometry(geom_obj)

            layer_features.append(fet)

        pr.addFeatures(layer_features)
        layer.updateExtents()
        return layer