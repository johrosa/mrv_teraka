# -*- coding: utf-8 -*-
from datetime import datetime
from uuid import UUID

from qgis.core import QgsExpression, QgsExpressionContext, QgsExpressionContextUtils

class BusinessRulesEngine:
    """Moteur de règles métier automatisé pour les tables iTeraka."""

    # Cache for compiled QgsExpression objects to avoid redundant parsing.
    # Key is (table_name, expr_str) because preparation is specific to table fields.
    _EXPRESSION_CACHE = {}

    # Contraintes applicatives calées sur les colonnes non-null les plus
    # structurantes de la base. Les champs techniques remplis automatiquement
    # au moment de la validation/publication restent optionnels ici.
    REQUIRED_FIELDS = {
        'arbre_gps': {
            'operateur_id', 'c_com', 'uuid_arbre_gps', 'uuid_bosquet_gps',
            'geom', 'numero_arbre', 'statut_arbre'
        },
        'bosquet_gps': {
            'uuid_bosquet_gps', 'uuid_membre', 'uuid_pg', 'c_com',
            'num_bosquet', 'code_bosquet', 'statut_bosquet',
            'date_statut', 'date_creation', 'geom'
        },
        'membre': {
            'uuid_membre', 'c_com', 'date_saisie', 'uuid_pg', 'code_pg',
            'nom_pg', 'statut_membre', 'date_statut', 'nom_membre',
            'genre', 'annee_inscription', 'pepinieriste', 'leader',
            'agent_cluster', 'quantificateur', 'deforestation',
            'zone_riparienne', 'arbres_sup_10pct'
        },
        'membre_suivi': {
            'uuid_membre_suivi', 'operateur_id', 'c_com', 'uuid_membre',
            'date_suivi', 'annee', 'revenu_annuel_estime', 'revenu_teraka',
            'frequence_penurie_alimentaire', 'qualite_recolte',
            'pratiques_csa', 'foyers_ameliore',
            'pratique_agroforesterie', 'nouvelle_pratique_agroforesterie',
            'ressent_bienfaits_agroforesterie', 'difficulte_programme',
            'difficulte_commentaire', 'risque_erosion_inondation',
            'bien_etre_general'
        },
        'pg_gps': {'uuid_pg_gps', 'geom', 'c_com'},
        'pg_infos': {
            'uuid_pg', 'date_saisie', 'c_com', 'code_pg', 'nom_pg',
            'date_inscription', 'annee_inscription', 'statut_pg'
        },
    }

    FK_TABLES = {
        'c_com': 'communes',
        'uuid_pg': 'pg_infos',
        'uuid_pg_gps': 'pg_gps',
        'uuid_membre': 'membre',
        'uuid_membre_suivi': 'membre_suivi',
        'uuid_bosquet_gps': 'bosquet_gps',
        'uuid_arbre_gps': 'arbre_gps',
        'uuid_pg_membre_event': 'pg_membre_evenement',
        'uuid_membre_event': 'pg_membre_evenement',
        'uuid_pg_suivi': 'pg_suivi',
        'uuid_pg_suivi_admin': 'pg_suivi_admin',
        'uuid_bosquet_evenement_doc': 'bosquet_evenement_document',
        'uuid_bosquet_evenement': 'bosquet_evenement',
        'uuid_membre_source': 'membre',
        'uuid_membre_cible': 'membre',
        'uuid_nouveau_membre': 'pg_nouveau_membre',
    }

    UUID_COLUMNS_WITH_TEXT_EXCEPTIONS = set()
    INTEGER_COLUMNS = {'id', 'c_com', 'annee', 'annee_inscription', 'annee_naissance'}
    BOOLEAN_COLUMNS = {
        'pepinieriste', 'leader', 'agent_cluster', 'quantificateur',
        'deforestation', 'zone_riparienne', 'arbres_sup_10pct',
        'pratiques_csa', 'foyers_ameliore', 'pratique_agroforesterie',
        'nouvelle_pratique_agroforesterie', 'ressent_bienfaits_agroforesterie',
        'difficulte_programme', 'echantillon', 'multitiges'
    }

    RULES = {
        'arbre_gps': [
            {'name': 'Diamètre positif', 'expr': '"dbh" > 0', 'severity': 'error'},
            {'name': 'Hauteur réaliste', 'expr': '"hauteur" < 50', 'severity': 'warning'},
            {'name': 'Espèce renseignée', 'expr': 'length("espece") > 0', 'severity': 'error'}
        ],
        'bosquet_gps': [
            {'name': 'Nom bosquet présent', 'expr': 'length("nom") > 0', 'severity': 'error'},
            {'name': 'C_COM valide', 'expr': 'length("c_com") > 0', 'severity': 'error'}
        ],
        'communes': [
            {'name': 'Nom présent', 'expr': 'length("nom") > 0', 'severity': 'error'},
            {'name': 'Code commune valide', 'expr': '"c_com" >= 100000', 'severity': 'warning'}
        ],
        'pg_gps': [
            {'name': 'Code PG présent', 'expr': 'length("code_pg") > 0', 'severity': 'error'},
            {'name': 'Commune valide', 'expr': 'length("c_com") > 0', 'severity': 'error'}
        ],
        'membre': [
            {'name': 'ID membre présent', 'expr': 'length("uuid_membre") > 0', 'severity': 'error'},
            {'name': 'Nom membre présent', 'expr': 'length("nom") > 0', 'severity': 'error'}
        ],
        'parcelle': [
            {'name': 'Surface positive', 'expr': '"surface" > 0', 'severity': 'error'},
            {'name': 'Propriétaire renseigné', 'expr': 'length("proprio") > 0', 'severity': 'warning'}
        ]
        # On peut étendre pour les 97 tables
    }

    @staticmethod
    def _error(message, severity='error'):
        return {'message': message, 'severity': severity}

    @staticmethod
    def _is_empty(value):
        if value is None:
            return True
        if isinstance(value, str):
            return value.strip() == '' or value.strip().lower() in {'null', 'none', 'nan'}
        return False

    @staticmethod
    def _to_text(value):
        return '' if value is None else str(value).strip()

    @staticmethod
    def _is_uuid(value):
        try:
            UUID(str(value).strip())
            return True
        except Exception:
            return False

    @staticmethod
    def _is_int(value):
        if isinstance(value, bool):
            return False
        try:
            return str(int(float(str(value).strip()))) == str(value).strip() or float(str(value).strip()).is_integer()
        except Exception:
            return False

    @staticmethod
    def _is_date(value):
        if hasattr(value, 'toPyDateTime'):
            return True
        if isinstance(value, datetime):
            return True
        text = BusinessRulesEngine._to_text(value)
        if text.endswith('Z'):
            text = text[:-1] + '+00:00'
        try:
            datetime.fromisoformat(text)
            return True
        except Exception:
            return False

    @staticmethod
    def _is_bool(value):
        if isinstance(value, bool):
            return True
        text = BusinessRulesEngine._to_text(value).lower()
        return text in {'true', 'false', '1', '0', 'yes', 'no', 'oui', 'non'}

    @staticmethod
    def _primary_uuid_field(table_name, row):
        candidate = f"uuid_{table_name}"
        if candidate in row:
            return candidate
        if table_name.endswith('s') and f"uuid_{table_name[:-1]}" in row:
            return f"uuid_{table_name[:-1]}"
        return None

    @staticmethod
    def _feature_to_dict(feature):
        fields = feature.fields()
        row = {}
        for idx in range(fields.count()):
            row[fields.at(idx).name()] = feature.attribute(idx)
        return row

    @staticmethod
    def _field_values(rows, field_name):
        values = set()
        for row in rows or []:
            value = row.get(field_name)
            if not BusinessRulesEngine._is_empty(value):
                values.add(BusinessRulesEngine._to_text(value).lower())
        return values

    @staticmethod
    def build_reference_index(collected_data=None, original_data=None):
        """Indexe les valeurs disponibles par table/champ pour verifier les FK."""
        index = {}
        for dataset in (original_data or {}, collected_data or {}):
            if not isinstance(dataset, dict):
                continue
            for table_name, rows in dataset.items():
                table_index = index.setdefault(table_name, {})
                if not isinstance(rows, list):
                    continue
                field_names = set()
                for row in rows:
                    if isinstance(row, dict):
                        field_names.update(row.keys())
                for field_name in field_names:
                    if field_name == 'c_com' or field_name.startswith('uuid_'):
                        table_index.setdefault(field_name, set()).update(
                            BusinessRulesEngine._field_values(rows, field_name)
                        )
        return index

    @staticmethod
    def _reference_exists(reference_index, table_name, field_name, value):
        table_index = reference_index.get(table_name)
        if table_index is None:
            return None
        if not table_index:
            return False
        expected_values = table_index.get(field_name)
        if expected_values is None and field_name == 'uuid_membre_event':
            expected_values = table_index.get('uuid_pg_membre_event')
        if expected_values is None:
            own_field = f"uuid_{table_name}"
            expected_values = table_index.get(own_field)
        if expected_values is None:
            return None
        return BusinessRulesEngine._to_text(value).lower() in expected_values

    @staticmethod
    def validate_database_constraints(table_name, row, reference_index=None):
        """Controle les contraintes de base detectables avant appel API."""
        errors = []
        row = row or {}

        required_fields = set(BusinessRulesEngine.REQUIRED_FIELDS.get(table_name, set()))
        primary_uuid = BusinessRulesEngine._primary_uuid_field(table_name, row)
        if primary_uuid:
            required_fields.add(primary_uuid)

        for field_name in sorted(required_fields):
            if field_name not in row or BusinessRulesEngine._is_empty(row.get(field_name)):
                errors.append(BusinessRulesEngine._error(
                    f"Champ obligatoire absent ou vide pour la base: {field_name}"
                ))

        for field_name, value in row.items():
            if BusinessRulesEngine._is_empty(value):
                continue
            if field_name.startswith('uuid_') and field_name not in BusinessRulesEngine.UUID_COLUMNS_WITH_TEXT_EXCEPTIONS:
                if not BusinessRulesEngine._is_uuid(value):
                    errors.append(BusinessRulesEngine._error(
                        f"Format UUID invalide dans {field_name}: {BusinessRulesEngine._to_text(value)}"
                    ))
            if (
                field_name in BusinessRulesEngine.INTEGER_COLUMNS
                or field_name.startswith('numero_')
                or field_name.startswith('nombre_')
                or field_name.startswith('nbre_')
            ) and not BusinessRulesEngine._is_int(value):
                errors.append(BusinessRulesEngine._error(
                    f"Format entier invalide dans {field_name}: {BusinessRulesEngine._to_text(value)}"
                ))
            if field_name.startswith('date_') and not BusinessRulesEngine._is_date(value):
                errors.append(BusinessRulesEngine._error(
                    f"Format date invalide dans {field_name}: {BusinessRulesEngine._to_text(value)}"
                ))
            if field_name in BusinessRulesEngine.BOOLEAN_COLUMNS and not BusinessRulesEngine._is_bool(value):
                errors.append(BusinessRulesEngine._error(
                    f"Format booleen invalide dans {field_name}: {BusinessRulesEngine._to_text(value)}"
                ))

        if reference_index:
            own_uuid = primary_uuid
            for field_name, ref_table in BusinessRulesEngine.FK_TABLES.items():
                if field_name not in row or field_name == own_uuid or BusinessRulesEngine._is_empty(row.get(field_name)):
                    continue
                exists = BusinessRulesEngine._reference_exists(reference_index, ref_table, field_name, row.get(field_name))
                if exists is False:
                    errors.append(BusinessRulesEngine._error(
                        f"Cle etrangere absente dans {ref_table}: {field_name}={BusinessRulesEngine._to_text(row.get(field_name))}"
                    ))

        return errors

    @staticmethod
    def validate_dataset(collected_data=None, original_data=None):
        """Valide les contraintes croisées pour toutes les tables chargees."""
        reference_index = BusinessRulesEngine.build_reference_index(collected_data, original_data)
        dataset_errors = {}
        for table_name, rows in (collected_data or {}).items():
            table_errors = {}
            for row_index, row in enumerate(rows or []):
                errors = BusinessRulesEngine.validate_database_constraints(
                    table_name, row, reference_index=reference_index
                )
                if errors:
                    table_errors[row_index] = errors
            dataset_errors[table_name] = table_errors
        return dataset_errors

    @staticmethod
    def validate_feature(table_name, feature, context=None):
        """
        Valide une entité QGIS selon les règles métier de sa table.

        Args:
            table_name: Nom de la table pour charger les règles.
            feature: Entité QgsFeature à valider.
            context: QgsExpressionContext optionnel pour réutilisation (performance).
        """
        errors = []
        rules = BusinessRulesEngine.RULES.get(table_name, [])
        errors.extend(BusinessRulesEngine.validate_database_constraints(
            table_name,
            BusinessRulesEngine._feature_to_dict(feature)
        ))

        if not rules:
            return errors

        if context is None:
            context = QgsExpressionContext()
            context.appendScope(QgsExpressionContextUtils.globalScope())

        context.setFeature(feature)

        for rule in rules:
            expr_str = rule['expr']
            cache_key = (table_name, expr_str)

            exp = BusinessRulesEngine._EXPRESSION_CACHE.get(cache_key)
            if exp is None:
                exp = QgsExpression(expr_str)
                # Optimization: prepare once with the context if fields are available.
                # Note: prepare() optimizes based on field names/indices in the context.
                exp.prepare(context)
                BusinessRulesEngine._EXPRESSION_CACHE[cache_key] = exp

            if not exp.evaluate(context):
                errors.append({
                    'message': rule['name'],
                    'severity': rule['severity']
                })
        return errors
