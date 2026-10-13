"""Tests for the synthetic spectrum generator."""

import numpy as np
import pandas as pd
import pytest

from gaia_twins.data.defaults import DEFAULT_AMBRE_BINNED
from gaia_twins.src.spectrum_generator import SyntheticSpectrumGenerator


class TestSyntheticSpectrumGenerator:
    def test_invalid_interpolation_method_raises(self):
        # Method validation happens before the AMBRE directory is touched.
        with pytest.raises(ValueError, match="interpolation_method"):
            SyntheticSpectrumGenerator(
                ambre_dir="/nonexistent", interpolation_method="bogus"
            )

    def test_knn_maps_to_nearest(self, tmp_path):
        (tmp_path / "leaf.zip").touch()
        gen = SyntheticSpectrumGenerator(
            ambre_dir=str(tmp_path), interpolation_method="knn", cache_dir=False
        )
        assert gen.interpolation_method == "nearest"

    def test_generate_spectrum_before_prepare_raises(self, tmp_path):
        (tmp_path / "leaf.zip").touch()
        gen = SyntheticSpectrumGenerator(ambre_dir=str(tmp_path), cache_dir=False)
        with pytest.raises(RuntimeError, match="prepare_ambre"):
            gen.generate_spectrum(5000.0, 4.0, 0.0)

    def test_generate_spectra_before_prepare_raises(self, tmp_path):
        (tmp_path / "leaf.zip").touch()
        gen = SyntheticSpectrumGenerator(ambre_dir=str(tmp_path), cache_dir=False)
        with pytest.raises(RuntimeError, match="prepare_ambre"):
            gen.generate_spectra([1234567890123456789])

    def test_default_construction_uses_bundled_grid(self, monkeypatch):
        captured = {}
        def fake_load(self, path):
            captured["path"] = path
            return pd.DataFrame(
                {
                    "filename": ["a.zip"],
                    "teff": [5000.0],
                    "logg": [4.0],
                    "mh": [0.0],
                    "wave_binned": [np.array([5000.0, 5010.0])],
                    "flux_binned": [np.array([1.0, 1.0])],
                }
            )

        class FakeInterpolator:  # noqa: D401
            def __init__(self, *a, **k):
                pass

            def get_grid_info(self):
                return {}

        monkeypatch.setattr(
            "gaia_twins.src.ambre_loader.AmbreLoader.load_binned_parquet", fake_load
        )
        monkeypatch.setattr(
            "gaia_twins.src.spectrum_generator.AmbreInterpolator", FakeInterpolator
        )

        # No arguments: must resolve the bundled grid automatically.
        gen = SyntheticSpectrumGenerator(cache_dir=False)
        gen.prepare_ambre()
        assert captured["path"].endswith(DEFAULT_AMBRE_BINNED)

    def test_cache_dir_false_disables_caching_everywhere(self):
        gen = SyntheticSpectrumGenerator(cache_dir=False)
        assert gen.cache_dir is None
        assert gen.gaia_querier.cache_dir is None

    def test_default_cache_dir_propagates_to_querier(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "gaia_twins.src.spectrum_generator.get_default_cache_dir",
            lambda: tmp_path,
        )
        gen = SyntheticSpectrumGenerator()  # no cache_dir -> default cache
        assert gen.cache_dir == tmp_path
        assert gen.gaia_querier.cache_dir == tmp_path

