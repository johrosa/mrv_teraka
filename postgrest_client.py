# -*- coding: utf-8 -*-
"""
PostgREST Client pour le plugin MrvTeraka
Fournit une abstraction pour interagir avec une API PostgREST
"""

import json
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional


class PostgREST:
    """Client PostgREST avec authentification JWT"""
    
    def __init__(self, api_base_url: str):
        """
        Initialise le client PostgREST
        
        Args:
            api_base_url: URL de base de l'API PostgREST (ex: http://localhost:3000)
        """
        self.api_base_url = api_base_url.rstrip('/')
        self.jwt_token: Optional[str] = None
        self.headers: Dict[str, str] = {}
    
    def set_auth_token(self, token: str):
        """Définit le jeton JWT pour l'authentification"""
        self.jwt_token = token
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        timeout: int = 20
    ) -> Dict[str, Any]:
        """
        Effectue une requête HTTP vers PostgREST
        
        Args:
            method: Méthode HTTP (GET, POST, PATCH, DELETE)
            endpoint: Endpoint PostgREST (ex: rpc/function_name ou table_name)
            params: Paramètres de requête QueryString
            data: Données à envoyer (pour POST/PATCH)
            timeout: Timeout en secondes
        
        Returns:
            Réponse JSON parsée
        
        Raises:
            RuntimeError: Si la requête échoue
        """
        # Construire l'URL
        url = f"{self.api_base_url}/{endpoint.lstrip('/')}"
        
        # Ajouter les querystring s'ils existent
        if params:
            query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            url = f"{url}?{query_string}"
        
        # Préparer les données
        request_data = None
        if data is not None:
            request_data = json.dumps(data).encode('utf-8')
        
        # Faire la requête
        try:
            request = urllib.request.Request(
                url,
                data=request_data,
                headers=self.headers,
                method=method.upper(),
            )
            
            with urllib.request.urlopen(request, timeout=timeout) as response:
                response_text = response.read().decode('utf-8')
                if response_text:
                    return json.loads(response_text)
                return {}
                
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8', errors='ignore')
            raise RuntimeError(
                f"PostgREST HTTP {e.code} : {e.reason}\n{error_body}"
            ) from e
        except Exception as exc:
            raise RuntimeError(f"Erreur PostgREST : {exc}") from exc
    
    def select(
        self,
        table: str,
        select: str = "*",
        filters: Optional[Dict[str, str]] = None,
        order: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Récupère des enregistrements d'une table
        
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
        
        result = self._make_request('GET', table, params=params)
        return result if isinstance(result, list) else [result] if result else []
    
    def insert(self, table: str, data: Dict[str, Any] | List[Dict[str, Any]]):
        """
        Insère un ou plusieurs enregistrements
        
        Args:
            table: Nom de la table
            data: Données à insérer (dict ou liste de dicts)
        
        Returns:
            Données insérées
        """
        # Normaliser en liste
        payload = data if isinstance(data, list) else [data]
        return self._make_request('POST', table, data=payload)
    
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
        return self._make_request('PATCH', table, params=filters, data=data)
    
    def delete(self, table: str, filters: Dict[str, str]):
        """
        Supprime des enregistrements
        
        Args:
            table: Nom de la table
            filters: Filtres pour identifier les enregistrements
        
        Returns:
            Réponse du serveur
        """
        return self._make_request('DELETE', table, params=filters)
    
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
        return self._make_request('POST', f'rpc/{function_name}', data=params or {})


class PostgRESTAuthenticator:
    """Gère l'authentification avec un backend JWT"""
    
    def __init__(self, api_base_url: str):
        """
        Initialise l'authentificateur
        
        Args:
            api_base_url: URL de base de l'API
        """
        self.api_base_url = api_base_url.rstrip('/')
    
    def authenticate(
        self,
        username: str,
        password: str,
        login_endpoint: str = "auth/signin"
    ) -> str:
        """
        Authentifie un utilisateur et récupère un jeton JWT
        
        Args:
            username: Nom d'utilisateur
            password: Mot de passe
            login_endpoint: Endpoint de connexion (peut varier selon le backend)
        
        Returns:
            Jeton JWT
        
        Raises:
            RuntimeError: Si l'authentification échoue
        """
        login_url = f"{self.api_base_url}/{login_endpoint}"
        payload = json.dumps({
            'email': username,  # PostgREST utilise généralement 'email'
            'password': password
        }).encode('utf-8')
        
        request = urllib.request.Request(
            login_url,
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                response_text = response.read().decode('utf-8')
                response_data = json.loads(response_text)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8', errors='ignore')
            raise RuntimeError(
                f"Authentification échouée: {e.code} {e.reason}\n{error_body}"
            ) from e
        except Exception as exc:
            raise RuntimeError(f"Erreur d'authentification: {exc}") from exc
        
        # PostgREST retourne généralement {access_token: "..."}
        # Mais certains backends retournent {token: "..."}
        token = response_data.get('access_token') or response_data.get('token')
        if not token:
            raise RuntimeError('Réponse invalide: jeton JWT introuvable')
        
        return token

