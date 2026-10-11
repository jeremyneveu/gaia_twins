"""Pytest configuration file.

Ensures the project root is importable so ``tests`` can ``import gaia_twins``.
"""

import sys
from pathlib import Path

# Add the project root (parent of tests/) to sys.path so that ``gaia_twins``
# is importable regardless of where pytest is invoked from.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

