"""4D interpolator for AMBRE stellar spectra."""

import numpy as np
import pandas as pd
from sklearn.neighbors import KNeighborsRegressor
from scipy.spatial import cKDTree
from tqdm import tqdm
from typing import Optional, Tuple


class AmbreInterpolator:
    """
    4D interpolator for AMBRE spectra.
    
    Interpolates flux as a function of (Teff, log g, [M/H], wavelength).
    Uses K-Nearest Neighbors for fast interpolation on irregular grid.
    """
    
    def __init__(
        self,
        ambre_data: pd.DataFrame,
        method: str = 'knn',
        n_neighbors: int = 4
    ):
        """
        Initialize AMBRE interpolator.
        
        Parameters
        ----------
        ambre_data : pd.DataFrame
            DataFrame with columns: teff, logg, mh, flux_binned, wave_binned
        method : str
            Interpolation method: 'knn' (K-Nearest Neighbors) or 'kdtree'
        n_neighbors : int
            Number of neighbors for interpolation
        """
        self.ambre_data = ambre_data
        self.method = method
        self.n_neighbors = n_neighbors
        self.model = None
        self.points = None
        self.values = None
        self.wavelength_grid = None
        
        # Get wavelength grid (should be same for all spectra)
        if len(ambre_data) > 0:
            self.wavelength_grid = ambre_data.iloc[0]['wave_binned']
        
        self._build_interpolator()
    
    def _build_interpolator(self):
        """Build the 4D interpolation model."""
        print(f"Building 4D interpolator ({self.method})...")
        
        # Extract all (teff, logg, mh, wavelength) points and corresponding flux
        all_points = []
        all_flux = []
        
        for idx, row in tqdm(self.ambre_data.iterrows(), 
                            total=len(self.ambre_data),
                            desc="Preparing interpolation data"):
            teff = row['teff']
            logg = row['logg']
            mh = row['mh']
            wave_binned = row['wave_binned']
            flux_binned = row['flux_binned']
            
            # Create 4D points for this spectrum
            for wave, flux in zip(wave_binned, flux_binned):
                if not np.isnan(flux):  # Skip NaN values
                    all_points.append([teff, logg, mh, wave])
                    all_flux.append(flux)
        
        self.points = np.array(all_points)
        self.values = np.array(all_flux)
        
        print(f"Total interpolation points: {len(self.points):,}")
        print(f"Parameter ranges:")
        print(f"  Teff: {self.points[:,0].min():.0f} - {self.points[:,0].max():.0f} K")
        print(f"  log g: {self.points[:,1].min():.1f} - {self.points[:,1].max():.1f}")
        print(f"  [M/H]: {self.points[:,2].min():.1f} - {self.points[:,2].max():.1f}")
        print(f"  Wavelength: {self.points[:,3].min():.0f} - {self.points[:,3].max():.0f} Å")
        
        # Build model based on method
        if self.method == 'knn':
            self._build_knn()
        elif self.method == 'kdtree':
            self._build_kdtree()
        else:
            raise ValueError(f"Unknown method: {self.method}")
    
    def _build_knn(self):
        """Build K-Nearest Neighbors model."""
        print("Training KNN model...")
        
        self.model = KNeighborsRegressor(
            n_neighbors=self.n_neighbors,
            weights='distance',
            algorithm='ball_tree',
            leaf_size=30
        )
        
        self.model.fit(self.points, self.values)
        print("KNN model ready")
    
    def _build_kdtree(self):
        """Build KD-Tree for nearest neighbor search."""
        print("Building KD-Tree...")
        
        self.model = cKDTree(self.points)
        print("KD-Tree ready")
    
    def interpolate(
        self,
        wavelengths: np.ndarray,
        teff: float,
        logg: float,
        mh: float
    ) -> np.ndarray:
        """
        Interpolate spectrum at given parameters.
        
        Parameters
        ----------
        wavelengths : np.ndarray
            Wavelength array in Angstroms
        teff : float
            Effective temperature (K)
        logg : float
            Surface gravity (cgs)
        mh : float
            Metallicity [M/H] (dex)
            
        Returns
        -------
        np.ndarray
            Interpolated flux array
        """
        wavelengths = np.asarray(wavelengths)
        
        # Create query points
        query_points = np.column_stack([
            np.full(len(wavelengths), teff),
            np.full(len(wavelengths), logg),
            np.full(len(wavelengths), mh),
            wavelengths
        ])
        
        # Interpolate based on method
        if self.method == 'knn':
            flux_interp = self.model.predict(query_points)
        elif self.method == 'kdtree':
            flux_interp = self._kdtree_interpolate(query_points)
        else:
            raise ValueError(f"Unknown method: {self.method}")
        
        return flux_interp
    
    def _kdtree_interpolate(self, query_points: np.ndarray) -> np.ndarray:
        """
        Interpolate using KD-Tree with inverse distance weighting.
        
        Parameters
        ----------
        query_points : np.ndarray
            Query points (N, 4)
            
        Returns
        -------
        np.ndarray
            Interpolated values
        """
        # Find k nearest neighbors
        distances, indices = self.model.query(query_points, k=self.n_neighbors)
        
        # Avoid division by zero
        distances = np.maximum(distances, 1e-10)
        
        # Inverse distance weighting
        weights = 1.0 / distances
        weights_sum = np.sum(weights, axis=1, keepdims=True)
        weights_norm = weights / weights_sum
        
        # Weighted average
        flux_interp = np.sum(weights_norm * self.values[indices], axis=1)
        
        return flux_interp
    
    def __call__(
        self,
        wavelengths: np.ndarray,
        teff: float,
        logg: float,
        mh: float
    ) -> np.ndarray:
        """
        Make interpolator callable.
        
        Same as interpolate() method.
        """
        return self.interpolate(wavelengths, teff, logg, mh)
    
    def check_bounds(
        self,
        teff: float,
        logg: float,
        mh: float
    ) -> Tuple[bool, str]:
        """
        Check if parameters are within interpolation bounds.
        
        Parameters
        ----------
        teff : float
            Effective temperature (K)
        logg : float
            Surface gravity (cgs)
        mh : float
            Metallicity [M/H] (dex)
            
        Returns
        -------
        is_valid : bool
            True if parameters are within bounds
        message : str
            Warning message if out of bounds
        """
        teff_min, teff_max = self.points[:,0].min(), self.points[:,0].max()
        logg_min, logg_max = self.points[:,1].min(), self.points[:,1].max()
        mh_min, mh_max = self.points[:,2].min(), self.points[:,2].max()
        
        issues = []
        
        if teff < teff_min or teff > teff_max:
            issues.append(f"Teff={teff:.0f}K out of range [{teff_min:.0f}, {teff_max:.0f}]")
        
        if logg < logg_min or logg > logg_max:
            issues.append(f"log g={logg:.1f} out of range [{logg_min:.1f}, {logg_max:.1f}]")
        
        if mh < mh_min or mh > mh_max:
            issues.append(f"[M/H]={mh:.1f} out of range [{mh_min:.1f}, {mh_max:.1f}]")
        
        if issues:
            return False, "; ".join(issues)
        else:
            return True, "Parameters within bounds"
    
    def get_grid_info(self) -> dict:
        """
        Get information about the interpolation grid.
        
        Returns
        -------
        dict
            Dictionary with grid statistics
        """
        return {
            'n_points': len(self.points),
            'n_spectra': len(self.ambre_data),
            'teff_range': (self.points[:,0].min(), self.points[:,0].max()),
            'logg_range': (self.points[:,1].min(), self.points[:,1].max()),
            'mh_range': (self.points[:,2].min(), self.points[:,2].max()),
            'wavelength_range': (self.points[:,3].min(), self.points[:,3].max()),
            'method': self.method,
            'n_neighbors': self.n_neighbors
        }
