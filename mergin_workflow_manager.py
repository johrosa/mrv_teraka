# -*- coding: utf-8 -*-
"""
MerginWorkflowManager
Gère le workflow complet de préparation Mergin jusqu'à la validation et fusion
"""

import json
import os
import datetime
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

    def __init__(self, postgrest_client):
        self.postgrest = postgrest_client

    def detect_conflicts(self, original, collected, pk_field='id'):
        """Détecte les conflits entre données originales et collectées"""
        conflicts = []

        # Entrées supprimées
        original_ids = {item.get(pk_field) for item in original}
        collected_ids = {item.get(pk_field) for item in collected}

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

        # Entrées modifiées - Optimization: O(N+M) with dictionary lookup
        original_dict = {item.get(pk_field): item for item in original if item.get(pk_field) is not None}
        for coll_item in collected:
            item_id = coll_item.get(pk_field)
            if item_id is None:
                continue
            orig_item = original_dict.get(item_id)

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
        conflicts = self.detect_conflicts(original, collected, pk_field=pk_field)
        results = {
            'table': table,
            'strategy': strategy,
            'merged_at': datetime.datetime.now().isoformat(),
            'conflicts': conflicts,
            'actions': []
        }

        if strategy == 'merge':
            # 1. Identifier les actions basées sur les conflits détectés
            modified_ids = {c['id'] for c in conflicts if c['type'] == 'modified'}
            added_ids = set()
            for c in conflicts:
                if c['type'] == 'added':
                    added_ids.update(c['ids'])

            # 2. Optimization: Combine additions and modifications into a single batch UPSERT call
            items_to_upsert = [item for item in collected if item.get(pk_field) in added_ids or item.get(pk_field) in modified_ids]
            if items_to_upsert:
                try:
                    self.postgrest.insert(table, items_to_upsert, upsert=True)
                    for item in items_to_upsert:
                        action_type = 'inserted' if item.get(pk_field) in added_ids else 'updated'
                        results['actions'].append({'type': action_type, 'id': item.get(pk_field)})
                except Exception as e:
                    results['actions'].append({'type': 'error', 'msg': f"Erreur upsert batch: {str(e)}"})

            # 3. Optimization: Batch deletions using 'in.' filter with chunking (to avoid URL length limits)
            deleted_ids = []
            for c in conflicts:
                if c['type'] == 'deleted':
                    deleted_ids.extend(c['ids'])

            if deleted_ids:
                # Chunk size for UUIDs/IDs to keep URL length under ~8KB (safe limit)
                chunk_size = 200
                for i in range(0, len(deleted_ids), chunk_size):
                    chunk = [str(d_id) for d_id in deleted_ids[i:i + chunk_size]]
                    try:
                        self.postgrest.delete(table, {pk_field: f"in.({','.join(chunk)})"})
                        for d_id in chunk:
                            results['actions'].append({'type': 'deleted', 'id': d_id})
                    except Exception as e:
                        results['actions'].append({'type': 'error', 'msg': f"Erreur delete batch chunk: {str(e)}"})

        elif strategy == 'replace':
            # Stratégie radicale : supprimer tout et réinsérer
            try:
                # On utilise 'in' avec chunking pour supprimer proprement
                original_ids = [str(o.get(pk_field)) for o in original if o.get(pk_field) is not None]
                if original_ids:
                    chunk_size = 200
                    for i in range(0, len(original_ids), chunk_size):
                        chunk = original_ids[i:i + chunk_size]
                        self.postgrest.delete(table, {pk_field: f"in.({','.join(chunk)})"})

                self.postgrest.insert(table, collected)
                results['actions'].append({'type': 'replace_all', 'count': len(collected)})
            except Exception as e:
                results['actions'].append({'type': 'error', 'msg': str(e)})

        return results

