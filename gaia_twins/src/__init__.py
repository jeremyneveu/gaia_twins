"""Source code for synthetic spectrum generation."""

from .gaia_query import GaiaQuerier
from .ambre_loader import AmbreLoader, parse_ambre_filename
from .interpolator import AmbreInterpolator
from .spectrum_generator import SyntheticSpectrumGenerator

__all__ = [
    "GaiaQuerier",
    "AmbreLoader",
    "parse_ambre_filename",
    "AmbreInterpolator",
    "SyntheticSpectrumGenerator",
]
