# -*- coding: utf-8 -*-
"""
Gestionnaire de jeton JWT pour MrvTeraka
Gère le stockage, validation et expiration des jetons
"""

import base64
import json
import time
from datetime import datetime, timedelta
from qgis.PyQt.QtCore import QSettings


class TokenManager:
    """Gère le stockage et la validation des jetons JWT"""

    def __init__(self, organization='iTeraka', app='MrvTeraka'):
        """
        Initialise le gestionnaire de jeton

        Args:
            organization: Organisation pour QSettings
            app: Nom de l'application pour QSettings
        """
        self.settings = QSettings(organization, app)
        self.token = None
        self.token_expiry = None
        self.mode = None
        self.api_url = None

    def save_token(self, token, api_url, mode, expires_in=None):
        """
        Sauvegarde un jeton avec métadonnées

        Args:
            token: Jeton JWT
            api_url: URL de base de l'API
            mode: Mode API (DJANGO ou STANDALONE)
            expires_in: Durée de validité en secondes (optionnel)
        """
        self.token = token
        self.api_url = api_url
        self.mode = mode

        # Calculer le temps d'expiration en fonction du JWT si possible
        if expires_in:
            expiry_time = time.time() + expires_in
        else:
            expiry_time = self._get_jwt_expiry(token) or (time.time() + (24 * 3600))

        self.token_expiry = expiry_time

        # Sauvegarder dans QSettings
        self.settings.setValue('token/jwt', token)
        self.settings.setValue('token/url', api_url)
        self.settings.setValue('token/mode', mode)
        self.settings.setValue('token/expiry', expiry_time)

        # Forcer l'écriture
        self.settings.sync()

    def load_token(self):
        """
        Charge le jeton sauvegardé

        Returns:
            Tuple (token, api_url, mode) ou (None, None, None)
        """
        token = self.settings.value('token/jwt')
        api_url = self.settings.value('token/url')
        mode = self.settings.value('token/mode')
        token_expiry = self.settings.value('token/expiry', type=float)

        if not token or not api_url:
            return None, None, None

        # Si l'expiration n'est pas présente, essayer de la lire depuis le JWT
        if token_expiry is None:
            jwt_expiry = self._get_jwt_expiry(token)
            if jwt_expiry:
                token_expiry = jwt_expiry
                self.settings.setValue('token/expiry', token_expiry)
                self.settings.sync()

        # Vérifier si le jeton a expiré
        if token_expiry and time.time() > token_expiry:
            self.clear_token()
            return None, None, None

        self.token = token
        self.api_url = api_url
        self.mode = mode
        self.token_expiry = token_expiry

        return token, api_url, mode

    def is_token_valid(self):
        """
        Vérifie si le jeton actuel est valide et non expiré

        Returns:
            bool: True si le jeton est valide et non expiré
        """
        if not self.token:
            token, _, _ = self.load_token()
            if not token:
                return False

        if self.token_expiry is None:
            jwt_expiry = self._get_jwt_expiry(self.token)
            if jwt_expiry:
                self.token_expiry = jwt_expiry
                self.settings.setValue('token/expiry', self.token_expiry)
                self.settings.sync()

        if self.token_expiry and time.time() > self.token_expiry:
            self.clear_token()
            return False

        return True

    def _get_jwt_expiry(self, token: str):
        """Retourne le timestamp d'expiration du JWT s'il est disponible."""
        payload = self.get_jwt_payload(token)
        if payload:
            exp = payload.get('exp')
            if isinstance(exp, (int, float)):
                return float(exp)
        return None

    def get_jwt_payload(self, token: str):
        """Décode et retourne le payload du JWT."""
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None

            payload = parts[1]
            padding = '=' * (-len(payload) % 4)
            decoded = base64.urlsafe_b64decode(payload + padding).decode('utf-8')
            return json.loads(decoded)
        except Exception:
            return None

    def get_user_id(self):
        """Retourne l'ID/UUID de l'utilisateur à partir du jeton."""
        payload = self.get_jwt_payload(self.token) if self.token else None
        if payload:
            # Essayer différents noms de champs communs pour l'ID utilisateur
            return payload.get('user_id') or payload.get('sub') or payload.get('uuid')
        return None

    def get_user_role(self):
        """Retourne le rôle de l'utilisateur à partir du jeton."""
        if not self.token:
            self.load_token()

        if not self.token:
            return None

        payload = self.get_jwt_payload(self.token)
        if payload:
            # Chercher le rôle dans les champs communs (role, roles, groups, etc.)
            return payload.get('role') or payload.get('roles') or payload.get('group') or payload.get('groups')
        return None

    def get_token_info(self):
        """
        Retourne les informations du jeton

        Returns:
            Dict avec les informations du jeton
        """
        if not self.is_token_valid():
            return None

        expiry_timestamp = self.token_expiry or 0
        expiry_datetime = datetime.fromtimestamp(expiry_timestamp)
        time_remaining = expiry_timestamp - time.time()

        return {
            'token': self.token[:20] + '...' if self.token else None,
            'api_url': self.api_url,
            'mode': self.mode,
            'expires_at': expiry_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            'time_remaining_seconds': max(0, int(time_remaining)),
            'is_valid': True
        }

    def clear_token(self):
        """Supprime le jeton stocké"""
        self.token = None
        self.token_expiry = None
        self.mode = None
        self.api_url = None

        self.settings.remove('token/jwt')
        self.settings.remove('token/url')
        self.settings.remove('token/mode')
        self.settings.remove('token/expiry')
        self.settings.sync()

    def refresh_token_expiry(self, expires_in=None):
        """
        Rafraîchit le délai d'expiration du jeton

        Args:
            expires_in: Nouvelle durée de validité en secondes
        """
        if not self.token:
            return False

        if expires_in:
            new_expiry = time.time() + expires_in
        else:
            new_expiry = time.time() + (24 * 3600)

        self.token_expiry = new_expiry
        self.settings.setValue('token/expiry', new_expiry)
        self.settings.sync()

        return True

