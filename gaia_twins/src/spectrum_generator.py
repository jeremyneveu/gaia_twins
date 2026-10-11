"""Main synthetic spectrum generator combining Gaia data and AMBRE models.

The :class:`SyntheticSpectrumGenerator` is the main user-facing entry point.
It ties together the AMBRE grid loader, the 4D interpolator and the Gaia
archive querying, and exposes high-level "twin" helpers on top of them.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Optional, Tuple, Union

from .gaia_query import GaiaQuerier
from .ambre_loader import AmbreLoader
from .interpolator import AmbreInterpolator
from ..utils.normalization import normalize_spectrum

# Regular-grid interpolation methods supported by scipy.
_VALID_METHODS = ("linear", "nearest")


class SyntheticSpectrumGenerator:
    """
    Generate synthetic stellar spectra ("twins") from Gaia source IDs.

    The generator loads a grid of AMBRE synthetic spectra and interpolates
    them at the astrophysical parameters (Teff, log g, [M/H]) of target Gaia
    stars, producing high-resolution model spectra that match each target.

    Parameters
    ----------
    ambre_dir : str
        Directory containing the AMBRE data (ZIP files or a pre-binned
        parquet grid).
    cache_dir : str, optional
        Directory used to persist processed AMBRE grids across runs.
    interpolation_method : str
        Interpolation scheme: ``"linear"`` (default) or ``"nearest"``.
    n_neighbors : int, optional
        Deprecated; retained for backwards compatibility and unused by the
        regular-grid interpolator.
    """

    def __init__(
        self,
        ambre_dir: str = "AMBRE",
        cache_dir: Optional[str] = None,
        interpolation_method: str = "linear",
        n_neighbors: Optional[int] = None,
    ):
        method = (interpolation_method or "linear").lower()
        # Backwards compatibility: the former KNN/KD-tree nearest-neighbour
        # schemes map onto the regular-grid 'nearest' interpolator.
        if method in ("knn", "kdtree"):
            method = "nearest"
        if method not in _VALID_METHODS:
            raise ValueError(
                "interpolation_method must be one of {}; got {}".format(
                    _VALID_METHODS, interpolation_method
                )
            )

        self.ambre_dir = Path(ambre_dir)
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.interpolation_method = method
        self.n_neighbors = n_neighbors

        # Components
        self.gaia_querier = GaiaQuerier(cache_dir=self.cache_dir)
        self.ambre_loader = AmbreLoader(str(self.ambre_dir))
        self.interpolator: Optional[AmbreInterpolator] = None

        # Data
        self.ambre_binned: Optional[pd.DataFrame] = None
        self.wavelength_grid: Optional[np.ndarray] = None

        # Create cache directory if needed
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # AMBRE preparation
    # ------------------------------------------------------------------
    def prepare_ambre(
        self,
        parquet_path: Optional[str] = None,
        wavelength_min: float = 3000.0,
        wavelength_max: float = 11000.0,
        wavelength_step: float = 10.0,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        Load the AMBRE grid and build the interpolation model.

        Two data sources are supported:

        * **Pre-binned parquet** (recommended): pass ``parquet_path`` pointing
          at a file (e.g. ``AMBRE/ambre_complete_binned_10.0A.parquet``) with
          columns ``filename, teff, logg, mh, flux_binned, wave_binned``. This
          avoids reading the ~13k raw AMBRE ZIP archives.
        * **Raw ZIP archives**: when ``parquet_path`` is ``None`` the AMBRE
          directory is scanned for ``*.zip`` files, each binned onto the
          wavelength grid defined by ``wavelength_min/max/step``.

        Parameters
        ----------
        parquet_path : str, optional
            Path to a pre-binned parquet grid. When provided,
            ``wavelength_min/max/step`` are ignored in favour of the grid
            stored inside the file.
        wavelength_min : float
            Lower bound of the binned grid (Angstroms) for the ZIP path.
        wavelength_max : float
            Upper bound of the binned grid (Angstroms) for the ZIP path.
        wavelength_step : float
            Bin width (Angstroms) for the ZIP path.
        use_cache : bool
            If True (and ``cache_dir`` is configured) the processed grid is
            loaded from / saved to cache. Has no effect when ``parquet_path``
            is given.

        Returns
        -------
        pd.DataFrame
            The prepared, binned AMBRE grid.
        """
        if parquet_path is not None:
            self.ambre_binned = self.ambre_loader.load_binned_parquet(
                str(parquet_path)
            )
            self.wavelength_grid = np.asarray(
                self.ambre_binned.iloc[0]["wave_binned"], dtype=float
            )
        else:
            # Verify the directory exists before attempting a slow scan.
            if not self.ambre_dir.exists():
                raise FileNotFoundError(
                    "AMBRE directory not found: {} (either supply a valid "
                    "directory of ZIP files or pass parquet_path)".format(
                        self.ambre_dir
                    )
                )
            self.wavelength_grid = np.arange(
                wavelength_min, wavelength_max + wavelength_step, wavelength_step
            )
            print(
                "Wavelength grid: {:.0f} - {:.0f} A (step {:.1f}, {} points)".format(
                    wavelength_min, wavelength_max, wavelength_step, len(self.wavelength_grid)
                )
            )
            self.ambre_binned = self._bin_raw_amdre(
                use_cache=use_cache, wavelength_step=wavelength_step
            )

        self._build_interpolator()
        return self.ambre_binned

    def _bin_raw_amdre(
        self,
        use_cache: bool,
        wavelength_step: float,
    ) -> pd.DataFrame:
        """Bin raw AMBRE ZIP archives onto ``self.wavelength_grid``."""
        cache_file = None
        if use_cache and self.cache_dir:
            cache_file = self.cache_dir / "ambre_binned_{:.1f}A.pkl".format(
                wavelength_step
            )
            if cache_file.exists():
                print("Loading cached AMBRE data from {}".format(cache_file))
                return self.ambre_loader.load_cache(str(cache_file))

        self.ambre_loader.create_catalog()
        binned = self.ambre_loader.load_binned_spectra(self.wavelength_grid)

        if cache_file is not None:
            self.ambre_loader.save_cache(str(cache_file), binned)

        return binned

    def _build_interpolator(self) -> None:
        """Build the 4D regular-grid interpolator from the binned AMBRE data."""
        if self.ambre_binned is None or len(self.ambre_binned) == 0:
            raise ValueError("No AMBRE data prepared; call prepare_ambre() first")
        self.interpolator = AmbreInterpolator(
            self.ambre_binned,
            method=self.interpolation_method,
            n_neighbors=self.n_neighbors,
        )

    # ------------------------------------------------------------------
    # Spectrum generation
    # ------------------------------------------------------------------
    def generate_spectrum(
        self,
        teff: float,
        logg: float,
        mh: float,
        wavelengths: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate a synthetic spectrum for a given set of stellar parameters.

        Parameters
        ----------
        teff : float
            Effective temperature (K).
        logg : float
            Surface gravity (cgs).
        mh : float
            Metallicity [M/H] (dex).
        wavelengths : np.ndarray, optional
            Wavelength grid (Angstroms) on which to evaluate the spectrum.
            Defaults to the generator's prepared wavelength grid.

        Returns
        -------
        wavelengths : np.ndarray
            The wavelength array used.
        flux : np.ndarray
            Interpolated flux, same length as ``wavelengths``.
        """
        self._require_ready()

        if wavelengths is None:
            wavelengths = self.wavelength_grid
        wavelengths = np.asarray(wavelengths, dtype=float)

        flux = self.interpolator.interpolate(wavelengths, teff, logg, mh)
        return wavelengths, flux

    def _require_ready(self) -> None:
        """Raise if AMBRE data has not been prepared yet."""
        if self.interpolator is None or self.ambre_binned is None:
            raise RuntimeError(
                "AMBRE grid not prepared. Call prepare_ambre() before generating spectra."
            )

    def generate_spectra(
        self,
        source_ids: Union[List[int], List[str], np.ndarray],
        use_gspspec: bool = False,
        wavelengths: Optional[np.ndarray] = None,
    ) -> pd.DataFrame:
        """
        Generate synthetic spectra for a list of Gaia source IDs.

        For each source, stellar parameters (Teff, log g, [M/H]) are fetched
        from the Gaia archive (GSP-Phot by default, GSP-Spec if
        ``use_gspspec``) and the AMBRE grid is interpolated at those values.

        Parameters
        ----------
        source_ids : list or np.ndarray
            Gaia DR3 source IDs.
        use_gspspec : bool
            Use GSP-Spec rather than GSP-Phot parameters (default False).
        wavelengths : np.ndarray, optional
            Wavelength grid on which to generate the spectra. Defaults to the
            prepared grid.

        Returns
        -------
        pd.DataFrame
            A DataFrame indexed by ``source_id`` with columns ``teff, logg,
            mh, synth_wave, synth_flux`` (one row per source).
        """
        self._require_ready()

        source_ids = [int(sid) for sid in source_ids]
        params = self.gaia_querier.fetch_astrophysical_params(source_ids, use_gspspec)

        if wavelengths is None:
            wavelengths = self.wavelength_grid
        wavelengths = np.asarray(wavelengths, dtype=float)

        # ``fetch_astrophysical_params`` returns source_id either as the index
        # or as a column; normalise to a dictionary keyed by source_id.
        if not params.empty and "source_id" in params.columns:
            params = params.set_index("source_id")
        param_by_id = {
            int(idx): (float(row["teff"]), float(row["logg"]), float(row["mh"]))
            for idx, row in params.iterrows()
        }

        rows = []
        for sid in source_ids:
            row_params = param_by_id.get(sid)
            if row_params is None:
                rows.append(
                    {
                        "source_id": sid,
                        "teff": np.nan,
                        "logg": np.nan,
                        "mh": np.nan,
                        "synth_wave": wavelengths,
                        "synth_flux": np.full(len(wavelengths), np.nan),
                    }
                )
                continue

            teff, logg, mh = row_params

            # Skip sources whose parameters are missing.
            if any(np.isnan([teff, logg, mh])):
                rows.append(
                    {
                        "source_id": sid,
                        "teff": np.nan, "logg": np.nan, "mh": np.nan,
                        "synth_wave": wavelengths,
                        "synth_flux": np.full(len(wavelengths), np.nan),
                    }
                )
                continue

            _, flux = self.generate_spectrum(teff, logg, mh, wavelengths)
            rows.append(
                {
                    "source_id": sid,
                    "teff": teff, "logg": logg, "mh": mh,
                    "synth_wave": wavelengths,
                    "synth_flux": flux,
                }
            )

        results = pd.DataFrame(rows).set_index("source_id")
        print(
            "Generated spectra for {} sources ({} with parameters)".format(
                len(results), results["teff"].notna().sum()
            )
        )
        return results

    # ------------------------------------------------------------------
    # Twin helpers
    # ------------------------------------------------------------------
    def find_twin(
        self,
        teff: float,
        logg: float,
        mh: float,
        return_index: bool = False,
    ) -> Union[pd.Series, int]:
        """
        Find the closest AMBRE spectrum to the requested stellar parameters.

        The "twin" is the AMBRE grid point minimising the (normalised)
        Euclidean distance in (Teff, log g, [M/H]) space.

        Parameters
        ----------
        teff : float
            Effective temperature (K).
        logg : float
            Surface gravity (cgs).
        mh : float
            Metallicity [M/H] (dex).
        return_index : bool
            If True, return the row index into the catalog instead of the row.

        Returns
        -------
        pd.Series or int
            The closest catalog row (with ``filename, teff, logg, mh``), or
            its positional index when ``return_index=True``.
        """
        self._require_ready()
        idx = self.ambre_loader.find_closest(teff, logg, mh, return_distance=False)
        return idx if return_index else self.ambre_loader.catalog.iloc[idx]

    def generate_twins(
        self,
        source_ids: Union[List[int], List[str], np.ndarray],
        use_gspspec: bool = False,
    ) -> pd.DataFrame:
        """
        Generate "twin" spectra for Gaia sources.

        For each source the stellar parameters are fetched from the Gaia
        archive, the closest AMBRE model is located with
        :meth:`find_twin`, and a high-resolution synthetic spectrum is
        interpolated at those parameters.

        Returns
        -------
        pd.DataFrame
            One row per source (indexed by ``source_id``) with columns
            ``teff, logg, mh`` and the columns returned by
            :meth:`generate_spectra`.
        """
        self._require_ready()

        results = self.generate_spectra(source_ids, use_gspspec=use_gspspec)

        twins = []
        for sid, row in results.iterrows():
            twin_row = None
            if not np.isnan(row["teff"]):
                twin_row = self.find_twin(row["teff"], row["logg"], row["mh"])
            twins.append(
                {
                    "source_id": sid,
                    "twin_teff": None if twin_row is None else twin_row["teff"],
                    "twin_logg": None if twin_row is None else twin_row["logg"],
                    "twin_mh": None if twin_row is None else twin_row["mh"],
                    "twin_filename": None if twin_row is None else twin_row["filename"],
                }
            )

        twin_df = pd.DataFrame(twins).set_index("source_id")
        results = results.join(twin_df, how="outer")
        print(
            "Found twins for {} sources".format(results["twin_filename"].notna().sum())
        )
        return results

    # ------------------------------------------------------------------
    # Persistence / inspection
    # ------------------------------------------------------------------
    def save_spectra(
        self,
        spectra: pd.DataFrame,
        output_file: str,
        format: str = "parquet",
    ) -> str:
        """
        Save a spectra DataFrame to disk.

        Parameters
        ----------
        spectra : pd.DataFrame
            DataFrame of generated spectra (from :meth:`generate_spectra`).
        output_file : str
            Destination path.
        format : str
            ``"parquet"`` (default), ``"pickle"`` or ``"csv"``. Array columns
            (``synth_wave``/``synth_flux``) are lost in ``"csv"``.

        Returns
        -------
        str
            The path the data was written to.
        """
        fmt = (format or "parquet").lower()
        if fmt in ("parquet",):
            spectra.to_parquet(output_file, index=True)
        elif fmt in ("pickle", "pkl"):
            spectra.to_pickle(output_file)
        elif fmt in ("csv",):
            metadata = spectra.drop(columns=["synth_wave", "synth_flux"])
            metadata.to_csv(output_file)
        else:
            raise ValueError("Unsupported output format: {}".format(format))
        print("Spectra saved to {}".format(output_file))
        return output_file

    def load_spectra(self, input_file: str) -> pd.DataFrame:
        """Load a spectra DataFrame saved with :meth:`save_spectra`."""
        input_file = str(input_file)
        if input_file.endswith((".pkl", ".pickle")):
            return pd.read_pickle(input_file)
        if input_file.endswith(".csv"):
            return pd.read_csv(input_file, index_col=0)
        return pd.read_parquet(input_file)

    def get_info(self) -> dict:
        """Return a summary of the generator's configuration and prepared grid."""
        info = {
            "ambre_dir": str(self.ambre_dir),
            "cache_dir": str(self.cache_dir) if self.cache_dir else None,
            "interpolation_method": self.interpolation_method,
            "n_neighbors": self.n_neighbors,
            "ambre_prepared": self.ambre_binned is not None,
        }
        if self.interpolator is not None and self.wavelength_grid is not None:
            info.update(self.interpolator.get_grid_info())
        return info





