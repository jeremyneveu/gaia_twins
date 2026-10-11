#!/usr/bin/env python3
"""Rebuild a binned AMBRE grid as a single parquet file.

The synthetic-spectrum pipeline can work directly from the raw AMBRE ZIP
archives, but reading and interpolating ~13k spectra on every run is slow.
This script performs that work **once**, producing a parquet file in exactly
the format expected by
:meth:`gaia_twins.src.ambre_loader.AmbreLoader.load_binned_parquet`.

Output columns
--------------
``filename`` : str
    Name of the source AMBRE ZIP file.
``teff``, ``logg``, ``mh`` : float
    Stellar parameters parsed from the filename (K, cgs, dex).
``flux_binned`` : np.ndarray
    Flux interpolated onto the common wavelength grid (W/nm/m²).
``wave_binned`` : np.ndarray
    The common wavelength grid (Å), identical for every row.

Usage
-----
.. code-block:: bash

    python scripts/rebuild_ambre_grid.py \\
        --ambre-dir AMBRE \\
        --output AMBRE/ambre_complete_binned_10.0A.parquet \\
        --wave-min 3000 --wave-max 11000 --wave-step 10.0
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make the in-tree package importable when run as a plain script, e.g.
# ``python scripts/rebuild_ambre_grid.py`` from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from gaia_twins.src.ambre_loader import AmbreLoader  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Rebuild the binned AMBRE grid as a single parquet file that "
            "the gaia-twins pipeline can load directly."
        )
    )
    parser.add_argument(
        "--ambre-dir", "-a", default="AMBRE",
        help="Directory containing the raw AMBRE ZIP archives (default: AMBRE).",
    )
    parser.add_argument(
        "--output", "-o", default="AMBRE/ambre_complete_binned_10.0A.parquet",
        help="Output parquet path (default: AMBRE/ambre_complete_binned_10.0A.parquet).",
    )
    parser.add_argument(
        "--wave-min", type=float, default=3000.0,
        help="Lower bound of the common wavelength grid in Å (default: 3000).",
    )
    parser.add_argument(
        "--wave-max", type=float, default=11000.0,
        help="Upper bound of the common wavelength grid in Å (default: 11000).",
    )
    parser.add_argument(
        "--wave-step", type=float, default=10.0,
        help="Bin width of the common wavelength grid in Å (default: 10).",
    )
    return parser


def main(argv=None) -> int:
    """Run the rebuild pipeline."""
    args = build_parser().parse_args(argv)

    ambre_dir = Path(args.ambre_dir)
    if not ambre_dir.exists():
        print(f"Error: AMBRE directory not found: {ambre_dir}", file=sys.stderr)
        return 1

    # Common wavelength grid (Å), inclusive of the upper bound.
    wave_grid = np.arange(
        args.wave_min, args.wave_max + args.wave_step, args.wave_step
    )
    print(
        f"Binning onto {len(wave_grid)} wavelength points: "
        f"{wave_grid.min():.0f} - {wave_grid.max():.0f} Å (step {args.wave_step:.1f} Å)"
    )

    loader = AmbreLoader(str(ambre_dir))
    loader.create_catalog()
    print(f"Found {len(loader.catalog)} AMBRE spectra in catalog")

    binned = loader.load_binned_spectra(wave_grid, show_progress=True)

    if len(binned) == 0:
        print("Error: no spectra could be binned.", file=sys.stderr)
        return 1

    # Ensure the required columns are present and written as a parquet grid.
    required = {"filename", "teff", "logg", "mh", "flux_binned", "wave_binned"}
    missing = required - set(binned.columns)
    if missing:
        print(
            f"Error: binned output missing columns: {sorted(missing)}",
            file=sys.stderr,
        )
        return 1

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        # save_cache writes a parquet whenever the suffix is '.parquet'.
        loader.save_cache(str(output), binned)
    except Exception as exc:  # pragma: no cover - defensive
        print(f"Error: failed to write parquet: {exc}", file=sys.stderr)
        return 1

    print("Done.")
    print(f"  Output : {output}")
    print(f"  Spectra: {len(binned)}")
    print(
        f"  Teff   : {binned['teff'].min():.0f} - {binned['teff'].max():.0f} K"
    )
    print(
        f"  log g  : {binned['logg'].min():.1f} - {binned['logg'].max():.1f}"
    )
    print(
        f"  [M/H]  : {binned['mh'].min():.1f} - {binned['mh'].max():.1f}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
