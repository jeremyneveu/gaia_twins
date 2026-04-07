"""
Gaia Synthetic Spectra Generator

A Python package to generate synthetic stellar spectra from Gaia source IDs
using AMBRE stellar atmosphere models.
"""

from .__version__ import __version__
from .src.spectrum_generator import SyntheticSpectrumGenerator
from .src.interpolator import AmbreInterpolator
from .utils.binning import bin_spectrum

__all__ = [
    "__version__",
    "SyntheticSpectrumGenerator",
    "AmbreInterpolator",
    "bin_spectrum",
]
