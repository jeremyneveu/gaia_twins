"""Tests for default path / data resolution."""

import pandas as pd
import pytest

from gaia_twins.data.defaults import (
    DEFAULT_AMBRE_BINNED,
    get_default_ambre_data_path,
    get_default_ambre_dir,
    get_default_cache_dir,
)


class TestDefaultPaths:
    def test_bundled_parquet_exists_and_is_valid(self):
        path = get_default_ambre_data_path()
        assert path.exists(), f"Bundled AMBRE grid not found at {path}"
        assert path.name == DEFAULT_AMBRE_BINNED
        # The file must be a usable pre-binned grid.
        df = pd.read_parquet(path)
        required = {"filename", "teff", "logg", "mh", "flux_binned", "wave_binned"}
        assert required <= set(df.columns)
        assert len(df) > 0

    def test_default_ambre_dir_is_data_dir(self):
        path = get_default_ambre_dir()
        assert path.exists()
        assert (path / DEFAULT_AMBRE_BINNED).exists()

    def test_ambre_dir_env_override(self, monkeypatch):
        monkeypatch.setenv("GAIA_TWINS_AMBRE_DIR", "/custom/ambre")
        assert str(get_default_ambre_dir()) == "/custom/ambre"

    def test_data_dir_env_override(self, monkeypatch, tmp_path):
        monkeypatch.setenv("GAIA_TWINS_DATA_DIR", str(tmp_path))
        assert get_default_ambre_dir() == tmp_path

    def test_cache_dir_env_override(self, monkeypatch):
        monkeypatch.setenv("GAIA_TWINS_CACHE_DIR", "/custom/cache")
        assert str(get_default_cache_dir()) == "/custom/cache"

    def test_cache_dir_uses_xdg(self, monkeypatch, tmp_path):
        monkeypatch.delenv("GAIA_TWINS_CACHE_DIR", raising=False)
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
        assert get_default_cache_dir() == tmp_path / "gaia-twins"
