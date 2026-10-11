"""Spectral binning utilities.

All ``*_spectrum`` helpers share a common, documented API:

* ``bin_spectrum`` / ``bin_spectrum_scipy`` bin onto a uniform wavelength grid
  defined by ``wave_min``, ``wave_max`` and ``wave_step``, aggregating samples
  with a configurable ``statistic`` (``"mean"``, ``"median"``, ...).
* ``rebin_spectrum`` resamples onto an arbitrary target wavelength grid via
  (interpolating) 1D resampling.
* ``adaptive_bin`` grows variable-size bins until a target SNR is reached.
"""

from __future__ import annotations

import numpy as np
from scipy.interpolate import interp1d
from scipy.stats import binned_statistic
from typing import Optional, Tuple

VALID_STATISTICS = ("mean", "median", "sum", "count", "std", "min", "max")


def _validate_inputs(wavelength: np.ndarray, flux: np.ndarray):
    """Raise ``ValueError`` on empty or mismatched inputs."""
    wavelength = np.asarray(wavelength)
    flux = np.asarray(flux)

    if wavelength.size == 0 or flux.size == 0:
        raise ValueError("wavelength and flux must not be empty")

    if wavelength.shape[0] != flux.shape[0]:
        raise ValueError("wavelength and flux must have the same length")

    return wavelength, flux


def _validate_statistic(statistic: str) -> str:
    statistic = (statistic or "mean").lower()
    if statistic not in VALID_STATISTICS:
        raise ValueError(
            "statistic must be one of {}, got {}".format(VALID_STATISTICS, statistic)
        )
    return statistic


def _make_bin_edges(
    wave_min: float,
    wave_max: float,
    wave_step: float,
) -> np.ndarray:
    """Build a uniform set of bin edges covering ``[wave_min, wave_max]``."""
    if wave_min >= wave_max:
        raise ValueError("wave_min must be smaller than wave_max")
    if wave_step <= 0:
        raise ValueError("wave_step must be positive")
    return np.arange(wave_min, wave_max + wave_step, wave_step)


def bin_spectrum(
    wavelength: np.ndarray,
    flux: np.ndarray,
    wave_min: float = None,
    wave_max: float = None,
    wave_step: float = 1.0,
    statistic: str = "mean",
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Bin a spectrum onto a uniform wavelength grid.

    Each data point is assigned to the bin containing its wavelength; the
    bin value is the ``statistic`` (mean/median/...) of the fluxes it holds.

    Parameters
    ----------
    wavelength : np.ndarray
        Wavelength array (Angstroms or any unit; must match ``wave_min`` set).
    flux : np.ndarray
        Flux array.
    wave_min : float, optional
        Lower boundary of the first bin. Defaults to ``floor(min(wavelength))``.
    wave_max : float, optional
        Upper boundary of the last bin. Defaults to ``ceil(max(wavelength))``.
    wave_step : float
        Uniform bin width (default 1.0).
    statistic : str
        Aggregation statistic: ``"mean"`` (default), ``"median"``, ``"sum"``,
        ``"count"``, ``"std"``, ``"min"`` or ``"max"``.

    Returns
    -------
    bin_centers : np.ndarray
        Centres of the wavelength bins.
    binned_flux : np.ndarray
        Aggregated flux per bin.

    Raises
    ------
    ValueError
        If inputs are empty, of mismatched length, or ``wave_step <= 0``.
    """
    wavelength, flux = _validate_inputs(wavelength, flux)
    statistic = _validate_statistic(statistic)

    if wave_min is None:
        wave_min = float(np.floor(np.nanmin(wavelength)))
    if wave_max is None:
        wave_max = float(np.ceil(np.nanmax(wavelength)))

    bin_edges = _make_bin_edges(wave_min, wave_max, wave_step)
    if len(bin_edges) < 2:
        return np.array([]), np.array([])

    binned_flux, edges, _ = binned_statistic(
        wavelength, flux, statistic=statistic, bins=bin_edges
    )
    bin_centers = (edges[:-1] + edges[1:]) / 2.0

    return bin_centers, binned_flux


def bin_spectrum_scipy(
    wavelength: np.ndarray,
    flux: np.ndarray,
    wave_min: float = None,
    wave_max: float = None,
    wave_step: float = 1.0,
    statistic: str = "mean",
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Bin a spectrum using ``scipy.stats.binned_statistic``.

    See :func:`bin_spectrum` for parameters and return values.
    """
    wavelength, flux = _validate_inputs(wavelength, flux)
    statistic = _validate_statistic(statistic)

    if wave_min is None:
        wave_min = float(np.floor(np.nanmin(wavelength)))
    if wave_max is None:
        wave_max = float(np.ceil(np.nanmax(wavelength)))

    bin_edges = _make_bin_edges(wave_min, wave_max, wave_step)
    if len(bin_edges) < 2:
        return np.array([]), np.array([])

    binned_flux, edges, _ = binned_statistic(
        wavelength, flux, statistic=statistic, bins=bin_edges
    )
    bin_centers = (edges[:-1] + edges[1:]) / 2.0

    return bin_centers, binned_flux


def rebin_spectrum(
    wavelength: np.ndarray,
    flux: np.ndarray,
    new_wavelength: np.ndarray,
    method: str = "linear",
    fill_value: float = None,
) -> np.ndarray:
    """
    Resample a spectrum onto a new wavelength grid.

    Parameters
    ----------
    wavelength : np.ndarray
        Original wavelength array (monotonic).
    flux : np.ndarray
        Original flux array.
    new_wavelength : np.ndarray
        Target wavelength grid.
    method : str
        Interpolation kind: ``"linear"`` (default), ``"nearest"``, ``"cubic"``.
    fill_value : float, optional
        Value used outside the original range. Defaults to ``np.nan``.

    Returns
    -------
    np.ndarray
        Flux evaluated on ``new_wavelength``.
    """
    wavelength, flux = _validate_inputs(wavelength, flux)
    new_wavelength = np.asarray(new_wavelength, dtype=float)

    if fill_value is None:
        fill_value = np.nan

    f = interp1d(
        wavelength,
        flux,
        kind=method,
        bounds_error=False,
        fill_value=fill_value,
    )
    return f(new_wavelength)


def adaptive_bin(
    wavelength: np.ndarray,
    flux: np.ndarray,
    flux_error: Optional[np.ndarray] = None,
    target_snr: float = 10.0,
    max_bin_size: Optional[int] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Adaptive binning to reach a given per-bin signal-to-noise ratio.

    Samples are accumulated from left to right until the combined SNR reaches
    ``target_snr`` (or ``max_bin_size`` samples are used), then the bin is
    closed. Fluxes are combined by inverse-variance weighting.

    Parameters
    ----------
    wavelength : np.ndarray
        Wavelength array (monotonic).
    flux : np.ndarray
        Flux array.
    flux_error : np.ndarray, optional
        Per-sample flux error. If None, assumes Poisson noise
        ``sqrt(|flux|)``.
    target_snr : float
        Desired signal-to-noise ratio per bin (default 10.0).
    max_bin_size : int, optional
        Maximum number of samples per bin; stops accumulation regardless of
        SNR. Unbounded by default.

    Returns
    -------
    bin_centers : np.ndarray
        Mean wavelength of each bin.
    binned_flux : np.ndarray
        Inverse-variance weighted mean flux per bin.
    binned_error : np.ndarray
        Propagated flux error per bin.
    """
    wavelength, flux = _validate_inputs(wavelength, flux)

    if flux_error is None:
        flux_error = np.sqrt(np.abs(flux))
    else:
        flux_error = np.asarray(flux_error, dtype=float)
        if flux_error.shape[0] != flux.shape[0]:
            raise ValueError("flux_error must have the same length as flux")

    if target_snr <= 0:
        target_snr = 0.0

    bins = []
    bin_flux = []
    bin_error = []

    i = 0
    n = len(wavelength)
    max_bin_size = max_bin_size if max_bin_size is not None else n

    while i < n:
        # Weighted mean / combined variance over [i, j)
        w_sum = 0.0
        f_sum = 0.0
        j = i
        current_snr = 0.0

        while j < n and (j - i) < max_bin_size and current_snr < target_snr:
            var_j = flux_error[j] ** 2
            if var_j > 0:
                w_j = 1.0 / var_j
                w_sum += w_j
                f_sum += flux[j] * w_j
            j += 1
            if w_sum > 0:
                current_snr = (f_sum / w_sum) / np.sqrt(1.0 / w_sum)

        if w_sum <= 0:
            # Degenerate: every sample in the range has zero error weight.
            w_sum = 1.0
            f_sum = float(np.mean(flux[i:j])) if j > i else float(flux[i])

        binned_f = f_sum / w_sum
        binned_e = np.sqrt(1.0 / w_sum) if w_sum > 0 else np.inf

        bins.append(np.mean(wavelength[i:j]))
        bin_flux.append(binned_f)
        bin_error.append(binned_e)

        i = j

    return np.array(bins), np.array(bin_flux), np.array(bin_error)

