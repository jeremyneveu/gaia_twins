"""Tests for the Gaia querier astrophysical params cache."""

import pandas as pd
import pytest

from gaia_twins.src.gaia_query import GaiaQuerier


def make_gaia_result(source_ids, teffs, loggs, mhs):
    """Build a fake astroquery-style result with .get_results().to_pandas()."""
    df = pd.DataFrame(
        {
            "source_id": source_ids,
            "teff_gspspec": teffs,
            "logg_gspspec": loggs,
            "mh_gspspec": mhs,
        }
    )
    table = type("FakeTable", (), {"to_pandas": lambda self: df})()
    result = type("FakeResult", (), {"get_results": lambda self: table})()
    return result


def write_cache(cache_dir, rows):
    """Persist a params cache parquet with the given rows."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows, columns=["source_id", "teff", "logg", "mh", "source"])
    df.to_parquet(cache_dir / GaiaQuerier.PARAMS_CACHE_FILE)


@pytest.fixture
def monkeypatch_launch(monkeypatch):
    def _patch(fn):
        monkeypatch.setattr("gaia_twins.src.gaia_query.Gaia.launch_job", fn)
    return _patch


class TestFetchAstrophysicalParamsCache:
    def test_cache_hit_serves_from_cache_without_network(self, tmp_path, monkeypatch_launch):
        write_cache(
            tmp_path,
            [{"source_id": 11111, "teff": 6000.0, "logg": 4.0, "mh": 0.0, "source": "gspspec"}],
        )

        def fail_launch(*args, **kwargs):
            raise AssertionError("Gaia.launch_job should not be called on a cache hit")

        monkeypatch_launch(fail_launch)

        querier = GaiaQuerier(cache_dir=tmp_path)
        params = querier.fetch_astrophysical_params([11111])

        assert 11111 in params.index
        assert params.loc[11111, "teff"] == 6000.0

    def test_cache_miss_queries_and_persists(self, tmp_path, monkeypatch_launch):
        monkeypatch_launch(
            lambda qry: make_gaia_result([22222], [5500.0], [4.5], [-0.2])
        )

        querier = GaiaQuerier(cache_dir=tmp_path)
        params = querier.fetch_astrophysical_params([22222], use_gspspec=True)

        assert 22222 in params.index
        assert params.loc[22222, "logg"] == 4.5

        # Second call must be a cache hit (no network).
        calls = []

        def spy_launch(qry):
            calls.append(qry)
            return make_gaia_result([], [], [], [])

        monkeypatch_launch(spy_launch)
        params2 = querier.fetch_astrophysical_params([22222])
        assert calls == []
        assert 22222 in params2.index

    def test_cache_merge_mixed_hit_and_miss(self, tmp_path, monkeypatch_launch):
        write_cache(
            tmp_path,
            [{"source_id": 33333, "teff": 7000.0, "logg": 3.8, "mh": 0.1, "source": "gspspec"}],
        )

        monkeypatch_launch(
            lambda qry: make_gaia_result([44444], [4800.0], [2.5], [-0.5])
        )

        querier = GaiaQuerier(cache_dir=tmp_path)
        params = querier.fetch_astrophysical_params([33333, 44444])

        assert set(params.index) == {33333, 44444}
        assert params.loc[33333, "teff"] == 7000.0  # from cache
        assert params.loc[44444, "teff"] == 4800.0  # from network

        # Both should now be in the persisted cache.
        cached = pd.read_parquet(tmp_path / GaiaQuerier.PARAMS_CACHE_FILE)
        assert set(cached["source_id"]) == {33333, 44444}

    def test_no_cache_dir_always_queries_network(self, tmp_path, monkeypatch_launch):
        calls = []

        def counting_launch(qry):
            calls.append(qry)
            return make_gaia_result([55555], [6200.0], [4.2], [0.05])

        monkeypatch_launch(counting_launch)

        querier = GaiaQuerier(cache_dir=False)  # caching explicitly disabled
        querier.fetch_astrophysical_params([55555])
        querier.fetch_astrophysical_params([55555])

        assert len(calls) == 2  # queried every time

    def test_default_cache_dir_persists_new_ids(self, monkeypatch, tmp_path, monkeypatch_launch):
        # Default construction (no cache_dir) now uses a user-level cache, so
        # newly queried IDs are persisted — the regression the user reported.
        monkeypatch.setattr(
            "gaia_twins.src.gaia_query.get_default_cache_dir", lambda: tmp_path
        )
        monkeypatch_launch(lambda qry: make_gaia_result([77777], [6100.0], [4.1], [0.0]))

        querier = GaiaQuerier()  # no cache_dir -> default cache is used
        params = querier.fetch_astrophysical_params([77777])

        assert 77777 in params.index
        cached = pd.read_parquet(tmp_path / GaiaQuerier.PARAMS_CACHE_FILE)
        assert set(cached["source_id"]) == {77777}

        # A second querier (fresh instance / new run) serves from the cache.
        monkeypatch_launch(
            lambda qry: (_ for _ in ()).throw(AssertionError("should not query"))
        )
        params2 = GaiaQuerier().fetch_astrophysical_params([77777])
        assert 77777 in params2.index
