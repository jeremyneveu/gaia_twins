"""Tests for normalization module."""

import pytest
import numpy as np

from gaia_twins.utils.normalization import (
    normalize_spectrum,
    ambre_normalization,
    normalize_flux,
    continuum_normalize
)


class TestNormalizeSpectrum:
    """Test normalize_spectrum function."""
    
    def test_integral_normalization(self):
        """Test normalization by integral matching."""
        synth_wave = np.linspace(400, 700, 100)
        synth_flux = np.ones(100) * 2.0
        gaia_wave = np.linspace(400, 700, 100)
        gaia_flux = np.ones(100) * 1.0
        
        normalized = normalize_spectrum(
            synth_wave, synth_flux,
            gaia_wave, gaia_flux,
            method='integral'
        )
        
        # Normalized integral should match
        synth_int = np.trapz(normalized, synth_wave)
        gaia_int = np.trapz(gaia_flux, gaia_wave)
        assert np.isclose(synth_int, gaia_int, rtol=0.01)
    
    def test_median_normalization(self):
        """Test normalization by median matching."""
        synth_wave = np.linspace(400, 700, 100)
        synth_flux = np.ones(100) * 4.0
        gaia_wave = np.linspace(400, 700, 100)
        gaia_flux = np.ones(100) * 2.0
        
        normalized = normalize_spectrum(
            synth_wave, synth_flux,
            gaia_wave, gaia_flux,
            method='median'
        )
        
        # Normalized median should match
        assert np.isclose(np.median(normalized), np.median(gaia_flux), rtol=0.01)
    
    def test_peak_normalization(self):
        """Test normalization by peak matching."""
        synth_wave = np.linspace(400, 700, 100)
        synth_flux = np.sin(synth_wave / 50) + 2.0
        gaia_wave = np.linspace(400, 700, 100)
        gaia_flux = np.sin(gaia_wave / 50) + 1.0
        
        normalized = normalize_spectrum(
            synth_wave, synth_flux,
            gaia_wave, gaia_flux,
            method='peak'
        )
        
        # Normalized peak should match
        assert np.isclose(np.max(normalized), np.max(gaia_flux), rtol=0.01)
    
    def test_invalid_method_raises(self):
        """Test that invalid method raises ValueError."""
        synth_wave = np.linspace(400, 700, 100)
        synth_flux = np.ones(100)
        gaia_wave = np.linspace(400, 700, 100)
        gaia_flux = np.ones(100)
        
        with pytest.raises(ValueError, match="Unknown normalization method"):
            normalize_spectrum(
                synth_wave, synth_flux,
                gaia_wave, gaia_flux,
                method='invalid'
            )
    
    def test_different_wavelength_ranges(self):
        """Test with different wavelength ranges."""
        synth_wave = np.linspace(300, 800, 200)
        synth_flux = np.ones(200) * 2.0
        gaia_wave = np.linspace(400, 700, 100)
        gaia_flux = np.ones(100) * 1.0
        
        normalized = normalize_spectrum(
            synth_wave, synth_flux,
            gaia_wave, gaia_flux,
            method='integral'
        )
        
        # Should use common range [400, 700]
        assert len(normalized) == len(synth_wave)


class TestAmbreNormalization:
    """Test ambre_normalization function."""
    
    def test_normalization_factor(self):
        """Test that normalization factor is computed correctly."""
        ambre_wave = np.linspace(400, 700, 100)
        ambre_flux = np.ones(100) * 3.0
        gaia_wave = np.linspace(400, 700, 100)
        gaia_flux = np.ones(100) * 1.0
        
        factor = ambre_normalization(
            ambre_wave, ambre_flux,
            gaia_wave, gaia_flux
        )
        
        # Factor should be ratio of integrals
        ambre_int = np.trapz(ambre_flux, ambre_wave)
        gaia_int = np.trapz(gaia_flux, gaia_wave)
        expected_factor = gaia_int / ambre_int
        
        assert np.isclose(factor, expected_factor, rtol=0.01)
    
    def test_zero_flux_returns_one(self):
        """Test that zero flux returns factor of 1."""
        ambre_wave = np.linspace(400, 700, 100)
        ambre_flux = np.zeros(100)
        gaia_wave = np.linspace(400, 700, 100)
        gaia_flux = np.ones(100)
        
        factor = ambre_normalization(
            ambre_wave, ambre_flux,
            gaia_wave, gaia_flux
        )
        
        assert factor == 1.0


class TestNormalizeFlux:
    """Test normalize_flux function."""
    
    def test_median_normalization(self):
        """Test normalization to median."""
        flux = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        normalized = normalize_flux(flux, method='median', target_value=1.0)
        
        assert np.isclose(np.median(normalized), 1.0)
    
    def test_mean_normalization(self):
        """Test normalization to mean."""
        flux = np.array([2.0, 4.0, 6.0, 8.0, 10.0])
        normalized = normalize_flux(flux, method='mean', target_value=5.0)
        
        assert np.isclose(np.mean(normalized), 5.0)
    
    def test_max_normalization(self):
        """Test normalization to max."""
        flux = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        normalized = normalize_flux(flux, method='max', target_value=1.0)
        
        assert np.isclose(np.max(normalized), 1.0)
    
    def test_invalid_method_raises(self):
        """Test that invalid method raises ValueError."""
        flux = np.ones(10)
        
        with pytest.raises(ValueError, match="Unknown normalization method"):
            normalize_flux(flux, method='invalid')


class TestContinuumNormalize:
    """Test continuum_normalize function."""
    
    def test_basic_continuum_normalization(self):
        """Test basic continuum fitting and normalization."""
        wavelength = np.linspace(400, 700, 100)
        # Create spectrum with continuum trend
        continuum = 2.0 + 0.001 * wavelength
        absorption = np.exp(-((wavelength - 550) ** 2) / (2 * 10 ** 2))
        flux = continuum * (1 - 0.5 * absorption)
        
        normalized = continuum_normalize(
            wavelength, flux, poly_order=2, n_iterations=3, sigma_clip=3.0
        )
        
        # Normalized continuum regions should be close to 1
        # (avoiding the absorption line)
        continuum_regions = (wavelength < 500) | (wavelength > 600)
        assert np.mean(normalized[continuum_regions]) > 0.9
        assert np.mean(normalized[continuum_regions]) < 1.1
    
    def test_linear_continuum(self):
        """Test with linear continuum."""
        wavelength = np.linspace(400, 700, 50)
        flux = 1.0 + 0.002 * wavelength  # Linear trend
        
        normalized = continuum_normalize(
            wavelength, flux, poly_order=1, n_iterations=2
        )
        
        # After normalization, should be close to constant
        assert np.std(normalized) < 0.1
    
    def test_custom_parameters(self):
        """Test with custom parameters."""
        wavelength = np.linspace(400, 700, 100)
        flux = 2.0 + 0.001 * wavelength
        
        normalized = continuum_normalize(
            wavelength, flux,
            poly_order=1,
            n_iterations=1,
            sigma_clip=2.0
        )
        
        # Should still produce reasonable normalization
        assert len(normalized) == len(flux)
        assert not np.any(np.isnan(normalized))


class TestNormalizationEdgeCases:
    """Test edge cases for normalization."""
    
    def test_identical_spectra(self):
        """Test normalization of identical spectra."""
        wave = np.linspace(400, 700, 100)
        flux = np.ones(100)
        
        normalized = normalize_spectrum(
            wave, flux, wave, flux, method='integral'
        )
        
        # Should return nearly identical flux
        assert np.allclose(normalized, flux, rtol=0.01)
    
    def test_no_overlap(self):
        """Test with non-overlapping wavelength ranges."""
        synth_wave = np.linspace(300, 400, 50)
        synth_flux = np.ones(50)
        gaia_wave = np.linspace(500, 600, 50)
        gaia_flux = np.ones(50)
        
        # Should handle gracefully (likely return factor of 1)
        normalized = normalize_spectrum(
            synth_wave, synth_flux,
            gaia_wave, gaia_flux,
            method='integral'
        )
        
        # Factor should be 1 (no common range)
        assert np.allclose(normalized, synth_flux)
