# -*- coding: utf-8 -*-
"""Paramètres de fonctionnement du plugin, indépendants de QGIS."""

from configparser import ConfigParser, Error as ConfigError
from dataclasses import dataclass
from pathlib import Path
import logging


LOGGER = logging.getLogger(__name__)
CONFIG_PATH = Path(__file__).resolve().with_name('config.ini')


@dataclass(frozen=True)
class PluginConfig:
    migration_batch_size: int = 1000
    migration_repeated_error_limit: int = 10
    page_size: int = 5000
    request_timeout: int = 20
    connection_timeout: int = 5
    auth_timeout: int = 15
    connection_check_interval: int = 60


def load_config(path=CONFIG_PATH) -> PluginConfig:
    """Charge le fichier INI; les valeurs absentes/invalides gardent leur défaut."""
    defaults = PluginConfig()
    parser = ConfigParser(interpolation=None)
    try:
        with Path(path).open(encoding='utf-8-sig') as config_file:
            parser.read_file(config_file)
    except FileNotFoundError:
        return defaults
    except (OSError, UnicodeError, ConfigError) as exc:
        LOGGER.warning('Configuration MRV Teraka illisible (%s) : %s', path, exc)
        return defaults

    def positive_int(section, option, default):
        try:
            value = parser.getint(section, option, fallback=default)
            if value <= 0:
                raise ValueError('entier strictement positif attendu')
            return value
        except ValueError:
            LOGGER.warning(
                'Configuration MRV Teraka : [%s] %s invalide; valeur par défaut %s.',
                section, option, default,
            )
            return default

    return PluginConfig(
        migration_batch_size=positive_int('migration', 'batch_size', defaults.migration_batch_size),
        migration_repeated_error_limit=positive_int(
            'migration', 'repeated_error_limit', defaults.migration_repeated_error_limit,
        ),
        page_size=positive_int('postgrest', 'page_size', defaults.page_size),
        request_timeout=positive_int('postgrest', 'request_timeout', defaults.request_timeout),
        connection_timeout=positive_int('postgrest', 'connection_timeout', defaults.connection_timeout),
        auth_timeout=positive_int('postgrest', 'auth_timeout', defaults.auth_timeout),
        connection_check_interval=positive_int(
            'postgrest', 'connection_check_interval', defaults.connection_check_interval,
        ),
    )


CONFIG = load_config()
