# -*- coding: utf-8 -*-
"""
Moteur de règles métier pour le plugin MrvTeraka.
"""
from qgis.core import (
    QgsExpression,
    QgsExpressionContext,
    QgsExpressionContextUtils
)

class BusinessRulesEngine:
    """Moteur de règles métier automatisé pour les tables iTeraka."""

    # Cache pour les expressions compilées afin d'améliorer les performances
    # lors de validations massives.
    _EXPRESSION_CACHE = {}

    RULES = {
        'arbre_gps': [
            {'name': 'Diamètre positif', 'expr': '"dbh" > 0',
             'severity': 'error'},
            {'name': 'Hauteur réaliste', 'expr': '"hauteur" < 50',
             'severity': 'warning'}
        ],
        'communes': [
            {'name': 'Nom présent', 'expr': 'length("nom") > 0',
             'severity': 'error'}
        ]
        # On peut étendre pour les 97 tables
    }

    @staticmethod
    def validate_feature(table_name, feature):
        """Valide une entité QGIS selon les règles métier de sa table."""
        errors = []
        rules = BusinessRulesEngine.RULES.get(table_name, [])

        context = QgsExpressionContext()
        context.appendScope(QgsExpressionContextUtils.globalScope())
        context.setFeature(feature)

        for rule in rules:
            expr_string = rule['expr']

            # Utilisation du cache pour éviter de recompiler l'expression
            # Performance: La compilation d'une QgsExpression est coûteuse
            # dans une boucle sur des milliers d'entités.
            if expr_string not in BusinessRulesEngine._EXPRESSION_CACHE:
                BusinessRulesEngine._EXPRESSION_CACHE[expr_string] = \
                    QgsExpression(expr_string)

            exp = BusinessRulesEngine._EXPRESSION_CACHE[expr_string]

            if not exp.evaluate(context):
                errors.append({
                    'message': rule['name'],
                    'severity': rule['severity']
                })
        return errors
