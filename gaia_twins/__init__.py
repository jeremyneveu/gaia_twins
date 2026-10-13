"""
gaia-twins: high-resolution synthetic "twin" spectra for Gaia stars.

A Python package that generates high-resolution synthetic stellar spectra
("twins") for Gaia stars by interpolating the AMBRE grid of stellar
atmosphere models at the astrophysical parameters (Teff, log g, [M/H]) of
each target source.
"""

from .__version__ import __version__
from .src.spectrum_generator import SyntheticSpectrumGenerator
from .src.interpolator import AmbreInterpolator
from .src.ambre_loader import AmbreLoader, parse_ambre_filename
from .src.gaia_query import GaiaQuerier
from .data.defaults import (
    DEFAULT_AMBRE_BINNED,
    get_default_ambre_data_path,
    get_default_ambre_dir,
    get_default_cache_dir,
)
from .utils.binning import (
    bin_spectrum,
    bin_spectrum_scipy,
    rebin_spectrum,
    adaptive_bin,
)
from .utils.normalization import ambre_normalization, normalize_flux
from .utils.validators import validate_source_ids, validate_wavelength_range

__all__ = [
    "__version__",
    "SyntheticSpectrumGenerator",
    "AmbreInterpolator",
    "AmbreLoader",
    "parse_ambre_filename",
    "GaiaQuerier",
    "DEFAULT_AMBRE_BINNED",
    "get_default_ambre_data_path",
    "get_default_ambre_dir",
    "get_default_cache_dir",
    "bin_spectrum",
    "bin_spectrum_scipy",
    "rebin_spectrum",
    "adaptive_bin",
    "ambre_normalization",
    "normalize_flux",
    "validate_source_ids",
    "validate_wavelength_range",
]

