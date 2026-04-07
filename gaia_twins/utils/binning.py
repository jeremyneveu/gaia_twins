"""Spectral binning utilities."""

import numpy as np
from scipy.stats import binned_statistic
from typing import Tuple


def bin_spectrum(
    wavelength: np.ndarray,
    flux: np.ndarray,
    bin_size: float = 1.0
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Bin a spectrum by wavelength bins.
    
    Parameters
    ----------
    wavelength : np.ndarray
        Wavelength array
    flux : np.ndarray
        Flux array
    bin_size : float
        Bin size in same units as wavelength
        
    Returns
    -------
    bin_centers : np.ndarray
        Centers of bins
    binned_flux : np.ndarray
        Mean flux in each bin
    """
    # Define bin edges
    wave_min = np.floor(np.min(wavelength))
    wave_max = np.ceil(np.max(wavelength))
    bin_edges = np.arange(wave_min, wave_max + bin_size, bin_size)
    
    # Use numpy histogram with weights
    flux_sum, _ = np.histogram(wavelength, bins=bin_edges, weights=flux)
    counts, _ = np.histogram(wavelength, bins=bin_edges)
    
    # Avoid division by zero
    with np.errstate(divide='ignore', invalid='ignore'):
        binned_flux = flux_sum / counts
        binned_flux[counts == 0] = np.nan
    
    # Centers of bins
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    
    return bin_centers, binned_flux


def bin_spectrum_scipy(
    wavelength: np.ndarray,
    flux: np.ndarray,
    bin_size: float = 1.0
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Bin a spectrum using scipy.stats.binned_statistic.
    
    More robust and feature-rich than simple binning.
    
    Parameters
    ----------
    wavelength : np.ndarray
        Wavelength array
    flux : np.ndarray
        Flux array
    bin_size : float
        Bin size in same units as wavelength
        
    Returns
    -------
    bin_centers : np.ndarray
        Centers of bins
    binned_flux : np.ndarray
        Mean flux in each bin
    """
    # Define bin edges
    wave_min = np.floor(np.min(wavelength))
    wave_max = np.ceil(np.max(wavelength))
    bin_edges = np.arange(wave_min, wave_max + bin_size, bin_size)
    
    # Bin the data
    binned_flux, edges, _ = binned_statistic(
        wavelength, 
        flux,
        statistic='mean',
        bins=bin_edges
    )
    
    # Centers of bins
    bin_centers = (edges[:-1] + edges[1:]) / 2
    
    return bin_centers, binned_flux


def rebin_spectrum(
    wavelength: np.ndarray,
    flux: np.ndarray,
    new_wavelength: np.ndarray,
    method: str = 'linear'
) -> np.ndarray:
    """
    Rebin spectrum to a new wavelength grid.
    
    Parameters
    ----------
    wavelength : np.ndarray
        Original wavelength array
    flux : np.ndarray
        Original flux array
    new_wavelength : np.ndarray
        Target wavelength grid
    method : str
        Interpolation method: 'linear', 'cubic', 'nearest'
        
    Returns
    -------
    np.ndarray
        Flux on new wavelength grid
    """
    from scipy.interpolate import interp1d
    
    # Create interpolation function
    f = interp1d(
        wavelength,
        flux,
        kind=method,
        bounds_error=False,
        fill_value=np.nan
    )
    
    # Interpolate to new grid
    new_flux = f(new_wavelength)
    
    return new_flux


def adaptive_bin(
    wavelength: np.ndarray,
    flux: np.ndarray,
    target_snr: float = 10.0,
    flux_error: Optional[np.ndarray] = None
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Adaptive binning to achieve target SNR.
    
    Parameters
    ----------
    wavelength : np.ndarray
        Wavelength array
    flux : np.ndarray
        Flux array
    target_snr : float
        Target signal-to-noise ratio
    flux_error : np.ndarray, optional
        Flux error array. If None, assumed Poisson noise.
        
    Returns
    -------
    bin_centers : np.ndarray
        Centers of bins
    binned_flux : np.ndarray
        Binned flux
    binned_error : np.ndarray
        Binned flux error
    """
    if flux_error is None:
        # Assume Poisson noise
        flux_error = np.sqrt(np.abs(flux))
    
    bins = []
    bin_flux = []
    bin_error = []
    
    i = 0
    while i < len(wavelength):
        j = i + 1
        current_flux = flux[i]
        current_error = flux_error[i]
        current_snr = current_flux / current_error if current_error > 0 else 0
        
        # Accumulate bins until target SNR is reached
        while j < len(wavelength) and current_snr < target_snr:
            # Add next pixel
            weight_i = 1.0 / (current_error**2) if current_error > 0 else 0
            weight_j = 1.0 / (flux_error[j]**2) if flux_error[j] > 0 else 0
            total_weight = weight_i + weight_j
            
            if total_weight > 0:
                current_flux = (current_flux * weight_i + flux[j] * weight_j) / total_weight
                current_error = 1.0 / np.sqrt(total_weight)
                current_snr = current_flux / current_error
            
            j += 1
        
        # Store bin
        bin_center = np.mean(wavelength[i:j])
        bins.append(bin_center)
        bin_flux.append(current_flux)
        bin_error.append(current_error)
        
        i = j
    
    return np.array(bins), np.array(bin_flux), np.array(bin_error)
