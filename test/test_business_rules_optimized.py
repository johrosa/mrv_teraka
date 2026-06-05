
import unittest
import sys
import os
from unittest.mock import MagicMock

# Setup QGIS environment
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, '/usr/lib/python3/dist-packages')

from qgis.core import QgsExpression, QgsFeature, QgsField, QgsFields, QgsApplication
from qgis.PyQt.QtCore import QVariant

class TestBusinessRulesCaching(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qgs = QgsApplication([], False)
        cls.qgs.initQgis()
        from business_rules import BusinessRulesEngine
        cls.Engine = BusinessRulesEngine

    @classmethod
    def tearDownClass(cls):
        cls.qgs.exitQgis()

    def test_caching_works(self):
        fields = QgsFields()
        fields.append(QgsField('dbh', QVariant.Double))
        fields.append(QgsField('hauteur', QVariant.Double))
        feature = QgsFeature(fields)
        feature.setAttribute('dbh', 10.0)
        feature.setAttribute('hauteur', 10.0)

        # Clear cache
        self.Engine._EXPRESSION_CACHE = {}

        # First call - should populate cache
        self.Engine.validate_feature('arbre_gps', feature)
        self.assertIn('"dbh" > 0', self.Engine._EXPRESSION_CACHE)

        # Store the object reference
        cached_obj = self.Engine._EXPRESSION_CACHE['"dbh" > 0']

        # Second call - should use cache
        self.Engine.validate_feature('arbre_gps', feature)
        self.assertIs(cached_obj, self.Engine._EXPRESSION_CACHE['"dbh" > 0'])

    def test_validation_logic(self):
        fields = QgsFields()
        fields.append(QgsField('dbh', QVariant.Double))
        fields.append(QgsField('hauteur', QVariant.Double))
        feature = QgsFeature(fields)

        # Valid
        feature.setAttribute('dbh', 10.0)
        feature.setAttribute('hauteur', 10.0)
        errors = self.Engine.validate_feature('arbre_gps', feature)
        self.assertEqual(len(errors), 0)

        # Invalid dbh
        feature.setAttribute('dbh', -1.0)
        feature.setAttribute('hauteur', 10.0)
        errors = self.Engine.validate_feature('arbre_gps', feature)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['message'], 'Diamètre positif')

        # Invalid hauteur (warning)
        feature.setAttribute('dbh', 10.0)
        feature.setAttribute('hauteur', 60.0)
        errors = self.Engine.validate_feature('arbre_gps', feature)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['message'], 'Hauteur réaliste')

if __name__ == '__main__':
    unittest.main()
