"""Data caching utilities for gaia-twins.

Provides a small ``CacheManager`` helper to persist processed AMBRE grids
and generated spectra to disk (pickle / parquet), so that long-running
preparations (e.g. binning the ~13k AMBRE spectra) only need to run once.
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any, Optional, Union

import pandas as pd


class CacheManager:
    """Load and save processed data artifacts (pickle, a small subset of pandas output).

    Parameters
    ----------
    cache_dir : str or Path
        Directory where cache files are stored. Created if missing.
    """

    def __init__(self, cache_dir: Union[str, Path, None] = None):
        self.cache_dir = Path(cache_dir) if cache_dir is not None else None
        if self.cache_dir is not None:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------
    def _resolve(self, key: str) -> Path:
        """Build an absolute cache path for ``key`` (a filename or raw key)."""
        name = Path(key)
        # A bare identifier is stored inside cache_dir.
        if self.cache_dir is not None and not name.is_absolute():
            path = self.cache_dir / name
        else:
            path = name
        return path

    # ------------------------------------------------------------------
    # Generic pickle-based cache
    # ------------------------------------------------------------------
    def get_path(self, key: str) -> Path:
        """Return the resolved path for a cache key without requiring existence."""
        return self._resolve(key)

    def exists(self, key: str) -> bool:
        """Return True if a cached artifact exists for ``key``."""
        return self._resolve(key).exists()

    def save(self, key: str, obj: Any) -> str:
        """Serialize ``obj`` to pickle at ``key`` and return the written path."""
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as fh:
            pickle.dump(obj, fh)
        return str(path)

    def load(self, key: str, default: Any = None) -> Any:
        """Load a pickled object at ``key``, returning ``default`` if missing."""
        path = self._resolve(key)
        if not path.exists():
            return default
        with open(path, "rb") as fh:
            return pickle.load(fh)

    # ------------------------------------------------------------------
    # DataFrame-specialised helpers (pandas)
    # ------------------------------------------------------------------
    def save_dataframe(self, key: str, df: pd.DataFrame, format: str = "parquet") -> str:
        """Save a DataFrame to parquet (or pickle) and return the written path.

        Parameters
        ----------
        key : str
            Cache key / filename.
        df : pd.DataFrame
            Data to persist.
        format : str
            ``"parquet"`` (default) or ``"pickle"``.

        Raises
        ------
        ValueError
            If ``format`` is unsupported.
        """
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)

        fmt = format.lower()
        if fmt == "parquet":
            df.to_parquet(path)
        elif fmt in ("pickle", "pkl"):
            df.to_pickle(path)
        else:
            raise ValueError(f"Unsupported dataframe cache format: {format}")
        return str(path)

    def load_dataframe(self, key: str, format: Optional[str] = None) -> pd.DataFrame:
        """Load a DataFrame from cache.

        Parameters
        ----------
        key : str
            Cache key / filename.
        format : str, optional
            ``"parquet"`` or ``"pickle"``. If None, inferred from the extension
            (falling back to parquet).
        """
        path = self._resolve(key)
        if not path.exists():
            raise FileNotFoundError(f"Cache file not found: {path}")

        fmt = (format or path.suffix.lstrip(".")).lower()
        if fmt == "parquet":
            return pd.read_parquet(path)
        if fmt in ("pickle", "pkl"):
            return pd.read_pickle(path)
        raise ValueError(f"Unsupported dataframe cache format: {fmt}")

    def clear(self, pattern: str = "*") -> int:
        """Delete cached files matching ``pattern`` inside ``cache_dir``.

        Returns the number of removed files.
        """
        if self.cache_dir is None:
            return 0
        removed = 0
        for path in self.cache_dir.glob(pattern):
            if path.is_file():
                path.unlink()
                removed += 1
        return removed
