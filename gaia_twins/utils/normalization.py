"""Spectrum normalization utilities."""

import numpy as np
from typing import Optional


def normalize_spectrum(
    synth_wave: np.ndarray,
    synth_flux: np.ndarray,
    gaia_wave: np.ndarray,
    gaia_flux: np.ndarray,
    method: str = 'integral'
) -> np.ndarray:
    """
    Normalize synthetic spectrum to match Gaia spectrum.
    
    Parameters
    ----------
    synth_wave : np.ndarray
        Synthetic spectrum wavelengths
    synth_flux : np.ndarray
        Synthetic spectrum flux
    gaia_wave : np.ndarray
        Gaia spectrum wavelengths
    gaia_flux : np.ndarray
        Gaia spectrum flux
    method : str
        Normalization method: 'integral', 'median', or 'peak'
        
    Returns
    -------
    np.ndarray
        Normalized synthetic flux
    """
    # Find common wavelength range
    wave_min = max(np.min(synth_wave), np.min(gaia_wave))
    wave_max = min(np.max(synth_wave), np.max(gaia_wave))
    
    # Mask for common range
    synth_mask = (synth_wave >= wave_min) & (synth_wave <= wave_max)
    gaia_mask = (gaia_wave >= wave_min) & (gaia_wave <= wave_max)
    
    synth_wave_common = synth_wave[synth_mask]
    synth_flux_common = synth_flux[synth_mask]
    gaia_wave_common = gaia_wave[gaia_mask]
    gaia_flux_common = gaia_flux[gaia_mask]
    
    # Calculate normalization factor
    if method == 'integral':
        # Match integrated flux
        synth_integral = np.trapezoid(synth_flux_common, x=synth_wave_common)
        gaia_integral = np.trapezoid(gaia_flux_common, x=gaia_wave_common)
        
        if synth_integral > 0:
            norm_factor = gaia_integral / synth_integral
        else:
            norm_factor = 1.0
            
    elif method == 'median':
        # Match median flux
        synth_median = np.median(synth_flux_common)
        gaia_median = np.median(gaia_flux_common)
        
        if synth_median > 0:
            norm_factor = gaia_median / synth_median
        else:
            norm_factor = 1.0
            
    elif method == 'peak':
        # Match peak flux
        synth_peak = np.max(synth_flux_common)
        gaia_peak = np.max(gaia_flux_common)
        
        if synth_peak > 0:
            norm_factor = gaia_peak / synth_peak
        else:
            norm_factor = 1.0
            
    else:
        raise ValueError(f"Unknown normalization method: {method}")
    
    return synth_flux * norm_factor


def ambre_normalization(
    ambre_wave: np.ndarray,
    ambre_flux: np.ndarray,
    gaia_wave: np.ndarray,
    gaia_flux: np.ndarray
) -> float:
    """
    Calculate normalization factor for AMBRE spectrum.
    
    This is a convenience function that returns only the normalization factor.
    
    Parameters
    ----------
    ambre_wave : np.ndarray
        AMBRE wavelengths
    ambre_flux : np.ndarray
        AMBRE flux
    gaia_wave : np.ndarray
        Gaia wavelengths
    gaia_flux : np.ndarray
        Gaia flux
        
    Returns
    -------
    float
        Normalization factor
    """
    # Find common wavelength range
    wave_min = max(np.min(ambre_wave), np.min(gaia_wave))
    wave_max = min(np.max(ambre_wave), np.max(gaia_wave))
    
    # Mask for common range
    ambre_mask = (ambre_wave >= wave_min) & (ambre_wave <= wave_max)
    gaia_mask = (gaia_wave >= wave_min) & (gaia_wave <= wave_max)
    
    ambre_wave_common = ambre_wave[ambre_mask]
    ambre_flux_common = ambre_flux[ambre_mask]
    gaia_wave_common = gaia_wave[gaia_mask]
    gaia_flux_common = gaia_flux[gaia_mask]
    
    # Calculate integrals
    ambre_integral = np.trapz(ambre_flux_common, ambre_wave_common)
    gaia_integral = np.trapz(gaia_flux_common, gaia_wave_common)
    
    if ambre_integral > 0:
        return gaia_integral / ambre_integral
    else:
        return 1.0


def normalize_flux(
    flux: np.ndarray,
    method: str = 'median',
    target_value: float = 1.0
) -> np.ndarray:
    """
    Normalize flux array to a target value.
    
    Parameters
    ----------
    flux : np.ndarray
        Flux array
    method : str
        Normalization method: 'median', 'mean', 'max'
    target_value : float
        Target normalization value
        
    Returns
    -------
    np.ndarray
        Normalized flux
    """
    if method == 'median':
        norm = np.median(flux)
    elif method == 'mean':
        norm = np.mean(flux)
    elif method == 'max':
        norm = np.max(flux)
    else:
        raise ValueError(f"Unknown normalization method: {method}")
    
    if norm > 0:
        return flux * (target_value / norm)
    else:
        return flux


def continuum_normalize(
    wavelength: np.ndarray,
    flux: np.ndarray,
    poly_order: int = 3,
    n_iterations: int = 3,
    sigma_clip: float = 3.0
) -> np.ndarray:
    """
    Normalize spectrum by fitting continuum.
    
    Uses iterative polynomial fitting with sigma clipping.
    
    Parameters
    ----------
    wavelength : np.ndarray
        Wavelength array
    flux : np.ndarray
        Flux array
    poly_order : int
        Polynomial order for continuum fit
    n_iterations : int
        Number of sigma-clipping iterations
    sigma_clip : float
        Sigma threshold for clipping
        
    Returns
    -------
    np.ndarray
        Continuum-normalized flux
    """
    # Initial fit
    mask = np.ones(len(flux), dtype=bool)
    
    for _ in range(n_iterations):
        # Fit polynomial to unmasked points
        coeffs = np.polyfit(wavelength[mask], flux[mask], poly_order)
        continuum = np.polyval(coeffs, wavelength)
        
        # Calculate residuals
        residuals = flux - continuum
        sigma = np.std(residuals[mask])
        
        # Update mask (keep points within sigma_clip * sigma)
        mask = np.abs(residuals) < sigma_clip * sigma
    
    # Final continuum fit
    coeffs = np.polyfit(wavelength[mask], flux[mask], poly_order)
    continuum = np.polyval(coeffs, wavelength)
    
    # Normalize
    normalized_flux = flux / continuum
    
    return normalized_flux
