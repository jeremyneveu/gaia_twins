"""Command-line interface for gaia-synth-spectra."""

import argparse
import sys
import logging
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

from ..src.spectrum_generator import SyntheticSpectrumGenerator
from ..utils.validators import (
    validate_source_ids,
    validate_wavelength_range,
    validate_output_format,
    validate_interpolation_method
)


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def read_source_ids(input_file: str) -> List[int]:
    """
    Read Gaia source IDs from file.
    
    Supports:
    - Text files with one ID per line
    - CSV files with 'source_id' column
    - Parquet files with 'source_id' column
    
    Parameters
    ----------
    input_file : str
        Path to input file
        
    Returns
    -------
    List[int]
        List of source IDs
    """
    input_path = Path(input_file)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    suffix = input_path.suffix.lower()
    
    if suffix == '.csv':
        df = pd.read_csv(input_file)
        if 'source_id' not in df.columns:
            raise ValueError("CSV file must contain 'source_id' column")
        source_ids = df['source_id'].tolist()
        
    elif suffix == '.parquet':
        df = pd.read_parquet(input_file)
        if 'source_id' not in df.columns:
            raise ValueError("Parquet file must contain 'source_id' column")
        source_ids = df['source_id'].tolist()
        
    else:
        # Assume text file with one ID per line
        with open(input_file, 'r') as f:
            source_ids = [line.strip() for line in f if line.strip()]
    
    return validate_source_ids(source_ids)


def save_results(
    results: pd.DataFrame,
    output_file: str,
    output_format: str
):
    """
    Save results to file.
    
    Parameters
    ----------
    results : pd.DataFrame
        Results DataFrame
    output_file : str
        Output file path
    output_format : str
        Output format
    """
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    format_lower = output_format.lower()
    
    if format_lower in ['pickle', 'pkl']:
        results.to_pickle(output_file)
        
    elif format_lower == 'parquet':
        # For parquet, need to exclude array columns
        meta_cols = [col for col in results.columns 
                     if not col.startswith('synth_')]
        results[meta_cols].to_parquet(output_file)
        logging.warning(
            "Parquet format does not support array columns. "
            "Only metadata saved. Use pickle format to save spectra."
        )
        
    elif format_lower in ['hdf5', 'h5']:
        results.to_hdf(output_file, key='spectra', mode='w')
        
    elif format_lower == 'csv':
        # For CSV, need to exclude array columns
        meta_cols = [col for col in results.columns 
                     if not col.startswith('synth_')]
        results[meta_cols].to_csv(output_file, index=False)
        logging.warning(
            "CSV format does not support array columns. "
            "Only metadata saved. Use pickle format to save spectra."
        )
    
    logging.info(f"Results saved to {output_file}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Generate synthetic stellar spectra from Gaia source IDs',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Input/Output
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '-i', '--input',
        type=str,
        help='Input file with source IDs (CSV, Parquet, or text file)'
    )
    input_group.add_argument(
        '-s', '--source-ids',
        type=str,
        nargs='+',
        help='Gaia source IDs (space-separated)'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        required=True,
        help='Output file path'
    )
    
    parser.add_argument(
        '-f', '--format',
        type=str,
        default='pickle',
        choices=['pickle', 'pkl', 'parquet', 'hdf5', 'h5', 'csv'],
        help='Output file format'
    )
    
    # AMBRE configuration
    parser.add_argument(
        '-a', '--ambre-dir',
        type=str,
        required=True,
        help='Directory containing AMBRE ZIP files'
    )
    
    parser.add_argument(
        '--ambre-cache',
        type=str,
        default=None,
        help='Path to AMBRE cache file (pickle)'
    )
    
    # Wavelength configuration
    parser.add_argument(
        '--wave-min',
        type=float,
        default=330.0,
        help='Minimum wavelength (nm)'
    )
    
    parser.add_argument(
        '--wave-max',
        type=float,
        default=1050.0,
        help='Maximum wavelength (nm)'
    )
    
    parser.add_argument(
        '--wave-step',
        type=float,
        default=0.5,
        help='Wavelength step (nm)'
    )
    
    # Interpolation
    parser.add_argument(
        '--interp-method',
        type=str,
        default='knn',
        choices=['knn', 'kdtree'],
        help='Interpolation method'
    )
    
    parser.add_argument(
        '--n-neighbors',
        type=int,
        default=4,
        help='Number of neighbors for KNN interpolation'
    )
    
    # Gaia query
    parser.add_argument(
        '--batch-size',
        type=int,
        default=1000,
        help='Batch size for Gaia queries'
    )
    
    # Other options
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    try:
        # Read source IDs
        if args.input:
            logger.info(f"Reading source IDs from {args.input}")
            source_ids = read_source_ids(args.input)
        else:
            source_ids = validate_source_ids(args.source_ids)
        
        logger.info(f"Processing {len(source_ids)} source IDs")
        
        # Validate wavelength range
        wave_min, wave_max, wave_step = validate_wavelength_range(
            args.wave_min, args.wave_max, args.wave_step
        )
        
        # Validate output format
        output_format = validate_output_format(args.format)
        
        # Validate interpolation method
        interp_method = validate_interpolation_method(args.interp_method)
        
        # Create generator
        logger.info("Initializing spectrum generator...")
        generator = SyntheticSpectrumGenerator(
            ambre_dir=args.ambre_dir,
            wavelength_min=wave_min,
            wavelength_max=wave_max,
            wavelength_step=wave_step,
            interpolation_method=interp_method,
            n_neighbors=args.n_neighbors,
            batch_size=args.batch_size
        )
        
        # Prepare AMBRE data
        logger.info("Loading AMBRE spectra...")
        generator.prepare_ambre(cache_file=args.ambre_cache)
        
        # Generate spectra
        logger.info("Generating synthetic spectra...")
        results = generator.generate_spectra(source_ids)
        
        logger.info(f"Successfully generated {len(results)} spectra")
        
        # Save results
        save_results(results, args.output, output_format)
        
        # Print summary
        logger.info("\nSummary:")
        logger.info(f"  Input source IDs: {len(source_ids)}")
        logger.info(f"  Generated spectra: {len(results)}")
        logger.info(f"  Wavelength range: {wave_min:.1f} - {wave_max:.1f} nm")
        logger.info(f"  Wavelength step: {wave_step:.2f} nm")
        logger.info(f"  Output file: {args.output}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=args.verbose)
        return 1


if __name__ == '__main__':
    sys.exit(main())
