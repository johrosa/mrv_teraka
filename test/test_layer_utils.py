# -*- coding: utf-8 -*-
import unittest
import sys
import os

# Ajouter le parent au path pour pouvoir importer layer_utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from layer_utils import is_geojson

class TestLayerUtils(unittest.TestCase):
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

if __name__ == '__main__':
    unittest.main()
