# -*- coding: utf-8 -*-
"""
Routine de vérification de connexion en arrière-plan.
"""

from qgis.PyQt.QtCore import QThread, pyqtSignal, QTimer
import time

class ConnectionChecker(QThread):
    """
    Thread de vérification périodique de la connexion API.
    """

    # Signaux
    connection_status_changed = pyqtSignal(bool, str)  # (est_connecté, message)

    def __init__(self, interval=60):
        """
        Initialise le checker.

        Args:
            interval: Intervalle entre les vérifications en secondes.
        """
        super().__init__()
        self.interval = interval
        self.postgrest_client = None
        self.is_running = False
        self._last_status = None

    def set_client(self, client):
        """Définit le client PostgREST à tester."""
        self.postgrest_client = client
        # Forcer une vérification au prochain cycle si le client change
        self._last_status = None

    def run(self):
        """Boucle principale du thread."""
        self.is_running = True

        while self.is_running:
            if self.postgrest_client:
                try:
                    # Vérifier le token via l'API
                    is_valid = self.postgrest_client.verify_token()

                    # Émettre le signal seulement si le statut change
                    if is_valid != self._last_status:
                        msg = "Connecté" if is_valid else "Session expirée ou serveur injoignable"
                        self.connection_status_changed.emit(is_valid, msg)
                        self._last_status = is_valid

                except Exception as e:
                    if self._last_status is not False:
                        self.connection_status_changed.emit(False, f"Erreur connexion: {str(e)}")
                        self._last_status = False

            # Attendre l'intervalle spécifié par petits pas pour pouvoir arrêter rapidement
            for _ in range(self.interval):
                if not self.is_running:
                    break
                time.sleep(1)

    def stop(self):
        """Arrête proprement le thread."""
        self.is_running = False
        self.wait()
