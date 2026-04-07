"""Tests for validators module."""

import pytest
import numpy as np

# Direct import - conftest.py sets up the path
from utils import validators


class TestValidateSourceIds:
    """Test source ID validation."""
    
    def test_valid_source_ids_list(self):
        """Test with valid list of integers."""
        ids = [5853498713190525696, 5762406957886626432]
        result = validators.validate_source_ids(ids)
        assert result == ids
        assert isinstance(result, list)
    
    def test_valid_source_ids_strings(self):
        """Test with valid list of strings."""
        ids = ["5853498713190525696", "5762406957886626432"]
        result = validators.validate_source_ids(ids)
        assert result == [5853498713190525696, 5762406957886626432]
    
    def test_valid_source_ids_array(self):
        """Test with numpy array."""
        ids = np.array([5853498713190525696, 5762406957886626432])
        result = validators.validate_source_ids(ids)
        assert result == [5853498713190525696, 5762406957886626432]
    
    def test_empty_list_raises(self):
        """Test that empty list raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validators.validate_source_ids([])
    
    def test_invalid_type_raises(self):
        """Test that invalid type raises ValueError."""
        with pytest.raises(ValueError):
            validators.validate_source_ids("not a list")
    
    def test_negative_id_raises(self):
        """Test that negative ID raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            validators.validate_source_ids([-123])
    
    def test_invalid_id_raises(self):
        """Test that invalid ID raises ValueError."""
        with pytest.raises(ValueError):
            validators.validate_source_ids(["not_a_number"])


class TestValidateWavelengthRange:
    """Test wavelength range validation."""
    
    def test_default_values(self):
        """Test with default values."""
        wmin, wmax, wstep = validators.validators.validate_wavelength_range()
        assert wmin == 330.0
        assert wmax == 1050.0
        assert wstep == 0.5
    
    def test_custom_values(self):
        """Test with custom values."""
        wmin, wmax, wstep = validators.validate_wavelength_range(400.0, 900.0, 1.0)
        assert wmin == 400.0
        assert wmax == 900.0
        assert wstep == 1.0
    
    def test_min_greater_than_max_raises(self):
        """Test that min > max raises ValueError."""
        with pytest.raises(ValueError, match="must be greater than"):
            validators.validate_wavelength_range(1000.0, 500.0, 1.0)
    
    def test_negative_wavelength_raises(self):
        """Test that negative wavelength raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            validators.validate_wavelength_range(-100.0, 1000.0, 1.0)
    
    def test_negative_step_raises(self):
        """Test that negative step raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            validators.validate_wavelength_range(300.0, 1000.0, -1.0)
    
    def test_step_too_large_raises(self):
        """Test that step > range raises ValueError."""
        with pytest.raises(ValueError, match="larger than wavelength range"):
            validators.validate_wavelength_range(300.0, 400.0, 200.0)


class TestValidateStellarParams:
    """Test stellar parameter validation."""
    
    def test_valid_params(self):
        """Test with valid parameters."""
        teff, logg, mh = validators.validate_stellar_params(5000.0, 4.0, 0.0)
        assert teff == 5000.0
        assert logg == 4.0
        assert mh == 0.0
    
    def test_none_values(self):
        """Test with None values."""
        teff, logg, mh = validators.validate_stellar_params()
        assert teff is None
        assert logg is None
        assert mh is None
    
    def test_negative_teff_raises(self):
        """Test that negative Teff raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            validators.validate_stellar_params(teff=-5000.0)
    
    def test_bounds_checking(self):
        """Test bounds checking."""
        # Should not raise
        teff, logg, mh = validators.validate_stellar_params(5000.0, 4.0, 0.0, check_bounds=True)
        
        # Should raise - Teff out of bounds
        with pytest.raises(ValueError, match="outside typical range"):
            validators.validate_stellar_params(teff=10000.0, check_bounds=True)


class TestValidateInterpolationMethod:
    """Test interpolation method validation."""
    
    def test_valid_methods(self):
        """Test valid methods."""
        assert validators.validate_interpolation_method('knn') == 'knn'
        assert validators.validate_interpolation_method('KNN') == 'knn'
        assert validators.validate_interpolation_method('kdtree') == 'kdtree'
        assert validators.validate_interpolation_method('nearest') == 'nearest'
    
    def test_invalid_method_raises(self):
        """Test that invalid method raises ValueError."""
        with pytest.raises(ValueError, match="Invalid interpolation method"):
            validators.validate_interpolation_method('invalid')


class TestValidateOutputFormat:
    """Test output format validation."""
    
    def test_valid_formats(self):
        """Test valid formats."""
        assert validators.validate_output_format('pickle') == 'pickle'
        assert validators.validate_output_format('PICKLE') == 'pickle'
        assert validators.validate_output_format('pkl') == 'pkl'
        assert validators.validate_output_format('parquet') == 'parquet'
        assert validators.validate_output_format('hdf5') == 'hdf5'
        assert validators.validate_output_format('h5') == 'h5'
        assert validators.validate_output_format('csv') == 'csv'
    
    def test_invalid_format_raises(self):
        """Test that invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid output format"):
            validators.validate_output_format('json')


class TestValidateBatchSize:
    """Test batch size validation."""
    
    def test_valid_batch_size(self):
        """Test valid batch size."""
        assert validators.validate_batch_size(100) == 100
        assert validators.validate_batch_size(1000) == 1000
    
    def test_string_converted(self):
        """Test that string is converted to int."""
        assert validators.validate_batch_size("500") == 500
    
    def test_negative_raises(self):
        """Test that negative batch size raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            validators.validate_batch_size(-10)
    
    def test_zero_raises(self):
        """Test that zero raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            validators.validate_batch_size(0)
    
    def test_very_large_raises(self):
        """Test that very large batch size raises ValueError."""
        with pytest.raises(ValueError, match="very large"):
            validators.validate_batch_size(20000)
