# -*- coding: utf-8 -*-
"""
Système de threads pour les tâches longues avec support d'annulation.
Évite le gel de l'interface QGIS pendant les opérations longues.
"""

from qgis.PyQt.QtCore import QThread, pyqtSignal, QObject
import traceback


class WorkerSignals(QObject):
    """Signaux pour communiquer avec le thread principal."""

    # Signal émis quand la tâche progresse (int: pourcentage 0-100)
    progress = pyqtSignal(int, str)

    # Signal émis quand la tâche est terminée avec succès (object: résultat)
    finished = pyqtSignal(object)

    # Signal émis en cas d'erreur (Exception, str: traceback)
    error = pyqtSignal(Exception, str)

    # Signal émis quand la tâche est annulée
    cancelled = pyqtSignal()

    # Signal pour mettre à jour le message de statut
    status = pyqtSignal(str)


class Worker(QThread):
    """
    Thread worker générique pour exécuter des tâches longues.

    Usage:
        def my_long_task(worker):
            for i in range(100):
                if worker.is_cancelled:
                    return None
                # Faire quelque chose
                worker.update_progress(i, f"Étape {i}/100")
            return result

        worker = Worker(my_long_task)
        worker.signals.progress.connect(on_progress)
        worker.signals.finished.connect(on_finished)
        worker.signals.error.connect(on_error)
        worker.signals.cancelled.connect(on_cancelled)
        worker.start()

        # Pour annuler:
        worker.cancel()
    """

    def __init__(self, task_func, *args, **kwargs):
        """
        Initialise le worker.

        Args:
            task_func: Fonction à exécuter. Doit accepter le worker comme premier argument.
            *args: Arguments positionnels pour task_func
            **kwargs: Arguments nommés pour task_func
        """
        super().__init__()
        self.task_func = task_func
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.is_cancelled = False
        self.result = None

    def run(self):
        """Exécute la tâche dans le thread."""
        try:
            # Passer le worker comme premier argument pour permettre l'annulation
            self.result = self.task_func(self, *self.args, **self.kwargs)

            if self.is_cancelled:
                self.signals.cancelled.emit()
            else:
                self.signals.finished.emit(self.result)

        except Exception as e:
            tb = traceback.format_exc()
            self.signals.error.emit(e, tb)

    def cancel(self):
        """Demande l'annulation de la tâche."""
        self.is_cancelled = True
        self.signals.status.emit("Annulation en cours...")

    def update_progress(self, value, message=""):
        """
        Met à jour la progression de la tâche.

        Args:
            value: Pourcentage de progression (0-100)
            message: Message descriptif
        """
        if not self.is_cancelled:
            self.signals.progress.emit(int(value), message)

    def update_status(self, message):
        """
        Met à jour le message de statut.

        Args:
            message: Message à afficher
        """
        if not self.is_cancelled:
            self.signals.status.emit(message)


class MerginSyncWorker(Worker):
    """Worker spécialisé pour les synchronisations Mergin Maps."""

    def __init__(self, mergin_client, project_path, direction='pull'):
        """
        Args:
            mergin_client: Instance du client Mergin
            project_path: Chemin du projet Mergin
            direction: 'pull' ou 'push'
        """
        super().__init__(self._sync_task, mergin_client, project_path, direction)

    @staticmethod
    def _sync_task(worker, mergin_client, project_path, direction):
        """Tâche de synchronisation Mergin."""
        try:
            worker.update_progress(10, f"Connexion à Mergin Maps...")

            if worker.is_cancelled:
                return None

            if direction == 'pull':
                worker.update_progress(30, f"Téléchargement des données du serveur...")
                mergin_client.pull_project(project_path)
                worker.update_progress(90, "Téléchargement terminé")
            else:  # push
                worker.update_progress(30, f"Envoi des données vers le serveur...")
                mergin_client.push_project(project_path)
                worker.update_progress(90, "Envoi terminé")

            if worker.is_cancelled:
                return None

            worker.update_progress(100, "Synchronisation terminée")
            return True

        except Exception as e:
            raise e


class BackendSyncWorker(Worker):
    """Worker spécialisé pour les synchronisations avec le backend API."""

    def __init__(self, postgrest_client, mapping, original_data, validated_data, merge_func):
        """
        Args:
            postgrest_client: Instance du client PostgREST
            mapping: Configuration du mapping
            original_data: Données originales
            validated_data: Données validées
            merge_func: Fonction de fusion des données
        """
        super().__init__(
            self._sync_task,
            postgrest_client,
            mapping,
            original_data,
            validated_data,
            merge_func
        )

    @staticmethod
    def _sync_task(worker, postgrest_client, mapping, original_data, validated_data, merge_func):
        """Tâche de synchronisation backend."""
        try:
            worker.update_progress(10, "Préparation de la fusion...")

            if worker.is_cancelled:
                return None

            worker.update_progress(30, "Fusion des données validées...")
            merge_results = merge_func(mapping, original_data, validated_data)

            if worker.is_cancelled:
                return None

            if not merge_results:
                return None

            worker.update_progress(70, "Synchronisation avec le backend...")

            # Ici on pourrait ajouter la logique de synchronisation réelle
            # Pour l'instant on retourne juste les résultats de fusion

            if worker.is_cancelled:
                return None

            worker.update_progress(100, "Synchronisation terminée")
            return merge_results

        except Exception as e:
            raise e


def create_mergin_sync_worker(mergin_client, project_path, direction='pull'):
    """
    Factory pour créer un worker de synchronisation Mergin.

    Args:
        mergin_client: Instance du client Mergin
        project_path: Chemin du projet Mergin
        direction: 'pull' ou 'push'

    Returns:
        MerginSyncWorker configuré
    """
    return MerginSyncWorker(mergin_client, project_path, direction)


def create_backend_sync_worker(postgrest_client, mapping, original_data, validated_data, merge_func):
    """
    Factory pour créer un worker de synchronisation backend.

    Args:
        postgrest_client: Instance du client PostgREST
        mapping: Configuration du mapping
        original_data: Données originales
        validated_data: Données validées
        merge_func: Fonction de fusion

    Returns:
        BackendSyncWorker configuré
    """
    return BackendSyncWorker(postgrest_client, mapping, original_data, validated_data, merge_func)
