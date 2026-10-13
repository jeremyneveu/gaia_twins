"""Command-line interface for gaia-twins."""

import argparse
import sys
import logging
from pathlib import Path
from typing import List, Optional

import pandas as pd

from ..src.spectrum_generator import SyntheticSpectrumGenerator


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def read_source_ids(input_file: str) -> List[int]:
    """
    Read Gaia source IDs from a text, CSV or parquet file.

    Supports:
    - Text files with one ID per line
    - CSV / parquet files with a 'source_id' column

    Returns
    -------
    List[int]
        Parsed source IDs (validated).
    """
    input_path = Path(input_file)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    suffix = input_path.suffix.lower()

    if suffix == ".csv":
        df = pd.read_csv(input_file)
        if "source_id" not in df.columns:
            raise ValueError("CSV file must contain a 'source_id' column")
        source_ids = df["source_id"].tolist()
    elif suffix == ".parquet":
        df = pd.read_parquet(input_file)
        if "source_id" not in df.columns:
            raise ValueError("Parquet file must contain a 'source_id' column")
        source_ids = df["source_id"].tolist()
    else:
        with open(input_file, "r") as fh:
            source_ids = [line.strip() for line in fh if line.strip()]

    return source_ids


def save_results(results: pd.DataFrame, output_file: str, output_format: str) -> None:
    """
    Save a spectra DataFrame to disk.

    Parameters
    ----------
    results : pd.DataFrame
        DataFrame of generated spectra (indexed by ``source_id``).
    output_file : str
        Destination path.
    output_format : str
        One of ``"pickle"``, ``"parquet"`` or ``"csv"``.
    """
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fmt = (output_format or "parquet").lower()

    if fmt in ("pickle", "pkl"):
        results.to_pickle(output_file)
    elif fmt == "parquet":
        # Parquet supports list columns via Arrow; keep arrays for pickling.
        try:
            results.to_parquet(output_file, index=True)
        except (ValueError, NotImplementedError):
            meta_cols = [c for c in results.columns if not c.startswith("synth_")]
            results[meta_cols].to_parquet(output_file, index=True)
            logging.warning(
                "Saving only metadata columns to parquet; use pickle to retain spectra."
            )
    elif fmt in ("csv",):
        meta_cols = [c for c in results.columns if not c.startswith("synth_")]
        results[meta_cols].to_csv(output_file)
    elif fmt in ("hdf5", "h5"):
        meta_cols = [c for c in results.columns if not c.startswith("synth_")]
        results[meta_cols].to_hdf(output_file, key="spectra", mode="w")
    else:
        raise ValueError(f"Unsupported output format: {output_format}")

    logging.info("Results saved to %s", output_file)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="gaia-twins",
        description=(
            "Generate high-resolution synthetic 'twin' spectra for Gaia stars "
            "from AMBRE stellar atmosphere models."
        ),
    )

    # Input sources
    parser.add_argument(
        "-i", "--input", type=str, default=None,
        help="File containing Gaia source IDs (text/csv/parquet).",
    )
    parser.add_argument(
        "-s", "--source-ids", type=str, nargs="+", default=None,
        help="One or more Gaia source IDs on the command line.",
    )

    # Output
    parser.add_argument(
        "-o", "--output", type=str, default="twin_spectra.pkl",
        help="Output file path (default: twin_spectra.pkl).",
    )
    parser.add_argument(
        "-f", "--format", type=str, default="pickle",
        choices=["pickle", "parquet", "csv", "hdf5"],
        help="Output format (default: pickle).",
    )

    # AMBRE data
    parser.add_argument(
        "-a", "--ambre-dir", type=str, default=None,
        help=(
            "Directory containing AMBRE data (ZIP files). Defaults to the "
            "pre-binned grid shipped with the package."
        ),
    )
    parser.add_argument(
        "--parquet", type=str, default=None,
        help=(
            "Path to a pre-binned AMBRE parquet grid. Defaults to the grid "
            "bundled with the package when available. Recommended for speed."
        ),
    )
    parser.add_argument(
        "--cache-dir", type=str, default=None,
        help=(
            "Directory used to cache the processed AMBRE grid and fetched Gaia "
            "parameters (default: user cache)."
        ),
    )

    # Wavelength grid (Angstroms)
    parser.add_argument(
        "--wave-min", type=float, default=3000.0,
        help="Minimum wavelength for the ZIP-path grid (Angstroms, default 3000).",
    )
    parser.add_argument(
        "--wave-max", type=float, default=11000.0,
        help="Maximum wavelength for the ZIP-path grid (Angstroms, default 11000).",
    )
    parser.add_argument(
        "--wave-step", type=float, default=10.0,
        help="Wavelength bin width (Angstroms, default 10).",
    )

    # Interpolation
    parser.add_argument(
        "--interp-method", type=str, default="linear",
        choices=["linear", "nearest"],
        help="Interpolation method (default: linear).",
    )
    parser.add_argument(
        "--n-neighbors", type=int, default=None,
        help="Deprecated; kept for compatibility (unused).",
    )

    # Gaia query
    parser.add_argument(
        "--batch-size", type=int, default=1000,
        help="Batch size for Gaia queries (default: 1000).",
    )
    parser.add_argument(
        "--gspspec", action="store_true",
        help="Use GSP-Spec (rather than GSP-Phot) stellar parameters.",
    )

    # Other
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose logging output.",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point of the gaia-twins command-line tool."""
    parser = build_parser()
    args = parser.parse_args(argv)

    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    if not args.input and not args.source_ids:
        parser.error("Provide source IDs via -i/--input or -s/--source-ids.")

    try:
        # Resolve source IDs
        if args.input:
            logger.info("Reading source IDs from %s", args.input)
            source_ids = read_source_ids(args.input)
        else:
            source_ids = [int(sid) for sid in args.source_ids]
        logger.info("Processing %d source IDs", len(source_ids))

        # Build the generator and load the AMBRE grid
        generator = SyntheticSpectrumGenerator(
            ambre_dir=args.ambre_dir,
            cache_dir=args.cache_dir,
            interpolation_method=args.interp_method,
            n_neighbors=args.n_neighbors,
        )
        logger.info("Preparing AMBRE data...")
        generator.prepare_ambre(
            parquet_path=args.parquet,
            wavelength_min=args.wave_min,
            wavelength_max=args.wave_max,
            wavelength_step=args.wave_step,
        )

        # Generate twin spectra
        logger.info("Generating twin spectra...")
        results = generator.generate_twins(source_ids, use_gspspec=args.gspspec)
        logger.info("Generated %d results", len(results))

        save_results(results, args.output, args.format)

        # Summary
        found = results["twin_filename"].notna().sum() if "twin_filename" in results else 0
        logger.info("Summary:")
        logger.info("  Input source IDs: %d", len(source_ids))
        logger.info("  Results: %d", len(results))
        logger.info("  Twins found: %d", found)
        logger.info("  Output file: %s", args.output)
        return 0

    except Exception as e:  # noqa: BLE001
        logger.error("Error: %s", e, exc_info=args.verbose)
        return 1


if __name__ == "__main__":
    sys.exit(main())

