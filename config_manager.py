# -*- coding: utf-8 -*-
"""
Configuration manager for MRV Teraka plugin.

Centralizes configuration loading from:
1. Environment variables (highest priority)
2. plugin_config.json user config file
3. Built-in defaults (lowest priority)

Provides cross-platform path handling for config/projects/exports/logs.
"""

import os
import sys
import json
import platform
from pathlib import Path


class ConfigManager:
    """Manages plugin configuration and paths."""
    
    # Default configuration
    DEFAULTS = {
        'api': {
            'django_url': 'http://localhost:8000',
            'postgrest_url': 'http://localhost:3000',
            'timeout_seconds': 30,
        },
        'features': {
            'enable_offline_mode': False,
            'auto_sync_interval_minutes': 60,
        }
    }
    
    _instance = None
    _config = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance
    
    @staticmethod
    def get_platform_config_dir():
        """Get the platform-specific config directory.
        
        Returns:
            str: Path to Teraka config directory (cross-platform)
                Windows: %LOCALAPPDATA%/Teraka/
                Linux/Mac: ~/.config/Teraka/
        """
        # Allow explicit override
        if os.getenv('TERAKA_CONFIG_DIR'):
            return os.path.expanduser(os.getenv('TERAKA_CONFIG_DIR'))

        if sys.platform == 'win32':
            # Windows: Use LOCALAPPDATA (not hidden AppData\Roaming)
            base = os.getenv('LOCALAPPDATA', os.path.expanduser('~\\AppData\\Local'))
        else:
            # Linux/Mac: Use ~/.config
            base = os.path.expanduser('~/.config')
        
        config_dir = os.path.join(base, 'Teraka')
        return config_dir
    
    @staticmethod
    def get_config_dir():
        """Returns writable config directory, creating if needed."""
        config_dir = ConfigManager.get_platform_config_dir()
        os.makedirs(config_dir, exist_ok=True)
        return config_dir
    
    @staticmethod
    def get_projects_dir():
        """Returns projects directory (for user QGIS projects)."""
        config_dir = ConfigManager.get_config_dir()
        projects_dir = os.path.join(config_dir, 'projects')
        os.makedirs(projects_dir, exist_ok=True)
        return projects_dir
    
    @staticmethod
    def get_user_default_project_path():
        """Returns the path for the accessible default QGIS project file."""
        projects_dir = ConfigManager.get_projects_dir()
        return os.path.join(projects_dir, 'Q_v17_7_7_ITASY2026_WP.qgz')
    
    @staticmethod
    def get_exports_dir():
        """Returns exports directory (for CSV, Shapefile, etc.)."""
        config_dir = ConfigManager.get_config_dir()
        exports_dir = os.path.join(config_dir, 'exports')
        os.makedirs(exports_dir, exist_ok=True)
        return exports_dir
    
    @staticmethod
    def get_logs_dir():
        """Returns logs directory."""
        config_dir = ConfigManager.get_config_dir()
        logs_dir = os.path.join(config_dir, 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        return logs_dir
    
    @staticmethod
    def get_cache_dir():
        """Returns cache directory (for temporary files)."""
        config_dir = ConfigManager.get_config_dir()
        cache_dir = os.path.join(config_dir, 'cache')
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir
    
    @staticmethod
    def load_config():
        """Load configuration from multiple sources.
        
        Priority order:
        1. Environment variables (TERAKA_*)
        2. User config file (~/.config/Teraka/plugin_config.json)
        3. Built-in defaults
        
        Returns:
            dict: Merged configuration
        """
        config = ConfigManager.DEFAULTS.copy()
        
        # Try to load user config file
        config_dir = ConfigManager.get_config_dir()
        config_file = os.path.join(config_dir, 'plugin_config.json')
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    # Deep merge
                    config = ConfigManager._merge_dicts(config, user_config)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load config file {config_file}: {e}")
        
        # Override with environment variables
        if os.getenv('TERAKA_API_URL'):
            config['api']['django_url'] = os.getenv('TERAKA_API_URL')
        
        if os.getenv('TERAKA_POSTGREST_URL'):
            config['api']['postgrest_url'] = os.getenv('TERAKA_POSTGREST_URL')
        
        if os.getenv('TERAKA_API_TIMEOUT'):
            try:
                config['api']['timeout_seconds'] = int(os.getenv('TERAKA_API_TIMEOUT'))
            except ValueError:
                pass
        
        return config
    
    @staticmethod
    def _merge_dicts(base, override):
        """Recursively merge override dict into base dict."""
        result = base.copy()
        for key, value in override.items():
            if isinstance(value, dict) and key in result and isinstance(result[key], dict):
                result[key] = ConfigManager._merge_dicts(result[key], value)
            else:
                result[key] = value
        return result
    
    @staticmethod
    def get_config():
        """Get cached configuration (singleton)."""
        if ConfigManager._config is None:
            ConfigManager._config = ConfigManager.load_config()
        return ConfigManager._config
    
    @staticmethod
    def reload_config():
        """Reload configuration (e.g., after user edits plugin_config.json)."""
        ConfigManager._config = ConfigManager.load_config()
        return ConfigManager._config
    
    @staticmethod
    def get_api_url():
        """Get Django API base URL."""
        return ConfigManager.get_config()['api']['django_url']
    
    @staticmethod
    def get_postgrest_url():
        """Get PostgREST API base URL."""
        return ConfigManager.get_config()['api']['postgrest_url']
    
    @staticmethod
    def get_api_timeout():
        """Get API timeout in seconds."""
        return ConfigManager.get_config()['api']['timeout_seconds']
    
    @staticmethod
    def create_config_template():
        """Create a template plugin_config.json if it doesn't exist.
        
        Returns:
            str: Path to created/existing config file
        """
        config_dir = ConfigManager.get_config_dir()
        config_file = os.path.join(config_dir, 'plugin_config.json')
        
        if not os.path.exists(config_file):
            template = {
                'api': {
                    'django_url': 'http://localhost:8000',
                    'postgrest_url': 'http://localhost:3000',
                    'timeout_seconds': 30
                },
                'features': {
                    'enable_offline_mode': False,
                    'auto_sync_interval_minutes': 60
                },
                '_comment': 'Edit this file to configure MRV Teraka. Override with env vars: TERAKA_API_URL, TERAKA_POSTGREST_URL, TERAKA_API_TIMEOUT'
            }
            
            try:
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(template, f, indent=2, ensure_ascii=False)
            except IOError as e:
                print(f"Warning: Could not create config file {config_file}: {e}")
        
        return config_file


# Export convenience functions
def get_config_dir():
    return ConfigManager.get_config_dir()

def get_projects_dir():
    return ConfigManager.get_projects_dir()

def get_exports_dir():
    return ConfigManager.get_exports_dir()

def get_logs_dir():
    return ConfigManager.get_logs_dir()

def get_api_url():
    return ConfigManager.get_api_url()

def get_postgrest_url():
    return ConfigManager.get_postgrest_url()
