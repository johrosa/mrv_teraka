# -*- coding: utf-8 -*-
import unittest
import sys
import os
from qgis.core import QgsApplication, QgsFeature, QgsField, QgsFields, QgsExpressionContext, QgsExpressionContextUtils
from qgis.PyQt.QtCore import QVariant

# Ensure current directory is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_rules import BusinessRulesEngine

class TestBusinessRulesOptimization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qgs = QgsApplication([], False)
        cls.qgs.initQgis()

    @classmethod
    def tearDownClass(cls):
        cls.qgs.exitQgis()

    def test_validation_logic_still_works(self):
        # Setup fields
        fields = QgsFields()
        fields.append(QgsField("dbh", QVariant.Double))
        fields.append(QgsField("hauteur", QVariant.Double))

        # Test Case 1: Valid feature
        feature_valid = QgsFeature(fields)
        feature_valid.setAttribute("dbh", 10.5)
        feature_valid.setAttribute("hauteur", 15.0)

        errors = BusinessRulesEngine.validate_feature('arbre_gps', feature_valid)
        self.assertEqual(len(errors), 0, "Valid feature should have no errors")

        # Test Case 2: Invalid feature (dbh <= 0)
        feature_invalid = QgsFeature(fields)
        feature_invalid.setAttribute("dbh", -1.0)
        feature_invalid.setAttribute("hauteur", 15.0)

        errors = BusinessRulesEngine.validate_feature('arbre_gps', feature_invalid)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['message'], 'Diamètre positif')

        # Test Case 3: Warning feature (hauteur >= 50)
        feature_warning = QgsFeature(fields)
        feature_warning.setAttribute("dbh", 10.5)
        feature_warning.setAttribute("hauteur", 60.0)

        errors = BusinessRulesEngine.validate_feature('arbre_gps', feature_warning)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['message'], 'Hauteur réaliste')
        self.assertEqual(errors[0]['severity'], 'warning')

    def test_context_reuse_works(self):
        fields = QgsFields()
        fields.append(QgsField("dbh", QVariant.Double))
        fields.append(QgsField("hauteur", QVariant.Double))

        feature = QgsFeature(fields)
        feature.setAttribute("dbh", -5.0)
        feature.setAttribute("hauteur", 10.0)

        context = QgsExpressionContext()
        context.appendScope(QgsExpressionContextUtils.globalScope())

        # Validate with explicit context
        errors = BusinessRulesEngine.validate_feature('arbre_gps', feature, context=context)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['message'], 'Diamètre positif')

        # Verify cache was populated
        self.assertIn(('arbre_gps', '"dbh" > 0'), BusinessRulesEngine._EXPRESSION_CACHE)

    def test_cross_table_isolation(self):
        # Setup table A
        fields_a = QgsFields()
        fields_a.append(QgsField("val", QVariant.Double)) # val is index 0
        feature_a = QgsFeature(fields_a)
        feature_a.setAttribute("val", 10.0)

        # Setup table B
        fields_b = QgsFields()
        fields_b.append(QgsField("other", QVariant.String))
        fields_b.append(QgsField("val", QVariant.Double)) # val is index 1
        feature_b = QgsFeature(fields_b)
        feature_b.setAttribute("val", 10.0)

        expr = '"val" > 5'
        # Define rule for both tables
        BusinessRulesEngine.RULES['table_a'] = [{'name': 'Rule A', 'expr': expr, 'severity': 'error'}]
        BusinessRulesEngine.RULES['table_b'] = [{'name': 'Rule B', 'expr': expr, 'severity': 'error'}]

        # Validate table A
        errors_a = BusinessRulesEngine.validate_feature('table_a', feature_a)
        self.assertEqual(len(errors_a), 0)

        # Validate table B
        errors_b = BusinessRulesEngine.validate_feature('table_b', feature_b)
        self.assertEqual(len(errors_b), 0)

        # Verify both are cached separately
        self.assertIn(('table_a', expr), BusinessRulesEngine._EXPRESSION_CACHE)
        self.assertIn(('table_b', expr), BusinessRulesEngine._EXPRESSION_CACHE)
        # Note: QgsExpression implements equality based on the expression string,
        # but they are separate objects in memory when cached under different keys.
        self.assertTrue(
            BusinessRulesEngine._EXPRESSION_CACHE[('table_a', expr)] is not
            BusinessRulesEngine._EXPRESSION_CACHE[('table_b', expr)]
        )

if __name__ == '__main__':
    unittest.main()
