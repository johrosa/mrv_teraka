# -*- coding: utf-8 -*-
"""
Installation opportuniste des dépendances Python optionnelles du plugin.
"""

import importlib.util
import site
import subprocess
import sys


FAST_GEO_PACKAGES = (
    ("pyogrio", "pyogrio"),
    ("geopandas", "geopandas"),
    ("shapely", "shapely"),
    ("pyarrow", "pyarrow"),
)


def missing_fast_geo_packages():
    return [
        package_name
        for module_name, package_name in FAST_GEO_PACKAGES
        if importlib.util.find_spec(module_name) is None
    ]


def install_missing_fast_geo_packages():
    missing = missing_fast_geo_packages()
    if not missing:
        return {
            "success": True,
            "message": "Dépendances pyogrio déjà disponibles.",
            "installed": [],
        }

    _ensure_pip()

    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        "--prefer-binary",
    ] + missing
    if _should_install_to_user_site():
        command.insert(5, "--user")

    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False
        )
        if process.returncode == 0:
            importlib.invalidate_caches()
            return {
                "success": True,
                "message": "Dépendances pyogrio installées: {}".format(", ".join(missing)),
                "installed": missing,
            }

        output = (process.stderr or process.stdout or "").strip()
        return {
            "success": False,
            "message": "Installation pyogrio échouée: {}".format(output[-1000:] or process.returncode),
            "installed": [],
        }
    except Exception as exc:
        return {
            "success": False,
            "message": "Installation pyogrio échouée: {}".format(exc),
            "installed": [],
        }


def _ensure_pip():
    process = subprocess.run(
        [sys.executable, "-m", "pip", "--version"],
        capture_output=True,
        text=True,
        check=False
    )
    if process.returncode == 0:
        return

    subprocess.run(
        [sys.executable, "-m", "ensurepip", "--upgrade"],
        capture_output=True,
        text=True,
        check=False
    )


def _should_install_to_user_site():
    if hasattr(sys, "real_prefix") or sys.prefix != getattr(sys, "base_prefix", sys.prefix):
        return False
    return bool(getattr(site, "ENABLE_USER_SITE", False))
