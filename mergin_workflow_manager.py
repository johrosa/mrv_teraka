# -*- coding: utf-8 -*-
"""
MerginWorkflowManager
Gère le workflow complet de préparation Mergin jusqu'à la validation et fusion
"""

import json
import os
import datetime
import re
from pathlib import Path


class MerginWorkflowManager:
    """Gère le cycle complet Mergin Map"""

    WORKFLOW_STAGES = {
        1: "Préparation",      # Charger données API, créer projet
        2: "Export",           # Exporter pour terrain
        3: "Collecte",         # Terrain (Mergin Map)
        4: "Imported",         # Données importées du terrain
        5: "Validation",       # Vérification des données
        6: "Fusion",           # Fusion avec la base
        7: "Synchronisation"   # Mise à jour API
    }

    def __init__(self, plugin_dir):
        self.plugin_dir = plugin_dir
        self.workflow_dir = os.path.join(plugin_dir, 'mergin_workflows')
        self.projects_dir = os.path.join(self.workflow_dir, 'projects')
        self.backups_dir = os.path.join(self.workflow_dir, 'backups')

        # Créer les répertoires s'ils n'existent pas
        for directory in [self.workflow_dir, self.projects_dir, self.backups_dir]:
            Path(directory).mkdir(parents=True, exist_ok=True)

    def create_project(self, project_name, source_tables, description=""):
        """
        Crée un nouveau projet Mergin et initialise son dossier.

        Args:
            project_name (str): Nom convivial du projet.
            source_tables (list or str): Liste des tables sources ou chaîne séparée par virgules.
            description (str): Description optionnelle.

        Returns:
            str: L'ID unique du projet généré.
        """
        if isinstance(source_tables, str):
            source_tables = [t.strip() for t in source_tables.split(',') if t.strip()]

        project_id = f"{project_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        project_path = os.path.join(self.projects_dir, project_id)
        Path(project_path).mkdir(parents=True, exist_ok=True)

        # Créer le fichier de métadonnées
        metadata = {
            'id': project_id,
            'name': project_name,
            'source_tables': source_tables,
            'description': description,
            'created': datetime.datetime.now().isoformat(),
            'stage': 1,  # Préparation
            'stages_completed': [1]
        }

        metadata_file = os.path.join(project_path, 'metadata.json')
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

        return project_id

    def save_exported_gpkg(self, project_id, gpkg_path):
        """
        Enregistre le chemin du GeoPackage généré pour le terrain.
        """
        import shutil
        project_path = os.path.join(self.projects_dir, project_id)
        target_path = os.path.join(project_path, 'mission_data.gpkg')

        source_path = os.path.normcase(os.path.abspath(gpkg_path))
        destination_path = os.path.normcase(os.path.abspath(target_path))
        if source_path != destination_path:
            shutil.copy(source_path, destination_path)

        self.update_stage(project_id, 2)  # Export

    def save_exported_data(self, project_id, data):
        """
        Sauvegarde les données initiales extraites de l'API (Snapshot JSON pour comparaison).
        """
        project_path = os.path.join(self.projects_dir, project_id)
        export_file = os.path.join(project_path, 'exported_data.json')

        with open(export_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        if not os.path.exists(os.path.join(project_path, 'mission_data.gpkg')):
            self.update_stage(project_id, 2)  # Export

    def import_collected_data(self, project_id, data):
        """Importe les données collectées au terrain"""
        project_path = os.path.join(self.projects_dir, project_id)
        import_file = os.path.join(project_path, 'imported_data.json')

        # Créer une sauvegarde des données originales
        self.backup_data(project_id, 'imported_data', data)

        with open(import_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self.update_stage(project_id, 4)  # Imported

    def validate_data(self, project_id, validation_results):
        """Stocke les résultats de validation"""
        project_path = os.path.join(self.projects_dir, project_id)
        validation_file = os.path.join(project_path, 'validation_results.json')

        # Ajouter timestamp
        validation_results['validated_at'] = datetime.datetime.now().isoformat()

        with open(validation_file, 'w', encoding='utf-8') as f:
            json.dump(validation_results, f, ensure_ascii=False, indent=2)

        self.update_stage(project_id, 5)  # Validation

    def merge_data(self, project_id, merge_results):
        """Stocke les résultats de fusion"""
        project_path = os.path.join(self.projects_dir, project_id)
        merge_file = os.path.join(project_path, 'merge_results.json')

        merge_results['merged_at'] = datetime.datetime.now().isoformat()

        with open(merge_file, 'w', encoding='utf-8') as f:
            json.dump(merge_results, f, ensure_ascii=False, indent=2)

        self.update_stage(project_id, 6)  # Fusion

    def sync_to_api(self, project_id, sync_results):
        """Enregistre la synchronisation vers l'API"""
        project_path = os.path.join(self.projects_dir, project_id)
        sync_file = os.path.join(project_path, 'sync_results.json')

        sync_results['synced_at'] = datetime.datetime.now().isoformat()

        with open(sync_file, 'w', encoding='utf-8') as f:
            json.dump(sync_results, f, ensure_ascii=False, indent=2)

        self.update_stage(project_id, 7)  # Synchronisation

    def update_stage(self, project_id, stage):
        """Met à jour l'étape du projet"""
        metadata_file = os.path.join(self.projects_dir, project_id, 'metadata.json')

        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        metadata['stage'] = stage
        if stage not in metadata.get('stages_completed', []):
            metadata['stages_completed'].append(stage)

        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

    def backup_data(self, project_id, data_type, data):
        """Crée une sauvegarde des données"""
        backup_dir = os.path.join(self.backups_dir, project_id)
        Path(backup_dir).mkdir(parents=True, exist_ok=True)

        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f"{data_type}_{timestamp}.json")

        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_project_info(self, project_id):
        """Récupère les informations d'un projet et gère la migration des anciennes métadonnées."""
        metadata_file = os.path.join(self.projects_dir, project_id, 'metadata.json')

        if os.path.exists(metadata_file):
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            # Migration logic: convert source_table (str) to source_tables (list)
            if 'source_table' in metadata and 'source_tables' not in metadata:
                table = metadata.pop('source_table')
                metadata['source_tables'] = [t.strip() for t in table.split(',') if t.strip()]
                # Update the file with migrated data
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)

            return metadata
        return None

    def get_project_layers(self, project_id):
        """Retourne la liste des tables associées à un projet"""
        info = self.get_project_info(project_id)
        if info:
            return info.get('source_tables', [])
        return []

    def list_external_mergin_projects(self, base_dir):
        """
        Liste les projets Mergin Maps officiels présents dans base_dir.
        Un projet est identifié par un dossier contenant un fichier .qgs ou .qgz.
        """
        projects = []
        if not base_dir or not os.path.exists(base_dir):
            return projects

        for item in os.listdir(base_dir):
            item_path = os.path.join(base_dir, item)
            if os.path.isdir(item_path):
                # Chercher un fichier projet QGIS
                qgis_files = [f for f in os.listdir(item_path) if f.endswith(('.qgs', '.qgz'))]
                if qgis_files:
                    projects.append({
                        'id': item_path,
                        'name': item,
                        'project_file': os.path.join(item_path, qgis_files[0])
                    })
        return projects

    def list_projects(self):
        """Liste tous les projets Mergin (uniquement les nouveaux, selon consigne)"""
        # La consigne demande d'ouvrir les projets du plugin Mergin Maps
        # On garde cette méthode pour la compatibilité interne si besoin,
        # mais on privilégiera list_external_mergin_projects dans l'UI.
        projects = []
        if os.path.exists(self.projects_dir):
            for project_id in os.listdir(self.projects_dir):
                info = self.get_project_info(project_id)
                if info:
                    projects.append(info)
        return projects

    def generate_workflow_report(self, project_id):
        """Génère un rapport du workflow complet"""
        project_path = os.path.join(self.projects_dir, project_id)

        report = {
            'project_id': project_id,
            'report_generated': datetime.datetime.now().isoformat(),
            'stages': {}
        }

        # Métadonnées
        metadata = self.get_project_info(project_id)
        report['metadata'] = metadata

        # Vérifier les fichiers d'étapes
        for stage_num in range(1, 8):
            stage_name = self.WORKFLOW_STAGES[stage_num]
            report['stages'][stage_name] = {
                'completed': stage_num in metadata.get('stages_completed', []),
                'files': []
            }

        # Fichiers disponibles
        for filename in os.listdir(project_path):
            if filename.endswith('.json'):
                report['stages']['Fichiers'] = report['stages'].get('Fichiers', [])
                report['stages']['Fichiers'].append(filename)

        return report

    def export_report_to_file(self, project_id, output_file=None):
        """Exporte le rapport à un fichier"""
        report = self.generate_workflow_report(project_id)

        if not output_file:
            output_file = os.path.join(
                self.workflow_dir,
                f"report_{project_id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        return output_file


class MerginDataMerger:
    """Gère la fusion des données collectées avec la base de données"""

    REPEATED_ERROR_LIMIT = 10

    def __init__(self, postgrest_client):
        self.postgrest = postgrest_client

    @staticmethod
    def _chunks(items, size):
        for start in range(0, len(items), size):
            yield items[start:start + size]

    @staticmethod
    def _postgrest_in_value(value):
        text = str(value)
        if any(ch in text for ch in [',', '(', ')', '"', ' ']):
            text = '"' + text.replace('"', '\\"') + '"'
        return text

    @staticmethod
    def _prepare_payload_rows(rows, conflict_field=None):
        prepared_rows = []
        conflict_field = str(conflict_field or '').lower()
        for row in rows:
            if not isinstance(row, dict):
                prepared_rows.append(row)
                continue

            prepared = dict(row)
            # Ne pas envoyer id=null à PostgREST: PostgreSQL ne déclenche pas
            # la valeur par défaut si la colonne est explicitement fournie à NULL.
            if prepared.get('id') in (None, '') and conflict_field != 'id':
                prepared.pop('id', None)
            prepared_rows.append(prepared)
        return prepared_rows

    @staticmethod
    def _row_identifier(row, pk_field='id'):
        if not isinstance(row, dict):
            return "ligne inconnue"
        for key in (pk_field, 'id', 'uuid_arbre_gps', 'uuid_bosquet_gps', 'uuid_pg_gps', 'uuid_pg', 'uuid_membre'):
            value = row.get(key)
            if value not in (None, ""):
                return f"{key}={value}"
        return "ligne sans identifiant"

    @staticmethod
    def _error_signature(exc):
        text = str(exc)
        for prefix in ('Details:', 'Détails:'):
            if prefix in text:
                text = text.split(prefix, 1)[0]
        text = re.sub(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', '<uuid>', text, flags=re.IGNORECASE)
        text = re.sub(r'\([^)]{30,}\)', '(<row>)', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:500]

    def _record_repeated_error(self, results, table, rows, pk_field, exc, error_state):
        signature = self._error_signature(exc)
        count = error_state.get(signature, 0) + len(rows)
        error_state[signature] = count
        sample = self._row_identifier(rows[0], pk_field) if rows else "ligne inconnue"
        message = (
            f"{table}: isolation arrêtée pour {len(rows)} ligne(s), "
            f"même erreur déjà répétée {count} fois. Exemple {sample}."
        )
        results.setdefault('steps', []).append(message)
        results['actions'].append({
            'type': 'error',
            'table': table,
            'row': sample,
            'count': len(rows),
            'signature': signature,
            'msg': (
                f"{len(rows)} ligne(s) non publiées: même erreur répétée "
                f"({count} occurrence(s)). Exemple {sample}: {str(exc)}"
            )
        })

    def _insert_with_fallback(self, table, rows, results, action_type, pk_field='id', upsert=False, error_state=None):
        if not rows:
            return

        error_state = error_state if error_state is not None else {}

        try:
            payload_rows = self._prepare_payload_rows(rows, pk_field)
            self.postgrest.insert(
                table,
                payload_rows,
                upsert=upsert,
                on_conflict=pk_field if upsert else None
            )
            for row in rows:
                results['actions'].append({'type': action_type, 'id': row.get(pk_field)})
            results.setdefault('steps', []).append(
                f"{table}: {len(rows)} ligne(s) {'mises à jour' if upsert else 'insérées'} en batch."
            )
            return
        except Exception as exc:
            signature = self._error_signature(exc)
            if error_state.get(signature, 0) >= self.REPEATED_ERROR_LIMIT:
                self._record_repeated_error(results, table, rows, pk_field, exc, error_state)
                return

            if len(rows) == 1:
                row = rows[0]
                error_state[signature] = error_state.get(signature, 0) + 1
                results.setdefault('steps', []).append(
                    f"{table}: ligne ignorée ({self._row_identifier(row, pk_field)}), erreur {error_state[signature]}/{self.REPEATED_ERROR_LIMIT} du même type."
                )
                results['actions'].append({
                    'type': 'error',
                    'table': table,
                    'id': row.get(pk_field) if isinstance(row, dict) else None,
                    'row': self._row_identifier(row, pk_field),
                    'signature': signature,
                    'msg': f"{self._row_identifier(row, pk_field)}: {str(exc)}"
                })
                return

            midpoint = len(rows) // 2
            results.setdefault('steps', []).append(
                f"{table}: batch de {len(rows)} ligne(s) en erreur, découpage en {midpoint} + {len(rows) - midpoint}."
            )
            self._insert_with_fallback(table, rows[:midpoint], results, action_type, pk_field, upsert, error_state)
            self._insert_with_fallback(table, rows[midpoint:], results, action_type, pk_field, upsert, error_state)

    def _delete_with_fallback(self, table, ids, results, pk_field='id', error_state=None):
        ids = [d_id for d_id in ids if d_id is not None]
        if not ids:
            return

        error_state = error_state if error_state is not None else {}

        try:
            id_list = ",".join(self._postgrest_in_value(d_id) for d_id in ids)
            self.postgrest.delete(table, {pk_field: f'in.({id_list})'})
            for d_id in ids:
                results['actions'].append({'type': 'deleted', 'id': d_id})
            results.setdefault('steps', []).append(f"{table}: {len(ids)} suppression(s) en batch.")
            return
        except Exception as exc:
            signature = self._error_signature(exc)
            if error_state.get(signature, 0) >= self.REPEATED_ERROR_LIMIT:
                error_state[signature] = error_state.get(signature, 0) + len(ids)
                results.setdefault('steps', []).append(
                    f"{table}: {len(ids)} suppression(s) ignorée(s), même erreur répétée {error_state[signature]} fois."
                )
                results['actions'].append({
                    'type': 'error',
                    'table': table,
                    'ids': ids[:5],
                    'count': len(ids),
                    'signature': signature,
                    'error': f"{len(ids)} suppression(s) non publiées: même erreur répétée. {str(exc)}"
                })
                return

            if len(ids) == 1:
                error_state[signature] = error_state.get(signature, 0) + 1
                results.setdefault('steps', []).append(
                    f"{table}: suppression ignorée ({pk_field}={ids[0]}), erreur {error_state[signature]}/{self.REPEATED_ERROR_LIMIT} du même type."
                )
                results['actions'].append({
                    'type': 'error',
                    'table': table,
                    'ids': ids,
                    'signature': signature,
                    'error': f"{pk_field}={ids[0]}: {str(exc)}"
                })
                return

            midpoint = len(ids) // 2
            results.setdefault('steps', []).append(
                f"{table}: batch suppression de {len(ids)} en erreur, découpage en {midpoint} + {len(ids) - midpoint}."
            )
            self._delete_with_fallback(table, ids[:midpoint], results, pk_field, error_state)
            self._delete_with_fallback(table, ids[midpoint:], results, pk_field, error_state)

    def detect_conflicts(self, original, collected, pk_field='id'):
        """Détecte les conflits entre données originales et collectées"""
        conflicts = []

        # Entrées supprimées
        original_by_id = {
            item.get(pk_field): item
            for item in original
            if isinstance(item, dict) and item.get(pk_field) is not None
        }
        collected_by_id = {
            item.get(pk_field): item
            for item in collected
            if isinstance(item, dict) and item.get(pk_field) is not None
        }
        original_ids = set(original_by_id.keys())
        collected_ids = set(collected_by_id.keys())

        deleted_ids = original_ids - collected_ids
        conflicts.append({
            'type': 'deleted',
            'count': len(deleted_ids),
            'ids': list(deleted_ids)
        })

        # Entrées ajoutées
        new_ids = collected_ids - original_ids
        conflicts.append({
            'type': 'added',
            'count': len(new_ids),
            'ids': list(new_ids)
        })

        # Entrées modifiées
        for coll_item in collected:
            item_id = coll_item.get(pk_field)
            orig_item = original_by_id.get(item_id)

            if orig_item and orig_item != coll_item:
                conflicts.append({
                    'type': 'modified',
                    'id': item_id,
                    'original': orig_item,
                    'collected': coll_item
                })

        return conflicts

    def merge(self, table, original, collected, strategy='merge', pk_field='id'):
        """
        Fusionne les données collectées avec la base de données.

        Args:
            table: Nom de la table API.
            original: Liste des données originales (snapshot).
            collected: Liste des données collectées (validées).
            strategy: 'merge' (intelligent) ou 'replace' (tout écraser).
            pk_field: Champ de clé primaire.

        Returns:
            dict: Résultats détaillés de la fusion.
        """
        # Préférer un champ uuid_<endpoint> si présent dans les données collectées
        try:
            endpoint_name = str(table).strip().strip('/')
        except Exception:
            endpoint_name = str(table or '')

        uuid_candidate = None
        if hasattr(self, 'postgrest') and hasattr(self.postgrest, '_infer_uuid_conflict_field'):
            try:
                uuid_candidate = self.postgrest._infer_uuid_conflict_field(endpoint_name, collected)
            except Exception:
                uuid_candidate = None

        if uuid_candidate:
            pk_field = uuid_candidate

        conflicts = self.detect_conflicts(original, collected, pk_field=pk_field)
        results = {
            'table': table,
            'strategy': strategy,
            'merged_at': datetime.datetime.now().isoformat(),
            'conflicts': conflicts,
            'actions': [],
            'steps': [],
            'pk_field_used': pk_field
        }

        if strategy == 'merge':
            # 1. Identifier les actions basées sur les conflits détectés
            modified_ids = {c['id'] for c in conflicts if c['type'] == 'modified'}
            added_ids = set()
            for c in conflicts:
                if c['type'] == 'added':
                    added_ids.update(c['ids'])
            deleted_ids = []
            for c in conflicts:
                if c['type'] == 'deleted':
                    deleted_ids.extend(c['ids'])

            # 2. Traiter les ajouts en insertion simple.
            # Un POST avec on_conflict exige une contrainte unique côté PostgreSQL.
            # Pour les nouvelles lignes détectées localement, l'upsert est inutile
            # et peut provoquer un 400 si la colonne UUID métier n'est pas unique.
            items_to_insert = [item for item in collected if item.get(pk_field) in added_ids]
            items_to_update = [item for item in collected if item.get(pk_field) in modified_ids]
            error_state = {}
            results['steps'].append(
                f"{table}: {len(items_to_insert)} ajout(s), {len(items_to_update)} mise(s) à jour, {len(deleted_ids)} suppression(s) détectée(s)."
            )
            for items_chunk in self._chunks(items_to_insert, 1000):
                results['steps'].append(f"{table}: tentative insertion batch de {len(items_chunk)} ligne(s).")
                self._insert_with_fallback(table, items_chunk, results, 'inserted', pk_field, upsert=False, error_state=error_state)

            # 3. Traiter les modifications en upsert batch.
            for items_chunk in self._chunks(items_to_update, 1000):
                results['steps'].append(f"{table}: tentative mise à jour batch de {len(items_chunk)} ligne(s).")
                self._insert_with_fallback(table, items_chunk, results, 'updated', pk_field, upsert=True, error_state=error_state)

            # 4. Traiter les suppressions si nécessaire (stratégie merge respecte la suppression terrain)
            deleted_ids = [d_id for d_id in deleted_ids if d_id is not None]
            delete_error_state = {}
            for ids_chunk in self._chunks(deleted_ids, 200):
                results['steps'].append(f"{table}: tentative suppression batch de {len(ids_chunk)} ligne(s).")
                self._delete_with_fallback(table, ids_chunk, results, pk_field, delete_error_state)

        elif strategy == 'replace':
            # Stratégie radicale : supprimer tout et réinsérer
            results.setdefault('steps', []).append(
                f"{table}: remplacement complet demandé ({len(original)} existante(s), {len(collected)} nouvelle(s))."
            )
            try:
                # On utilise 'in' pour supprimer en une seule requête si possible
                original_ids = [o.get(pk_field) for o in original if o.get(pk_field) is not None]
                delete_error_state = {}
                for ids_chunk in self._chunks(original_ids, 200):
                    self._delete_with_fallback(table, ids_chunk, results, pk_field, delete_error_state)

                insert_error_state = {}
                for items_chunk in self._chunks(collected, 1000):
                    self._insert_with_fallback(table, items_chunk, results, 'inserted', pk_field, upsert=False, error_state=insert_error_state)
                results['actions'].append({'type': 'replace_all', 'count': len(collected)})
            except Exception as e:
                results['actions'].append({'type': 'error', 'msg': str(e)})

        return results

