# -*- coding: utf-8 -*-
import unittest
import sys
import os

# Ajouter le parent au path pour pouvoir importer layer_utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from layer_utils import is_geojson, create_vector_layer
from qgis.core import QgsApplication, QgsVectorLayer

class TestLayerUtils(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialisation de QGIS pour les tests
        cls.qgs = QgsApplication([], False)
        cls.qgs.initQgis()

    @classmethod
    def tearDownClass(cls):
        cls.qgs.exitQgis()

    def test_is_geojson(self):
        # Cas positif: FeatureCollection
        data = {'type': 'FeatureCollection', 'features': []}
        self.assertTrue(is_geojson(data))

        # Cas positif: Feature
        data = {'type': 'Feature', 'geometry': None, 'properties': {}}
        self.assertTrue(is_geojson(data))

        # Cas négatif: Liste
        data = []
        self.assertFalse(is_geojson(data))

        # Cas négatif: Dict sans type correct
        data = {'type': 'Point', 'coordinates': [0, 0]}
        self.assertFalse(is_geojson(data))

        # Cas négatif: None
        self.assertFalse(is_geojson(None))

    def test_create_vector_layer(self):
        data = [
            {'id': 1, 'name': 'Point A', 'geom': '{"type": "Point", "coordinates": [47.5, -18.9]}'},
            {'id': 2, 'name': 'Point B', 'geom': '{"type": "Point", "coordinates": [47.6, -19.0]}'}
        ]
        layer = create_vector_layer(data, "Test Layer", geom_field='geom')

        self.assertIsNotNone(layer)
        self.assertTrue(layer.isValid())
        self.assertEqual(layer.name(), "Test Layer")
        self.assertEqual(layer.featureCount(), 2)

        # Vérifier les champs
        fields = layer.fields()
        self.assertIn('id', [f.name() for f in fields])
        self.assertIn('name', [f.name() for f in fields])
        self.assertNotIn('geom', [f.name() for f in fields])

if __name__ == '__main__':
    unittest.main()
