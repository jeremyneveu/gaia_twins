"""Tests for the AMBRE data loader."""

import pandas as pd
import pytest

from gaia_twins.src.ambre_loader import AmbreLoader, parse_ambre_filename


class TestParseAmbreFilename:
    def test_full_filename(self):
        result = parse_ambre_filename(
            "M_p3500g3.5z-0.25t1.0_a-0.10c0.00n0.00o-0.10r0.00s0.00_VIS.spec.flat.zip"
        )
        assert result == {"teff": 3500.0, "logg": 3.5, "mh": -0.25}

    def test_negative_logg(self):
        result = parse_ambre_filename(
            "M_p4000g-0.5z0.0t1.0_a0.00c0.00n0.00o0.00r0.00s0.00_VIS.spec.flat.zip"
        )
        assert result["logg"] == -0.5

    def test_s_family_giant_grid(self):
        # Files from the "s" (giant/extension) grid must also parse.
        result = parse_ambre_filename(
            "M_s5500g1.0z-1.50t2.0_a0.80c0.00n0.00o0.80r0.00s0.00_VIS.spec.flat.zip"
        )
        assert result == {"teff": 5500.0, "logg": 1.0, "mh": -1.5}

    def test_raises_on_unparseable(self):
        with pytest.raises(ValueError, match="Could not parse"):
            parse_ambre_filename("not_a_real_filename.zip")


class TestAmbreLoader:
    @pytest.fixture
    def loader(self, tmp_path):
        # tmp_path holds a fake AMBRE dir (one .zip) so the constructor passes;
        # the catalog is set directly to keep the test self-contained.
        (tmp_path / "M_p5000g4.0z0.00t1.0_a0.00c0.00n0.00o0.00r0.00s0.00_VIS.spec.flat.zip").touch()
        loader = AmbreLoader(str(tmp_path))
        loader.catalog = pd.DataFrame(
            [
                {"filename": "A_p4000g3.5z-1.0...zip", "teff": 4000.0, "logg": 3.5, "mh": -1.0},
                {"filename": "B_p5000g4.0z0.0...zip", "teff": 5000.0, "logg": 4.0, "mh": 0.0},
                {"filename": "C_p6000g4.5z0.5...zip", "teff": 6000.0, "logg": 4.5, "mh": 0.5},
            ]
        )
        return loader

    def test_find_closest_index(self, loader):
        idx = loader.find_closest(5100.0, 4.1, 0.05, return_distance=False)
        assert loader.catalog.iloc[idx]["filename"].startswith("B")

    def test_find_closest_distance(self, loader):
        # Querying exactly on the target's parameters yields distance ~ 0.
        idx, distance = loader.find_closest(5000.0, 4.0, 0.0, return_distance=True)
        assert loader.catalog.iloc[idx]["filename"].startswith("B")
        assert distance == pytest.approx(0.0)

    def test_find_closest_raises_without_catalog(self, tmp_path):
        (tmp_path / "x.zip").touch()
        loader = AmbreLoader(str(tmp_path))
        with pytest.raises(ValueError, match="Catalog not created"):
            loader.find_closest(5000.0, 4.0, 0.0)
