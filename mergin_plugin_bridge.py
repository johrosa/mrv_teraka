# -*- coding: utf-8 -*-
"""
Bridge to the official Mergin Maps QGIS plugin.

MrvTeraka should not keep a second Mergin login state when the official plugin
already owns the authenticated session inside QGIS.
"""

import os
import re

from qgis.PyQt.QtCore import QSettings


class MerginPluginBridge:
    """Small adapter around the official Mergin Maps QGIS plugin."""

    def __init__(self):
        self.last_error = ""

    def plugin(self):
        """Return the loaded official Mergin plugin instance, if available."""
        self.last_error = ""
        try:
            from qgis.utils import plugins
        except Exception as exc:
            self.last_error = str(exc)
            return None

        plugin = plugins.get("Mergin") or plugins.get("mergin")
        if plugin is None:
            self.last_error = "Le plugin officiel Mergin Maps n'est pas charge dans QGIS."
        return plugin

    def client(self):
        """
        Return an authenticated MerginClient from the official plugin.

        Prefer the live plugin instance. If it is loaded but has not initialized
        its client yet, ask it to create its manager/client using its saved QGIS
        auth configuration.
        """
        self.last_error = ""
        plugin = self.plugin()
        if plugin is None:
            return None

        mc = getattr(plugin, "mc", None)
        if mc is None and hasattr(plugin, "create_manager"):
            try:
                plugin.create_manager()
                mc = getattr(plugin, "mc", None)
            except Exception as exc:
                self.last_error = str(exc)

        if mc is None:
            try:
                from Mergin.utils_auth import create_mergin_client

                mc = create_mergin_client()
                plugin.mc = mc
            except Exception as exc:
                self.last_error = str(exc)
                return None

        return mc

    def is_connected(self):
        """Return True when a usable official Mergin client is available."""
        mc = self.client()
        if mc is None:
            return False

        if getattr(mc, "_user_info", None):
            return True

        try:
            mc.user_info()
            return True
        except Exception as exc:
            err_msg = str(exc).lower()
            # If it's a network issue, assume we are connected but offline
            if any(k in err_msg for k in ["connection", "timeout", "unreachable", "refused"]):
                return True
            self.last_error = str(exc)
            return False

    def namespace(self):
        """Return the active Mergin workspace/name where new projects go."""
        plugin = self.plugin()
        workspace = getattr(plugin, "current_workspace", None) if plugin else None
        if isinstance(workspace, dict) and workspace.get("name"):
            return workspace["name"]

        mc = self.client()
        if mc is None:
            return None

        try:
            return mc.username()
        except Exception:
            pass

        user_info = getattr(mc, "_user_info", None) or {}
        return user_info.get("username") or user_info.get("name")

    def connection_label(self):
        """Human readable Mergin connection label."""
        namespace = self.namespace()
        if namespace:
            return "Mergin Maps connecte: {}".format(namespace)

        if self.is_connected():
            return "Mergin Maps connecte (mode hors-ligne)"

        if self.last_error:
            return "Mergin Maps non connecte: {}".format(self.last_error)
        return "Mergin Maps non connecte"

    def create_project_and_push(self, project_name, project_dir, is_public=False):
        """Create a Mergin Maps project and upload the local mission folder."""
        mc = self.client()
        namespace = self.namespace()
        if mc is None or not namespace:
            raise RuntimeError(self.connection_label())

        full_project_name = "{}/{}".format(namespace, project_name)
        mc.create_project_and_push(full_project_name, project_dir, is_public=is_public)
        self.register_local_project(full_project_name, project_dir, getattr(mc, "url", ""))
        return full_project_name

    def default_projects_dir(self):
        """Return the parent folder used by Mergin Maps for local projects."""
        settings = QSettings()
        base_dir = settings.value("Mergin/lastUsedDownloadDir")
        if not base_dir:
            base_dir = os.path.join(os.path.expanduser("~"), "Mergin Projects")
        return base_dir

    def safe_project_name(self, name):
        """Return a filesystem/server friendly Mergin project name."""
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", name.strip())
        safe = safe.strip("._-")
        return safe or "mrv_teraka_project"

    def new_project_dir(self, project_name):
        """Create and return a unique local project directory."""
        settings = QSettings()
        base_dir = self.default_projects_dir()
        safe_name = self.safe_project_name(project_name)
        os.makedirs(base_dir, exist_ok=True)

        project_dir = os.path.join(base_dir, safe_name)
        suffix = 1
        while os.path.exists(project_dir):
            suffix += 1
            project_dir = os.path.join(base_dir, "{}_{}".format(safe_name, suffix))

        os.makedirs(project_dir, exist_ok=True)
        settings.setValue("Mergin/lastUsedDownloadDir", base_dir)
        return project_dir, os.path.basename(project_dir)

    def register_local_project(self, full_project_name, project_dir, server_url=""):
        """Register a local project path the same way the official plugin does."""
        settings = QSettings()
        settings.setValue("Mergin/localProjects/{}/path".format(full_project_name), project_dir)
        if server_url:
            settings.setValue("Mergin/localProjects/{}/server".format(full_project_name), server_url.rstrip("/"))

    def list_local_projects(self):
        """Return local Mergin projects registered by the official plugin."""
        settings = QSettings()
        projects = []
        seen_paths = set()

        for key in settings.allKeys():
            if not key.startswith("Mergin/localProjects/") or not key.endswith("/path"):
                continue
            project_path = settings.value(key)
            if project_path:
                self._append_project(projects, seen_paths, project_path)

        fallback_dirs = [
            settings.value("Mergin/lastUsedDownloadDir"),
            os.path.join(os.path.expanduser("~"), "Mergin Projects"),
        ]
        for base_dir in fallback_dirs:
            if not base_dir or not os.path.isdir(base_dir):
                continue
            for item in os.listdir(base_dir):
                self._append_project(projects, seen_paths, os.path.join(base_dir, item))

        return projects

    def _append_project(self, projects, seen_paths, project_path):
        project_path = os.path.abspath(project_path)
        if project_path in seen_paths or not os.path.isdir(project_path):
            return

        qgis_files = [
            f for f in os.listdir(project_path)
            if f.lower().endswith((".qgs", ".qgz"))
        ]
        if not qgis_files:
            return

        seen_paths.add(project_path)
        projects.append({
            "id": project_path,
            "name": os.path.basename(project_path),
            "project_file": os.path.join(project_path, qgis_files[0]),
        })
