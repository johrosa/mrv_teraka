# -*- coding: utf-8 -*-
from qgis.core import QgsExpression, QgsExpressionContext, QgsExpressionContextUtils

class BusinessRulesEngine:
    """Moteur de règles métier automatisé pour les tables iTeraka."""

    _EXPRESSION_CACHE = {}

    RULES = {
        'arbre_gps': [
            {'name': 'Diamètre positif', 'expr': '"dbh" > 0', 'severity': 'error'},
            {'name': 'Hauteur réaliste', 'expr': '"hauteur" < 50', 'severity': 'warning'}
        ],
        'communes': [
            {'name': 'Nom présent', 'expr': 'length("nom") > 0', 'severity': 'error'}
        ]
        # On peut étendre pour les 97 tables
    }

    @staticmethod
    def validate_feature(table_name, feature, context=None):
        """Valide une entité QGIS selon les règles métier de sa table."""
        errors = []
        rules = BusinessRulesEngine.RULES.get(table_name, [])

        if context is None:
            context = QgsExpressionContext()
            context.appendScope(QgsExpressionContextUtils.globalScope())

        context.setFeature(feature)

        for rule in rules:
            expr_str = rule['expr']
            cache_key = (table_name, expr_str)
            # Cache the compiled QgsExpression to avoid redundant parsing.
            # We use table_name in key because exp.prepare(context) optimizes based on field indices.
            if cache_key not in BusinessRulesEngine._EXPRESSION_CACHE:
                exp = QgsExpression(expr_str)
                exp.prepare(context)
                BusinessRulesEngine._EXPRESSION_CACHE[cache_key] = exp

            exp = BusinessRulesEngine._EXPRESSION_CACHE[cache_key]

            if not exp.evaluate(context):
                errors.append({
                    'message': rule['name'],
                    'severity': rule['severity']
                })
        return errors
