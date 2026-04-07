"""Pytest configuration file."""

import sys
from pathlib import Path

# Add the package to the path for testing
package_root = Path(__file__).parent.parent / 'gaia_synth_spectra'
sys.path.insert(0, str(package_root))
