"""Default paths and data resolution for gaia-twins.

The package ships a pre-binned AMBRE grid (see ``gaia_twins/data/``) so the
library works out of the box after ``pip install`` without needing the full
~41 GB AMBRE archive. This module centralises the resolution of those defaults
so a single point of truth drives the generator, the loader and the CLI.

All the paths below can be overridden through environment variables, which is
handy when a user keeps the full AMBRE grid (or the cache) elsewhere.
"""

from __future__ import annotations

import importlib.resources
import os
from pathlib import Path

#: Name of the pre-binned AMBRE grid shipped inside the package.
DEFAULT_AMBRE_BINNED = "ambre_complete_binned_10.0A.parquet"

#: Environment-variable overrides.
ENV_AMBRE_DIR = "GAIA_TWINS_AMBRE_DIR"
ENV_DATA_DIR = "GAIA_TWINS_DATA_DIR"
ENV_CACHE_DIR = "GAIA_TWINS_CACHE_DIR"

#: Name of the data subpackage holding the packaged resources.
_PKG = "gaia_twins.data"


def get_default_ambre_data_path() -> Path:
    """Return the path of the pre-binned AMBRE grid shipped with the package.

    Uses :func:`importlib.resources.files` so it works for regular (wheel) and
    editable installs alike, with a ``FileNotFoundError``-free fallback to the
    directory next to this source file.
    """
    try:
        ref = importlib.resources.files(_PKG).joinpath(DEFAULT_AMBRE_BINNED)
        # For normalised / editable installs ``files()`` returns a real Path;
        # for zipped installs it returns a Traversable we need to materialise.
        if isinstance(ref, Path):
            return Path(ref)
        with importlib.resources.as_file(ref) as resolved:
            return Path(resolved)
    except (ImportError, ModuleNotFoundError, FileNotFoundError, TypeError):
        return Path(__file__).resolve().parent / DEFAULT_AMBRE_BINNED


def get_default_ambre_dir() -> Path:
    """Return the default AMBRE data directory.

    Resolution order:
    1. ``GAIA_TWINS_AMBRE_DIR`` environment variable (full grid of ZIPs on disk).
    2. ``GAIA_TWINS_DATA_DIR`` environment variable.
    3. The package's bundled ``gaia_twins/data`` directory (holding the
       pre-binned grid).
    """
    for env in (ENV_AMBRE_DIR, ENV_DATA_DIR):
        value = os.environ.get(env)
        if value:
            return Path(value)
    return Path(__file__).resolve().parent


def get_default_cache_dir() -> Path:
    """Return the user-level cache directory for persisted data.

    Used by default to store the Gaia astrophysical-parameters parquet cache
    and any processed AMBRE grid, so newly fetched data is kept across runs.

    Resolution order:
    1. ``GAIA_TWINS_CACHE_DIR`` environment variable.
    2. ``$XDG_CACHE_HOME/gaia-twins`` (Linux / macOS).
    3. ``~/.cache/gaia-twins``.
    """
    env = os.environ.get(ENV_CACHE_DIR)
    if env:
        return Path(env)
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".cache"
    return base / "gaia-twins"
