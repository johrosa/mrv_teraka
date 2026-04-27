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

    def create_project(self, project_name, source_table, description=""):
        """
        Crée un nouveau projet Mergin

        Args:
            project_name: Nom du projet
            source_table: Table source de l'API
            description: Description du projet

        Returns:
            project_id (str)
        """
        project_id = f"{project_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        project_path = os.path.join(self.projects_dir, project_id)
        Path(project_path).mkdir(parents=True, exist_ok=True)

        # Créer le fichier de métadonnées
        metadata = {
            'id': project_id,
            'name': project_name,
            'source_table': source_table,
            'description': description,
            'created': datetime.datetime.now().isoformat(),
            'stage': 1,  # Préparation
            'stages_completed': [1]
        }

        metadata_file = os.path.join(project_path, 'metadata.json')
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

        return project_id

    def save_exported_data(self, project_id, data):
        """Sauvegarde les données exportées"""
        project_path = os.path.join(self.projects_dir, project_id)
        export_file = os.path.join(project_path, 'exported_data.json')

        with open(export_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

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
        """Récupère les informations d'un projet"""
        metadata_file = os.path.join(self.projects_dir, project_id, 'metadata.json')

        if os.path.exists(metadata_file):
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def list_projects(self):
        """Liste tous les projets Mergin"""
        projects = []
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

        # Entrées modifiées
        for coll_item in collected:
            item_id = coll_item.get(pk_field)
            orig_item = next((o for o in original if o.get(pk_field) == item_id), None)

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
        Fusionne les données

        Args:
            table: Nom de la table
            original: Données originales
            collected: Données collectées
            strategy: 'merge' | 'replace' | 'manual'
            pk_field: Nom du champ clé primaire

        Returns:
            Résultats de la fusion
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
            # Fusion intelligente
            for item in collected:
                action = self._merge_item(table, item, pk_field=pk_field)
                results['actions'].append(action)

        elif strategy == 'replace':
            # Remplacer toutes les données
            results['actions'] = [
                {
                    'type': 'replace_all',
                    'table': table,
                    'count': len(collected)
                }
            ]

        return results

    def _merge_item(self, table, item, pk_field='id'):
        """Fusionne un article unique"""
        item_id = item.get(pk_field)

        try:
            # Vérifier si existe
            result = self.postgrest.select(table, filters={f'{pk_field}': f'eq.{item_id}'})

            if result:
                # Mettre à jour
                self.postgrest.update(table, item, {f'{pk_field}': f'eq.{item_id}'})
                return {'type': 'updated', 'id': item_id}
            else:
                # Insérer
                self.postgrest.insert(table, item)
                return {'type': 'inserted', 'id': item_id}

        except Exception as e:
            return {'type': 'error', 'id': item_id, 'error': str(e)}

