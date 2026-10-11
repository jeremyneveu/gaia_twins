"""Tests for binning module."""

import pytest
import numpy as np

from gaia_twins.utils.binning import (
    bin_spectrum,
    bin_spectrum_scipy,
    rebin_spectrum,
    adaptive_bin
)


class TestBinSpectrum:
    """Test bin_spectrum function."""
    
    def test_basic_binning(self):
        """Test basic spectrum binning."""
        wavelength = np.linspace(400, 700, 1000)
        flux = np.sin(wavelength / 100) + 2.0
        
        wave_binned, flux_binned = bin_spectrum(
            wavelength, flux,
            wave_min=400, wave_max=700, wave_step=10
        )
        
        assert len(wave_binned) == len(flux_binned)
        assert wave_binned[0] >= 400
        assert wave_binned[-1] <= 700
        assert np.all(np.diff(wave_binned) > 0)  # Monotonic increasing
    
    def test_custom_statistic(self):
        """Test with different statistics."""
        wavelength = np.linspace(400, 500, 100)
        flux = np.ones(100) * 5.0
        
        wave_mean, flux_mean = bin_spectrum(
            wavelength, flux,
            wave_min=400, wave_max=500, wave_step=10,
            statistic='mean'
        )
        
        # With constant flux, mean should equal the constant value
        assert np.allclose(flux_mean, 5.0)
    
    def test_empty_input_raises(self):
        """Test that empty input raises ValueError."""
        with pytest.raises(ValueError):
            bin_spectrum(np.array([]), np.array([]))


class TestBinSpectrumScipy:
    """Test bin_spectrum_scipy function."""
    
    def test_basic_binning_scipy(self):
        """Test basic binning with scipy."""
        wavelength = np.linspace(400, 700, 1000)
        flux = np.sin(wavelength / 100) + 2.0
        
        wave_binned, flux_binned = bin_spectrum_scipy(
            wavelength, flux,
            wave_min=400, wave_max=700, wave_step=10
        )
        
        assert len(wave_binned) == len(flux_binned)
        assert wave_binned[0] >= 400
        assert wave_binned[-1] <= 700
    
    def test_median_statistic(self):
        """Test median statistic."""
        wavelength = np.linspace(400, 500, 100)
        flux = np.random.randn(100) + 10.0
        
        wave_median, flux_median = bin_spectrum_scipy(
            wavelength, flux,
            wave_min=400, wave_max=500, wave_step=50,
            statistic='median'
        )
        
        # Median should be close to 10 for random normal data
        assert np.all(flux_median > 8) and np.all(flux_median < 12)


class TestRebinSpectrum:
    """Test rebin_spectrum function."""
    
    def test_basic_rebinning(self):
        """Test basic spectrum rebinning."""
        wavelength = np.linspace(400, 700, 300)
        flux = np.sin(wavelength / 100) + 2.0
        
        new_wavelength = np.linspace(450, 650, 100)
        flux_rebinned = rebin_spectrum(wavelength, flux, new_wavelength)
        
        assert len(flux_rebinned) == len(new_wavelength)
        assert not np.any(np.isnan(flux_rebinned))
    
    def test_linear_interpolation(self):
        """Test that linear interpolation works correctly."""
        wavelength = np.array([400.0, 500.0, 600.0])
        flux = np.array([1.0, 2.0, 3.0])
        
        new_wavelength = np.array([450.0, 550.0])
        flux_rebinned = rebin_spectrum(
            wavelength, flux, new_wavelength, method='linear'
        )
        
        # Should get midpoint values
        assert np.allclose(flux_rebinned, [1.5, 2.5])
    
    def test_extrapolation_fills_value(self):
        """Test that extrapolation uses fill_value."""
        wavelength = np.array([400.0, 500.0, 600.0])
        flux = np.array([1.0, 2.0, 3.0])
        
        new_wavelength = np.array([350.0, 450.0, 650.0])
        flux_rebinned = rebin_spectrum(
            wavelength, flux, new_wavelength, fill_value=0.0
        )
        
        # First and last should be fill value
        assert flux_rebinned[0] == 0.0
        assert flux_rebinned[2] == 0.0
        assert flux_rebinned[1] == 1.5  # Interpolated


class TestAdaptiveBin:
    """Test adaptive_bin function."""
    
    def test_basic_adaptive_binning(self):
        """Test basic adaptive binning."""
        wavelength = np.linspace(400, 700, 1000)
        flux = np.ones(1000) * 10.0
        error = np.ones(1000) * 1.0  # SNR = 10
        
        wave_binned, flux_binned, error_binned = adaptive_bin(
            wavelength, flux, error, target_snr=15
        )
        
        assert len(wave_binned) == len(flux_binned)
        assert len(wave_binned) == len(error_binned)
        assert len(wave_binned) < len(wavelength)  # Should have fewer bins
    
    def test_high_snr_no_binning(self):
        """Test that high SNR data isn't binned much."""
        wavelength = np.linspace(400, 500, 100)
        flux = np.ones(100) * 100.0
        error = np.ones(100) * 1.0  # SNR = 100
        
        wave_binned, flux_binned, error_binned = adaptive_bin(
            wavelength, flux, error, target_snr=10
        )
        
        # Should have similar length (minimal binning)
        assert len(wave_binned) >= 90
    
    def test_max_bin_size_limit(self):
        """Test that max_bin_size is respected."""
        wavelength = np.linspace(400, 700, 1000)
        flux = np.ones(1000) * 1.0
        error = np.ones(1000) * 10.0  # Very low SNR
        
        wave_binned, flux_binned, error_binned = adaptive_bin(
            wavelength, flux, error, target_snr=100, max_bin_size=5
        )
        
        # Should still produce some bins despite low SNR
        assert len(wave_binned) > 50


class TestBinningEdgeCases:
    """Test edge cases for binning functions."""
    
    def test_single_point_spectrum(self):
        """Test with single point."""
        wavelength = np.array([500.0])
        flux = np.array([1.0])
        
        # Should handle gracefully
        wave_binned, flux_binned = bin_spectrum(
            wavelength, flux,
            wave_min=400, wave_max=600, wave_step=50
        )
        
        assert len(wave_binned) >= 0
    
    def test_unsorted_wavelength(self):
        """Test with unsorted wavelength array."""
        wavelength = np.array([500, 400, 600, 450])
        flux = np.array([1, 2, 3, 4])
        
        # Should handle by sorting internally or raising error
        # Implementation dependent
        try:
            wave_binned, flux_binned = bin_spectrum(
                wavelength, flux,
                wave_min=400, wave_max=600, wave_step=50
            )
            # If it works, output should be sorted
            assert np.all(np.diff(wave_binned) >= 0)
        except ValueError:
            # Or it might raise an error - both acceptable
            pass
    
    def test_nan_values(self):
        """Test handling of NaN values."""
        wavelength = np.linspace(400, 700, 100)
        flux = np.ones(100)
        flux[50] = np.nan
        
        wave_binned, flux_binned = bin_spectrum_scipy(
            wavelength, flux,
            wave_min=400, wave_max=700, wave_step=50
        )
        
        # Should handle NaN gracefully (skip or interpolate)
        assert not np.all(np.isnan(flux_binned))
