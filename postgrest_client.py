# -*- coding: utf-8 -*-
"""
PostgREST Client pour le plugin MrvTeraka
Fournit une abstraction pour interagir avec une API PostgREST
Compatible avec PostgREST pur et PostgREST via Django
"""

import json
import urllib.request
import urllib.error
import urllib.parse
from typing import Any, Dict, List, Optional
from enum import Enum
import re
import requests


class PostgRESTMode(Enum):
    """Modes de PostgREST supportés"""
    STANDALONE = "standalone"      # PostgREST pur (http://localhost:3000)
    DJANGO = "django"              # PostgREST via Django (http://localhost:8000/api)


class PostgRESTError(RuntimeError):
    """Erreur PostgREST structurée avec le corps JSON d'origine si disponible."""

    def __init__(
        self,
        status_code: int,
        reason: str,
        url: str,
        method: str,
        endpoint: str,
        error_body: str,
        error_json: Optional[Dict[str, Any]] = None,
    ):
        self.status_code = status_code
        self.reason = reason
        self.url = url
        self.method = method.upper()
        self.endpoint = endpoint
        self.error_body = error_body
        self.error_json = error_json or {}
        self.code = self.error_json.get('code')
        self.message = (
            self.error_json.get('message')
            or self.error_json.get('detail')
            or self.error_json.get('error')
            or error_body.strip()
        )
        self.details = self.error_json.get('details')
        self.hint = self.error_json.get('hint')
        super().__init__(self._build_message())

    def _build_message(self) -> str:
        parts = [f"PostgREST HTTP {self.status_code} : {self.reason}"]
        if self.code:
            parts.append(f"Code: {self.code}")
        if self.message:
            parts.append(f"Message: {self.message}")
        if self.details:
            parts.append(f"Details: {self.details}")
        if self.hint:
            parts.append(f"Hint: {self.hint}")
        return "\n".join(parts)

    def user_message(self) -> str:
        parts = [
            f"Requête {self.method} {self.endpoint}",
            f"HTTP {self.status_code} {self.reason}",
        ]
        if self.code:
            parts.append(f"Code base/PostgREST: {self.code}")
        if self.message:
            parts.append(f"Message: {self.message}")
        if self.details:
            parts.append(f"Détails: {self.details}")
        if self.hint:
            parts.append(f"Indice: {self.hint}")
        return "\n".join(parts)


class PostgREST:
    """Client PostgREST avec authentification JWT
    
    Compatible avec:
    - PostgREST standalone (http://localhost:3000)
    - PostgREST via Django (http://localhost:8000/api)
    """
    
    def __init__(self, api_base_url: str, mode: PostgRESTMode = PostgRESTMode.DJANGO):
        """
        Initialise le client PostgREST
        
        Args:
            api_base_url: URL de base de l'API PostgREST
                - Standalone: http://localhost:3000
                - Django: http://localhost:8000 ou http://localhost:8000/api
            mode: Mode de PostgREST (STANDALONE ou DJANGO)
        """
        self.api_base_url = api_base_url.rstrip('/')
        self.mode = mode
        self.jwt_token: Optional[str] = None
        self.headers: Dict[str, str] = {}
        self.postgrest_api_url = self.api_base_url
        self.session = requests.Session()

        # Pour Django, normaliser l'URL de proxy vers /api/data
        if mode == PostgRESTMode.DJANGO:
            self.postgrest_api_url = self._normalize_django_postgrest_url()
    
    def _normalize_django_postgrest_url(self) -> str:
        """Retourne l'URL de base Django pour les requêtes PostgREST proxyées."""
        if self.api_base_url.endswith('/api/data/'):
            return self.api_base_url
        if self.api_base_url.endswith('/api/data'):
            return f"{self.api_base_url}/"
        if self.api_base_url.endswith('/api'):
            return f"{self.api_base_url}/data/"
        if '/api' not in self.api_base_url:
             return f"{self.api_base_url}/api/data/"
        return f"{self.api_base_url}/data/"
    
    def set_auth_token(self, token: str):
        """Définit le jeton JWT pour l'authentification"""
        self.jwt_token = token
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def _build_url(self, endpoint: str, params: Optional[Dict[str, str]] = None) -> str:
        """
        Construit l'URL complète pour la requête.
        
        Args:
            endpoint: Endpoint de l'API.
            params: Paramètres de requête optionnels.

        Returns:
            URL complète formatée.
        """
        endpoint = endpoint.strip('/')
        if self.mode == PostgRESTMode.DJANGO:
            if endpoint.startswith('api/data/'):
                endpoint = endpoint[len('api/data/'):]
            elif endpoint.startswith('data/'):
                endpoint = endpoint[len('data/'):]

        base_url = self.postgrest_api_url.rstrip('/')
        # Pour éviter les redirects 301 (HEAD /api/data -> 301, puis GET /api/data/ avec données),
        # ajouter un trailing slash si l'endpoint est vide
        if endpoint:
            url = f"{base_url}/{endpoint}"
        else:
            url = f"{base_url}/"
        if params:
            query_string = urllib.parse.urlencode(params)
            url = f"{url}?{query_string}"
        return url

    def _split_endpoint_params(self, endpoint: str) -> tuple[str, Dict[str, str]]:
        """Sépare un endpoint éventuellement suffixé par des paramètres de requête."""
        endpoint = str(endpoint or "")
        if '?' not in endpoint:
            return endpoint, {}

        path, query = endpoint.split('?', 1)
        parsed = urllib.parse.parse_qs(query, keep_blank_values=True)
        params = {
            key: values[-1] if values else ""
            for key, values in parsed.items()
        }
        return path, params

    def _infer_uuid_conflict_field(self, endpoint: str, payload: List[Dict[str, Any]]) -> Optional[str]:
        """Retourne uuid_<endpoint> si ce champ est présent dans le payload."""
        endpoint_name = endpoint.strip('/').split('/')[-1].lower()
        if not endpoint_name:
            return None

        payload_columns = set()
        for row in payload:
            if isinstance(row, dict):
                payload_columns.update(str(key).lower() for key in row.keys())

        candidates = [f'uuid_{endpoint_name}']
        if endpoint_name.endswith('s'):
            candidates.append(f'uuid_{endpoint_name[:-1]}')

        for candidate in candidates:
            if candidate in payload_columns:
                return candidate
        return None

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        timeout: int = 20,
        show_error_ui: bool = False,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Effectue une requête HTTP vers PostgREST."""
        from .utils import Utils
        
        # Normaliser les UUID dans les données si présentes
        if data:
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        for k, v in item.items():
                            if isinstance(v, str) and ('uuid' in k.lower() or k.lower() == 'id' or 'pg_uuid' in k.lower()):
                                item[k] = Utils.normalize_uuid(v)
            elif isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, str) and ('uuid' in k.lower() or k.lower() == 'id' or 'pg_uuid' in k.lower()):
                        data[k] = Utils.normalize_uuid(v)

        # Normaliser les UUID dans les paramètres (filtres)
        if params:
            for k, v in params.items():
                if isinstance(v, str) and ('.eq.' in v or '.neq.' in v):
                    # Cas spécial pour les filtres PostgREST type col=eq.{uuid}
                    parts = v.split('.', 2)
                    if len(parts) >= 3:
                        op = parts[1]
                        val = parts[2]
                        if 'uuid' in k.lower() or k.lower() == 'id' or 'pg_uuid' in k.lower():
                            params[k] = f"{parts[0]}.{op}.{Utils.normalize_uuid(val)}"
                elif isinstance(v, str) and ('uuid' in k.lower() or k.lower() == 'id' or 'pg_uuid' in k.lower()):
                    params[k] = Utils.normalize_uuid(v)

        url = self._build_url(endpoint, params)
        request_data = json.dumps(data).encode('utf-8') if data is not None else None
        
        # Fusionner les headers globaux avec les headers spécifiques à la requête
        request_headers = self.headers.copy()
        if headers:
            request_headers.update(headers)
        
        # Ajouter Prefer: resolution=merge pour les POST/PATCH/PUT pour gérer les upserts
        if method.upper() in ['POST', 'PATCH', 'PUT'] and 'Prefer' not in request_headers:
            request_headers['Prefer'] = 'resolution=merge'

        try:
            response = self.session.request(
                method.upper(),
                url,
                data=request_data,
                headers=request_headers,
                timeout=timeout,
            )
            response_text = response.text or ""
            if response.status_code >= 400:
                content_type = response.headers.get('Content-Type', '').lower()
                is_html_error = 'text/html' in content_type or bool(
                    re.search(r'<(?:!DOCTYPE|html|head|body)', response_text, re.IGNORECASE)
                )
                if show_error_ui and is_html_error:
                    self._show_django_error(response, url, response_text, method=method)
                error_json = self._parse_error_json(response_text)
                raise PostgRESTError(
                    status_code=response.status_code,
                    reason=response.reason,
                    url=url,
                    method=method,
                    endpoint=endpoint,
                    error_body=response_text,
                    error_json=error_json,
                )
            return json.loads(response_text) if response_text else {}

        except PostgRESTError:
            raise
        except requests.RequestException as exc:
            raise RuntimeError(f"Erreur PostgREST : {exc}") from exc
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8', errors='ignore')
            content_type = e.headers.get('Content-Type', '').lower()
            is_html_error = 'text/html' in content_type or bool(
                re.search(r'<(?:!DOCTYPE|html|head|body)', error_body, re.IGNORECASE)
            )
            if show_error_ui and is_html_error:
                self._show_django_error(e, url, error_body, method=method)
            error_json = self._parse_error_json(error_body)
            raise PostgRESTError(
                status_code=e.code,
                reason=e.reason,
                url=url,
                method=method,
                endpoint=endpoint,
                error_body=error_body,
                error_json=error_json,
            ) from e
        except Exception as exc:
            raise RuntimeError(f"Erreur PostgREST : {exc}") from exc
    
    def _show_django_error(self, http_error, url, error_body, method='GET'):
        """Affiche une erreur Django avec rendu HTML"""
        try:
            from .django_error_viewer import show_django_error

            # Extraire les en-têtes
            headers = dict(getattr(http_error, 'headers', {}) or {})

            # Déterminer si c'est du HTML
            is_html = 'text/html' in headers.get('Content-Type', '').lower()
            if not is_html:
                is_html = bool(re.search(r'<(?:!DOCTYPE|html|head|body)', error_body, re.IGNORECASE))

            html_content = error_body if is_html else ""
            text_content = "" if is_html else error_body

            # Afficher le visionneur
            show_django_error(
                parent=None,
                error_code=getattr(http_error, 'code', getattr(http_error, 'status_code', '')),
                error_reason=getattr(http_error, 'reason', ''),
                html_content=html_content,
                error_message=(error_body if not is_html else ""),
                url=url,
                method=method.upper(),
                headers=headers,
                text_content=text_content
            )
        except Exception:
            # Fallback si django_error_viewer n'est pas disponible
            pass

    @staticmethod
    def _parse_error_json(error_body: str) -> Optional[Dict[str, Any]]:
        try:
            parsed_body = json.loads(error_body)
        except (TypeError, ValueError):
            return None

        if not isinstance(parsed_body, dict):
            return None

        nested_message = parsed_body.get('message')
        if isinstance(nested_message, str):
            try:
                nested_json = json.loads(nested_message)
                if isinstance(nested_json, dict):
                    merged = dict(nested_json)
                    merged.setdefault('proxy_message', nested_message)
                    return merged
            except (TypeError, ValueError):
                pass

        return parsed_body

    def select(
        self,
        table: str,
        select: str = "*",
        filters: Optional[Dict[str, str]] = None,
        order: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_paginate: bool = True,
        page_size: int = 5000
    ) -> List[Dict[str, Any]]:
        """
        Récupère des enregistrements d'une table avec support optionnel de la pagination automatique.
        
        Args:
            table: Nom de la table.
            select: Colonnes à sélectionner.
            filters: Filtres optionnels.
            order: Tri (ex: "id.asc").
            limit: Limite globale.
            offset: Offset initial.
            auto_paginate: Si True, récupère toutes les pages jusqu'à la limite.
            page_size: Taille de chaque page pour la pagination.
        
        Returns:
            Liste consolidée des enregistrements.
        """
        all_data = []
        current_offset = offset or 0
        remaining_limit = limit
        
        while True:
            params = {'select': select}
            if filters:
                params.update(filters)
            if order:
                params['order'] = order

            # Calculer la limite pour cette page
            current_limit = page_size
            if remaining_limit is not None:
                current_limit = min(page_size, remaining_limit)

            params['limit'] = str(current_limit)
            params['offset'] = str(current_offset)

            result = self._make_request('GET', table, params=params, show_error_ui=True)
            page_data = result if isinstance(result, list) else [result] if result else []

            if not page_data:
                break

            all_data.extend(page_data)

            # Arrêter si on a atteint la limite globale demandée ou si on n'a plus de données
            if not auto_paginate or len(page_data) < current_limit:
                break

            current_offset += len(page_data)
            if remaining_limit is not None:
                remaining_limit -= len(page_data)
                if remaining_limit <= 0:
                    break

        return all_data
    
    def insert(
        self,
        table: str,
        data: Dict[str, Any] | List[Dict[str, Any]],
        upsert: bool = False,
        on_conflict: Optional[str] = None,
        show_error_ui: bool = True
    ):
        """
        Insère ou met à jour un ou plusieurs enregistrements.
        
        Args:
            table: Nom de la table.
            data: Données (dict ou liste de dicts).
            upsert: Si True, met à jour les enregistrements existants (basé sur la PK).
            on_conflict: Champ(s) uniques à utiliser pour l'upsert PostgREST.
        
        Returns:
            Données traitées.
        """
        payload = data if isinstance(data, list) else [data]
        headers = {}
        endpoint, params = self._split_endpoint_params(table)
        if upsert:
            # Header PostgREST pour support Upsert
            headers['Prefer'] = 'resolution=merge-duplicates'
            conflict_field = on_conflict or params.get('on_conflict') or self._infer_uuid_conflict_field(endpoint, payload)
            if conflict_field:
                params['on_conflict'] = conflict_field

        return self._make_request('POST', endpoint, params=params or None, data=payload, show_error_ui=show_error_ui, headers=headers)
    
    def update(
        self,
        table: str,
        data: Dict[str, Any],
        filters: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Met à jour des enregistrements
        
        Args:
            table: Nom de la table
            data: Données à mettre à jour
            filters: Filtres pour identifier les enregistrements
        
        Returns:
            Enregistrements mis à jour
        """
        return self._make_request('PATCH', table, params=filters, data=data, show_error_ui=True)
    
    def delete(self, table: str, filters: Dict[str, str]):
        """
        Supprime des enregistrements
        
        Args:
            table: Nom de la table
            filters: Filtres pour identifier les enregistrements
        
        Returns:
            Réponse du serveur
        """
        return self._make_request('DELETE', table, params=filters, show_error_ui=True)
    
    def call_rpc(
        self,
        function_name: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Appelle une fonction RPC PostgREST
        
        Args:
            function_name: Nom de la fonction
            params: Paramètres de la fonction
        
        Returns:
            Résultat de la fonction
        """
        return self._make_request('POST', f'rpc/{function_name}', data=params or {}, show_error_ui=True)

    def fetch_schema(self) -> Dict[str, Any]:
        """
        Récupère le schéma complet de l'API (OpenAPI / Root endpoint).

        Returns:
            Dict contenant les tables, vues et fonctions disponibles.
        """
        return self._make_request('GET', '', show_error_ui=True)

    def verify_token(self) -> bool:
        """Vérifie que le jeton actuel est accepté par le serveur via une requête HEAD légère sur la racine API."""
        if not self.jwt_token:
            return False
        try:
            # Requête HEAD sur la racine API pour vérifier le token sans charger aucune donnée
            self._make_request('HEAD', '', show_error_ui=False, timeout=5)
            return True
        except RuntimeError as exc:
            message = str(exc)
            if 'HTTP 401' in message or 'HTTP 403' in message:
                return False
            # Autres erreurs = pas de connexion
            return False
        except Exception:
            return False

    # Versions avec support UI pour les erreurs
    def select_with_ui(
        self,
        table: str,
        select: str = "*",
        filters: Optional[Dict[str, str]] = None,
        order: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Récupère des enregistrements avec affichage UI des erreurs Django

        Args:
            table: Nom de la table
            select: Colonnes à sélectionner (par défaut *)
            filters: Filtres (ex: {"id": "eq.5", "name": "ilike.*foo*"})
            order: Ordre (ex: "id.desc")
            limit: Limite d'enregistrements
            offset: Offset pour pagination

        Returns:
            Liste des enregistrements
        """
        params = {'select': select}

        if filters:
            params.update(filters)

        if order:
            params['order'] = order

        if limit:
            params['limit'] = str(limit)

        if offset:
            params['offset'] = str(offset)

        try:
            result = self._make_request('GET', table, params=params, show_error_ui=True)
            return result if isinstance(result, list) else [result] if result else []
        except RuntimeError as e:
            raise

    def insert_with_ui(self, table: str, data: Dict[str, Any] | List[Dict[str, Any]]):
        """
        Insère des enregistrements avec affichage UI des erreurs Django

        Args:
            table: Nom de la table
            data: Données à insérer (dict ou liste de dicts)

        Returns:
            Données insérées
        """
        payload = data if isinstance(data, list) else [data]
        try:
            return self._make_request('POST', table, data=payload, show_error_ui=True)
        except RuntimeError as e:
            raise

    def update_with_ui(
        self,
        table: str,
        data: Dict[str, Any],
        filters: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Met à jour des enregistrements avec affichage UI des erreurs Django

        Args:
            table: Nom de la table
            data: Données à mettre à jour
            filters: Filtres pour identifier les enregistrements

        Returns:
            Enregistrements mis à jour
        """
        try:
            return self._make_request('PATCH', table, params=filters, data=data, show_error_ui=True)
        except RuntimeError as e:
            raise

    def delete_with_ui(self, table: str, filters: Dict[str, str]):
        """
        Supprime des enregistrements avec affichage UI des erreurs Django

        Args:
            table: Nom de la table
            filters: Filtres pour identifier les enregistrements

        Returns:
            Réponse du serveur
        """
        try:
            return self._make_request('DELETE', table, params=filters, show_error_ui=True)
        except RuntimeError as e:
            raise

    def call_rpc_with_ui(
        self,
        function_name: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Appelle une fonction RPC PostgREST avec affichage UI des erreurs Django

        Args:
            function_name: Nom de la fonction
            params: Paramètres de la fonction

        Returns:
            Résultat de la fonction
        """
        try:
            return self._make_request('POST', f'rpc/{function_name}', data=params or {}, show_error_ui=True)
        except RuntimeError as e:
            raise


class PostgRESTAuthenticator:
    """Gère l'authentification avec un backend JWT
    
    Compatible avec:
    - PostgREST standalone (http://localhost:3000)
    - PostgREST via Django (http://localhost:8000/api)
    """
    
    def __init__(self, api_base_url: str, mode: PostgRESTMode = PostgRESTMode.STANDALONE):
        """
        Initialise l'authentificateur
        
        Args:
            api_base_url: URL de base de l'API
            mode: Mode de PostgREST (STANDALONE ou DJANGO)
        """
        self.api_base_url = api_base_url.rstrip('/')
        self.mode = mode
        self.auth_api_url = self.api_base_url
        
        # Pour Django, normaliser l'URL d'authentification vers /api
        if mode == PostgRESTMode.DJANGO:
            self.auth_api_url = self._normalize_django_auth_url()
    
    def _normalize_django_auth_url(self) -> str:
        """Retourne l'URL d'authentification Django (sans /data)."""
        if self.api_base_url.endswith('/api/data'):
            return self.api_base_url[:-len('/data')]
        if self.api_base_url.endswith('/api'):
            return self.api_base_url
        if '/api' not in self.api_base_url:
            return f"{self.api_base_url}/api"
        return self.api_base_url 

    def authenticate(
        self,
        username: str,
        password: str,
        login_endpoint: Optional[str] = None
    ) -> str:
        """
        Authentifie un utilisateur et récupère un jeton JWT
        
        Args:
            username: Nom d'utilisateur ou email
            password: Mot de passe
            login_endpoint: Endpoint de connexion personnalisé
                - Par défaut pour STANDALONE: 'auth/signin'
                - Par défaut pour DJANGO: 'api/auth/signin' ou 'auth/token'
        
        Returns:
            Jeton JWT
        
        Raises:
            RuntimeError: Si l'authentification échoue
        """
        # Endpoint par défaut selon le mode
        if login_endpoint is None:
            if self.mode == PostgRESTMode.DJANGO:
                login_endpoint = 'login/'  # Sera ajouté à /api automatiquement
            else:
                login_endpoint = 'auth/signin'
        
        login_endpoint = str(login_endpoint).lstrip('/')
        login_url = f"{self.auth_api_url}/{login_endpoint}"
        
        # Format du payload selon le mode
        if self.mode == PostgRESTMode.DJANGO:
            # Django utilise généralement 'username' ou 'email'
            payload = {
                'username': username,
                'password': password
            }
        else:
            # PostgREST standalone utilise 'email'
            payload = {
                'email': username,
                'password': password
            }
        
        payload_json = json.dumps(payload).encode('utf-8')
        
        request = urllib.request.Request(
            login_url,
            data=payload_json,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                response_text = response.read().decode('utf-8')
                response_data = json.loads(response_text)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8', errors='ignore')
            if self.mode == PostgRESTMode.DJANGO:
                try:
                    from django_error_viewer import show_django_error

                    show_django_error(
                        parent=None,
                        error_code=e.code,
                        error_reason=e.reason,
                        html_content=error_body,
                        url=login_url,
                        method='POST',
                        headers=dict(e.headers),
                        text_content=error_body
                    )
                except Exception:
                    pass
            raise RuntimeError(
                f"Authentification échouée: {e.code} {e.reason}\n{error_body}"
            ) from e
        except Exception as exc:
            raise RuntimeError(f"Erreur d'authentification: {exc}") from exc
        
        # Extraire le jeton selon le format de réponse
        # PostgREST standalone: {access_token: "..."}
        # Django Token: {token: "..."}
        # Django JWT: {access: "...", refresh: "..."}
        token = (
            response_data.get('access_token') or
            response_data.get('access') or
            response_data.get('token')
        )
        
        if not token:
            raise RuntimeError('Réponse invalide: jeton JWT introuvable')
        
        return token
