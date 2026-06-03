# -*- coding: utf-8 -*-
import json
import requests
import os

class MerginAPIClient:
    """Client natif pour l'API Mergin Maps (sans dépendance externe)."""

    def __init__(self, base_url="https://app.merginmaps.com/api/v1"):
        self.base_url = base_url
        self.token = None
        self.username = None

    def login(self, username, password):
        """Authentification et récupération du jeton JWT."""
        url = f"{self.base_url}/auth/login"
        payload = {"username": username, "password": password}
        response = requests.post(url, json=payload)

        if response.status_code == 200:
            data = response.json()
            self.token = data.get('token')
            self.username = username
            return True
        return False

    def create_project(self, namespace, project_name):
        """Crée un nouveau projet sur Mergin Maps."""
        url = f"{self.base_url}/projects"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {
            "namespace": namespace,
            "name": project_name,
            "is_public": False
        }
        response = requests.post(url, json=payload, headers=headers)
        return response.status_code == 201

    def upload_file(self, namespace, project_name, file_path, remote_path):
        """Upload d'un fichier vers un projet Mergin."""
        url = f"{self.base_url}/projects/{namespace}/{project_name}/files"
        headers = {"Authorization": f"Bearer {self.token}"}

        with open(file_path, 'rb') as f:
            files = {'file': (remote_path, f)}
            response = requests.post(url, headers=headers, files=files)
        return response.status_code in [200, 201]

    def download_project(self, namespace, project_name, target_dir):
        """Télécharge l'intégralité d'un projet localement."""
        url = f"{self.base_url}/projects/{namespace}/{project_name}/zip"
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(url, headers=headers, stream=True)

        if response.status_code == 200:
            zip_path = os.path.join(target_dir, f"{project_name}.zip")
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return zip_path
        return None
