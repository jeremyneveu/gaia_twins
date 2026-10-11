"""Input validation utilities."""

import numpy as np
import re
from typing import List, Union, Tuple, Optional


def validate_source_ids(source_ids: Union[List[str], List[int], np.ndarray]) -> List[int]:
    """
    Validate and convert Gaia source IDs to list of integers.
    
    Parameters
    ----------
    source_ids : Union[List[str], List[int], np.ndarray]
        Gaia DR3 source IDs
        
    Returns
    -------
    List[int]
        Validated list of source IDs as integers
        
    Raises
    ------
    ValueError
        If source IDs are invalid
    """
    if isinstance(source_ids, np.ndarray):
        source_ids = source_ids.tolist()
    
    if not isinstance(source_ids, list):
        raise ValueError("source_ids must be a list or numpy array")
    
    if len(source_ids) == 0:
        raise ValueError("source_ids cannot be empty")
    
    validated_ids = []
    for sid in source_ids:
        try:
            # Convert to int
            sid_int = int(sid)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid source ID: {sid}") from e

        # Gaia DR3 source IDs must be strictly positive
        if sid_int <= 0:
            raise ValueError(f"Invalid source ID: {sid} (must be positive)")

        validated_ids.append(sid_int)

    return validated_ids


def validate_wavelength_range(
    wavelength_min: Optional[float] = None,
    wavelength_max: Optional[float] = None,
    wavelength_step: Optional[float] = None
) -> Tuple[float, float, float]:
    """
    Validate wavelength range parameters.
    
    Parameters
    ----------
    wavelength_min : float, optional
        Minimum wavelength in nm (default: 330)
    wavelength_max : float, optional
        Maximum wavelength in nm (default: 1050)
    wavelength_step : float, optional
        Wavelength step in nm (default: 0.5)
        
    Returns
    -------
    Tuple[float, float, float]
        Validated (wavelength_min, wavelength_max, wavelength_step)
        
    Raises
    ------
    ValueError
        If wavelength parameters are invalid
    """
    # Set defaults
    if wavelength_min is None:
        wavelength_min = 330.0
    if wavelength_max is None:
        wavelength_max = 1050.0
    if wavelength_step is None:
        wavelength_step = 0.5
    
    # Validate types
    try:
        wavelength_min = float(wavelength_min)
        wavelength_max = float(wavelength_max)
        wavelength_step = float(wavelength_step)
    except (ValueError, TypeError) as e:
        raise ValueError("Wavelength parameters must be numeric") from e
    
    # Validate range
    if wavelength_min <= 0:
        raise ValueError(f"wavelength_min must be positive, got {wavelength_min}")
    
    if wavelength_max <= wavelength_min:
        raise ValueError(
            f"wavelength_max ({wavelength_max}) must be greater than "
            f"wavelength_min ({wavelength_min})"
        )
    
    if wavelength_step <= 0:
        raise ValueError(f"wavelength_step must be positive, got {wavelength_step}")
    
    if wavelength_step > (wavelength_max - wavelength_min):
        raise ValueError(
            f"wavelength_step ({wavelength_step}) is larger than wavelength range "
            f"({wavelength_max - wavelength_min})"
        )
    
    return wavelength_min, wavelength_max, wavelength_step


def validate_stellar_params(
    teff: Optional[float] = None,
    logg: Optional[float] = None,
    mh: Optional[float] = None,
    check_bounds: bool = False
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """
    Validate stellar atmospheric parameters.
    
    Parameters
    ----------
    teff : float, optional
        Effective temperature in K
    logg : float, optional
        Surface gravity in log10(cm/s²)
    mh : float, optional
        Metallicity [M/H] in dex
    check_bounds : bool
        If True, check if parameters are within typical ranges
        
    Returns
    -------
    Tuple[Optional[float], Optional[float], Optional[float]]
        Validated (teff, logg, mh)
        
    Raises
    ------
    ValueError
        If parameters are invalid
    """
    # Validate Teff
    if teff is not None:
        try:
            teff = float(teff)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid Teff: {teff}") from e
        
        if teff <= 0:
            raise ValueError(f"Teff must be positive, got {teff}")
        
        if check_bounds:
            if teff < 2500 or teff > 8000:
                raise ValueError(
                    f"Teff ({teff} K) outside typical range [2500, 8000] K"
                )
    
    # Validate log g
    if logg is not None:
        try:
            logg = float(logg)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid log g: {logg}") from e
        
        if check_bounds:
            if logg < 0 or logg > 6:
                raise ValueError(
                    f"log g ({logg}) outside typical range [0, 6]"
                )
    
    # Validate [M/H]
    if mh is not None:
        try:
            mh = float(mh)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid [M/H]: {mh}") from e
        
        if check_bounds:
            if mh < -5 or mh > 1:
                raise ValueError(
                    f"[M/H] ({mh}) outside typical range [-5, 1]"
                )
    
    return teff, logg, mh


def validate_interpolation_method(method: str) -> str:
    """
    Validate interpolation method.
    
    Parameters
    ----------
    method : str
        Interpolation method
        
    Returns
    -------
    str
        Validated method (lowercase)
        
    Raises
    ------
    ValueError
        If method is not supported
    """
    method = method.lower()
    
    # 'nearest' (RegularGridInterpolator) is the direct equivalent of the
    # former KNN/KD-tree nearest-neighbour schemes; all four spellings are
    # accepted for backwards compatibility.
    valid_methods = ['linear', 'nearest', 'knn', 'kdtree']
    
    if method not in valid_methods:
        raise ValueError(
            f"Invalid interpolation method: {method}. "
            f"Must be one of {valid_methods}"
        )
    
    return method


def validate_output_format(format_str: str) -> str:
    """
    Validate output file format.
    
    Parameters
    ----------
    format_str : str
        Output format
        
    Returns
    -------
    str
        Validated format (lowercase)
        
    Raises
    ------
    ValueError
        If format is not supported
    """
    format_str = format_str.lower()
    
    valid_formats = ['pickle', 'pkl', 'parquet', 'hdf5', 'h5', 'csv']
    
    if format_str not in valid_formats:
        raise ValueError(
            f"Invalid output format: {format_str}. "
            f"Must be one of {valid_formats}"
        )
    
    return format_str


def validate_file_path(file_path: str, must_exist: bool = False) -> str:
    """
    Validate file path.
    
    Parameters
    ----------
    file_path : str
        Path to file
    must_exist : bool
        If True, check if file exists
        
    Returns
    -------
    str
        Validated file path
        
    Raises
    ------
    ValueError
        If file path is invalid
    FileNotFoundError
        If must_exist=True and file doesn't exist
    """
    import os
    
    if not isinstance(file_path, str):
        raise ValueError("file_path must be a string")
    
    if not file_path:
        raise ValueError("file_path cannot be empty")
    
    if must_exist and not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    return file_path


def validate_batch_size(batch_size: int) -> int:
    """
    Validate batch size parameter.
    
    Parameters
    ----------
    batch_size : int
        Batch size
        
    Returns
    -------
    int
        Validated batch size
        
    Raises
    ------
    ValueError
        If batch size is invalid
    """
    try:
        batch_size = int(batch_size)
    except (ValueError, TypeError) as e:
        raise ValueError(f"batch_size must be an integer, got {batch_size}") from e
    
    if batch_size <= 0:
        raise ValueError(f"batch_size must be positive, got {batch_size}")
    
    if batch_size > 10000:
        raise ValueError(
            f"batch_size ({batch_size}) is very large. "
            f"Consider using smaller batches (< 10000)"
        )
    
    return batch_size
