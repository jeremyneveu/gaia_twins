"""4D interpolator for AMBRE stellar spectra.

Reimplements the notebook's ``RegularGridInterpolator`` approach, which maps
``(teff, logg, [M/H], wavelength) -> flux`` on the (irregular) AMBRE grid.
The previous KNN / KD-tree implementation built a model over *every* 4D point
(up to millions) which is neither accurate nor memory-scalable for ~13k
spectra; the regular-grid linear interpolation is both the reference method
and far more tractable.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.interpolate import RegularGridInterpolator
from scipy.ndimage import distance_transform_edt
from typing import Optional, Tuple

_DEFAULT_FILL = np.nan


class AmbreInterpolator(object):
    """
    4D regular-grid interpolator for AMBRE spectra.

    Interpolates flux as a function of ``(Teff, log g, [M/H], wavelength)``
    using a ``scipy.interpolate.RegularGridInterpolator`` built from a
    DataFrame of binned AMBRE spectra.

    Parameters
    ----------
    ambre_data : pd.DataFrame
        DataFrame with columns ``teff, logg, mh, flux_binned, wave_binned``.
    method : str
        Interpolation method: ``"linear"`` (default) or ``"nearest"``.
    n_neighbors : int
        Kept for API compatibility; unused for regular-grid interpolation.
    """

    def __init__(
        self,
        ambre_data: pd.DataFrame,
        method: str = 'linear',
        n_neighbors: int = 4,
    ):
        self.ambre_data = ambre_data
        self.method = method
        self.n_neighbors = n_neighbors
        self.model = None
        self.wavelength_grid = None
        self._teff_axis = None
        self._logg_axis = None
        self._mh_axis = None
        self._flux_grid = None

        if ambre_data is not None and len(ambre_data) > 0:
            self.wavelength_grid = np.asarray(ambre_data.iloc[0]['wave_binned'])

        self._build_interpolator()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def _build_interpolator(self):
        """Build the 4D regular-grid interpolation model."""
        if self.ambre_data is None or len(self.ambre_data) == 0:
            raise ValueError("No AMBRE data to build an interpolator from.")

        print(f"Building 4D AMBRE interpolator ({self.method})...")

        self._teff_axis = np.sort(self.ambre_data['teff'].unique())
        self._logg_axis = np.sort(self.ambre_data['logg'].unique())
        self._mh_axis = np.sort(self.ambre_data['mh'].unique())

        teff_index = {t: i for i, t in enumerate(self._teff_axis)}
        logg_index = {g: i for i, g in enumerate(self._logg_axis)}
        mh_index = {m: i for i, m in enumerate(self._mh_axis)}

        n_teff, n_logg, n_mh = len(self._teff_axis), len(self._logg_axis), len(self._mh_axis)
        n_wave = len(self.wavelength_grid)

        # Place the real spectra onto the 4D grid. Missing (teff, logg, mh)
        # combinations are filled from the closest populated grid point (in
        # parameter space) so that linear interpolation never hits NaN; this
        # reproduces the notebook behaviour in a numerically robust way.
        flux_grid = np.empty((n_teff, n_logg, n_mh, n_wave), dtype=np.float64)
        valid = np.zeros((n_teff, n_logg, n_mh), dtype=bool)

        for row in self.ambre_data.itertuples():
            i_t = teff_index.get(row.teff)
            i_g = logg_index.get(row.logg)
            i_m = mh_index.get(row.mh)
            if i_t is None or i_g is None or i_m is None:
                continue
            flux_grid[i_t, i_g, i_m, :] = np.asarray(row.flux_binned)
            valid[i_t, i_g, i_m] = True

        filled = int(valid.sum())
        print("Grid shape: {} ({} spectra placed)".format(flux_grid.shape, filled))

        # Fill empty cells (within the convex hull of populated points) with
        # the values of the nearest populated cell.
        empty = ~valid
        if empty.any():
            if not valid.any():
                raise ValueError("No AMBRE spectra could be placed on the grid.")
            _, indices = distance_transform_edt(valid, return_indices=True)
            i_src, g_src, m_src = indices
            flux_grid[empty] = flux_grid[i_src[empty], g_src[empty], m_src[empty], :]
            print(
                "Filled {} missing grid cells from nearest neighbours".format(
                    int(empty.sum())
                )
            )

        axes = (self._teff_axis, self._logg_axis, self._mh_axis, self.wavelength_grid)

        # fill_value guards extrapolation outside the grid; nearest-neighbour
        # filling above handles the (sparse) interior.
        self.model = RegularGridInterpolator(
            axes,
            flux_grid,
            method=self.method,
            bounds_error=False,
            fill_value=_DEFAULT_FILL,
        )
        self._flux_grid = flux_grid
        print("4D AMBRE interpolator ready.")

    # ------------------------------------------------------------------
    # Interpolation
    # ------------------------------------------------------------------
    def interpolate(
        self,
        wavelengths: np.ndarray,
        teff: float,
        logg: float,
        mh: float,
    ) -> np.ndarray:
        """
        Interpolate a synthetic spectrum at the given stellar parameters.

        Parameters
        ----------
        wavelengths : np.ndarray
            Wavelength array in Angstroms.
        teff : float
            Effective temperature (K).
        logg : float
            Surface gravity (cgs).
        mh : float
            Metallicity [M/H] (dex).

        Returns
        -------
        np.ndarray
            Interpolated flux array (same length as ``wavelengths``).
        """
        wavelengths = np.asarray(wavelengths, dtype=float)

        # Clamp stellar parameters to the grid bounds so that sources slightly
        # outside the AMBRE grid (e.g. Teff below the coolest model) receive
        # the closest available grid model instead of NaN.
        teff_c = float(np.clip(teff, self._teff_axis.min(), self._teff_axis.max()))
        logg_c = float(np.clip(logg, self._logg_axis.min(), self._logg_axis.max()))
        mh_c = float(np.clip(mh, self._mh_axis.min(), self._mh_axis.max()))

        query_points = np.column_stack([
            np.full(len(wavelengths), teff_c),
            np.full(len(wavelengths), logg_c),
            np.full(len(wavelengths), mh_c),
            wavelengths,
        ])

        return np.asarray(self.model(query_points), dtype=float)

    def __call__(
        self,
        wavelengths: np.ndarray,
        teff: float,
        logg: float,
        mh: float,
    ) -> np.ndarray:
        """Equivalent to :meth:`interpolate`."""
        return self.interpolate(wavelengths, teff, logg, mh)

    # ------------------------------------------------------------------
    # Inspect
    # ------------------------------------------------------------------
    def check_bounds(
        self,
        teff: float,
        logg: float,
        mh: float,
    ) -> Tuple[bool, str]:
        """
        Check whether the requested parameters lie within the AMBRE grid.

        Returns
        -------
        is_valid : bool
            True if all parameters are inside the grid bounds.
        message : str
            Human-readable description of any out-of-bounds parameters.
        """
        is_valid = False
        message = "Parameters within bounds"

        if self._teff_axis is None:
            return is_valid, "Interpolator not built"

        issues = []
        if teff < self._teff_axis.min() or teff > self._teff_axis.max():
            issues.append(
                "Teff={:.0f}K out of range [{:.0f}, {:.0f}]".format(
                    teff, self._teff_axis.min(), self._teff_axis.max()
                )
            )
        if logg < self._logg_axis.min() or logg > self._logg_axis.max():
            issues.append(
                "log g={:.1f} out of range [{:.1f}, {:.1f}]".format(
                    logg, self._logg_axis.min(), self._logg_axis.max()
                )
            )
        if mh < self._mh_axis.min() or mh > self._mh_axis.max():
            issues.append(
                "[M/H]={:.1f} out of range [{:.1f}, {:.1f}]".format(
                    mh, self._mh_axis.min(), self._mh_axis.max()
                )
            )

        if issues:
            return False, "; ".join(issues)
        return True, message

    def get_grid_info(self) -> dict:
        """Return statistics about the interpolation grid."""
        return {
            'n_spectra': len(self.ambre_data),
            'method': self.method,
            'teff_range': (self._teff_axis.min(), self._teff_axis.max()),
            'logg_range': (self._logg_axis.min(), self._logg_axis.max()),
            'mh_range': (self._mh_axis.min(), self._mh_axis.max()),
            'wavelength_range': (
                float(self.wavelength_grid.min()),
                float(self.wavelength_grid.max()),
            ),
            'n_wavelength_points': len(self.wavelength_grid),
            'grid_shape': None if self._flux_grid is None else self._flux_grid.shape,
        }

