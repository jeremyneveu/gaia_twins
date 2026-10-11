"""Tests for the AMBRE interpolator module."""

import numpy as np
import pandas as pd
import pytest

from gaia_twins.src.interpolator import AmbreInterpolator


def _make_grid_data(n_wave: int = 20):
    """Build a small, fully-populated (teff, logg, mh) grid DataFrame."""
    wave = np.linspace(4000.0, 8000.0, n_wave)
    rows = []
    for teff in [4000.0, 5000.0]:
        for logg in [3.0, 4.0]:
            for mh in [-1.0, 0.0]:
                flux = teff * 0.1 + logg * 20.0 + mh * 50.0 + wave * 0.01
                rows.append(
                    {
                        "filename": f"p{teff}g{logg}z{mh}.zip",
                        "teff": teff,
                        "logg": logg,
                        "mh": mh,
                        "flux_binned": flux,
                        "wave_binned": wave,
                    }
                )
    return pd.DataFrame(rows)


class TestAmbreInterpolator:
    def test_construct_and_grid_info(self):
        interp = AmbreInterpolator(_make_grid_data(), method="linear")
        info = interp.get_grid_info()
        assert info["grid_shape"] == (2, 2, 2, 20)
        assert info["method"] == "linear"
        assert info["n_spectra"] == 8

    def test_interpolate_matches_grid_node(self):
        interp = AmbreInterpolator(_make_grid_data(), method="linear")
        wave = np.linspace(4000.0, 8000.0, 20)
        flux = interp.interpolate(wave, teff=4000.0, logg=3.0, mh=-1.0)
        # At a grid node, linear interpolation reproduces the node exactly.
        node = 4000.0 * 0.1 + 3.0 * 20.0 + (-1.0) * 50.0 + wave * 0.01
        np.testing.assert_allclose(flux, node, atol=1e-8)

    def test_interpolate_finite_at_off_grid_point(self):
        interp = AmbreInterpolator(_make_grid_data(), method="linear")
        wave = np.linspace(4000.0, 8000.0, 20)
        flux = interp.interpolate(wave, teff=4500.0, logg=3.5, mh=-0.5)
        assert np.isfinite(flux).all()

    def test_check_bounds_within(self):
        interp = AmbreInterpolator(_make_grid_data())
        ok, _ = interp.check_bounds(4500.0, 3.5, -0.5)
        assert ok is True

    def test_check_bounds_outside(self):
        interp = AmbreInterpolator(_make_grid_data())
        ok, msg = interp.check_bounds(12000.0, 3.5, -0.5)
        assert ok is False
        assert "Teff" in msg

    def test_raises_on_empty_data(self):
        with pytest.raises(ValueError):
            AmbreInterpolator(pd.DataFrame())
