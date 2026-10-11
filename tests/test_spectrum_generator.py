"""Tests for the synthetic spectrum generator."""

import pytest

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
            ambre_dir=str(tmp_path), interpolation_method="knn"
        )
        assert gen.interpolation_method == "nearest"

    def test_generate_spectrum_before_prepare_raises(self, tmp_path):
        (tmp_path / "leaf.zip").touch()
        gen = SyntheticSpectrumGenerator(ambre_dir=str(tmp_path))
        with pytest.raises(RuntimeError, match="prepare_ambre"):
            gen.generate_spectrum(5000.0, 4.0, 0.0)

    def test_generate_spectra_before_prepare_raises(self, tmp_path):
        (tmp_path / "leaf.zip").touch()
        gen = SyntheticSpectrumGenerator(ambre_dir=str(tmp_path))
        with pytest.raises(RuntimeError, match="prepare_ambre"):
            gen.generate_spectra([1234567890123456789])
