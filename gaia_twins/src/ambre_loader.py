"""Load and manage AMBRE stellar atmosphere models."""

import os
import zipfile
import numpy as np
import pandas as pd
from pathlib import Path
from tqdm import tqdm
from typing import Optional, Tuple, Dict
from scipy.interpolate import interp1d


class AmbreLoader:
    """Load AMBRE stellar spectra from ZIP archives."""
    
    def __init__(self, ambre_dir: str = "AMBRE"):
        """
        Initialize AMBRE loader.
        
        Parameters
        ----------
        ambre_dir : str
            Directory containing AMBRE ZIP files
        """
        self.ambre_dir = Path(ambre_dir)
        self.catalog = None
        
        if not self.ambre_dir.exists():
            raise FileNotFoundError(f"AMBRE directory not found: {ambre_dir}")
    
    def create_catalog(self) -> pd.DataFrame:
        """
        Create catalog of AMBRE files by parsing filenames.
        
        Returns
        -------
        pd.DataFrame
            Catalog with columns: filename, teff, logg, mh
        """
        print(f"Creating AMBRE catalog from {self.ambre_dir}...")
        
        # Find all ZIP files
        filenames = sorted([f.name for f in self.ambre_dir.glob("*.zip")])
        
        if not filenames:
            raise FileNotFoundError(f"No ZIP files found in {self.ambre_dir}")
        
        print(f"Found {len(filenames)} AMBRE files")
        
        # Parse filenames to extract stellar parameters
        catalog_data = []
        
        for f in tqdm(filenames, desc="Parsing filenames"):
            try:
                # Example filename: ambre_p6000g40z00t02.zip
                # Format: p{teff}g{logg}z{mh}t{alpha}
                key = f.split("_")[1].split(".")[0]
                
                # Extract Teff (e.g., p6000 -> 6000)
                teff = float(key.split("g")[0][1:])
                
                # Extract log g (e.g., g40 -> 4.0)
                logg = float(key.split("g")[1].split("z")[0]) / 10.0
                
                # Extract [M/H] (e.g., z00 -> 0.0, zm20 -> -2.0)
                mh_str = key.split("z")[1].split("t")[0]
                if mh_str.startswith("m"):
                    mh = -float(mh_str[1:]) / 10.0
                elif mh_str.startswith("p"):
                    mh = float(mh_str[1:]) / 10.0
                else:
                    mh = float(mh_str) / 10.0
                
                catalog_data.append({
                    'filename': f,
                    'teff': teff,
                    'logg': logg,
                    'mh': mh
                })
                
            except (IndexError, ValueError) as e:
                print(f"Warning: Could not parse {f}: {e}")
                continue
        
        self.catalog = pd.DataFrame(catalog_data)
        
        print(f"\nCatalog created with {len(self.catalog)} spectra")
        print(f"Teff range: {self.catalog['teff'].min():.0f} - {self.catalog['teff'].max():.0f} K")
        print(f"log g range: {self.catalog['logg'].min():.1f} - {self.catalog['logg'].max():.1f}")
        print(f"[M/H] range: {self.catalog['mh'].min():.1f} - {self.catalog['mh'].max():.1f}")
        
        return self.catalog
    
    def read_spectrum(
        self, 
        filename: str,
        convert_units: bool = True
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Read a spectrum from AMBRE ZIP file.
        
        Parameters
        ----------
        filename : str
            Name of ZIP file
        convert_units : bool
            If True, convert from erg/s/cm²/Å to W/nm/m²
            
        Returns
        -------
        wavelength : np.ndarray or None
            Wavelength array in Angstroms
        flux : np.ndarray or None
            Flux array (units depend on convert_units)
        """
        zip_path = self.ambre_dir / filename
        
        if not zip_path.exists():
            print(f"File not found: {zip_path}")
            return None, None
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_file:
                # Look for .spec files
                spec_files = [f for f in zip_file.namelist() if f.endswith('.spec')]
                
                if not spec_files:
                    print(f"No .spec file found in {filename}")
                    return None, None
                
                # Read the spectrum file
                with zip_file.open(spec_files[0]) as spec_file:
                    # AMBRE format: wavelength, flux, normalized_flux
                    data = np.loadtxt(spec_file)
                    
                    if data.shape[1] >= 2:
                        wavelength = data[:, 0]
                        flux = data[:, 1]
                        
                        if convert_units:
                            # Convert erg/s/cm²/Å to W/nm/m²
                            # 1 erg/s/cm²/Å = 1e-7 W·s/s / 1e-4 m² / 0.1 nm = 1e-2 W/nm/m²
                            flux = flux * 1e-2
                        
                        return wavelength, flux
                    else:
                        print(f"Unexpected format in {filename}")
                        return None, None
                        
        except Exception as e:
            print(f"Error reading {filename}: {e}")
            return None, None
    
    def load_binned_spectra(
        self,
        wavelength_grid: np.ndarray,
        show_progress: bool = True
    ) -> pd.DataFrame:
        """
        Load all AMBRE spectra and bin them to a common wavelength grid.
        
        Parameters
        ----------
        wavelength_grid : np.ndarray
            Common wavelength grid in Angstroms
        show_progress : bool
            Show progress bar
            
        Returns
        -------
        pd.DataFrame
            DataFrame with columns: filename, teff, logg, mh, flux_binned, wave_binned
        """
        if self.catalog is None:
            self.create_catalog()
        
        print(f"Loading and binning {len(self.catalog)} AMBRE spectra...")
        print(f"Wavelength grid: {wavelength_grid.min():.0f} - {wavelength_grid.max():.0f} Å")
        print(f"Number of points: {len(wavelength_grid)}")
        
        binned_data = []
        
        iterator = tqdm(self.catalog.iterrows(), total=len(self.catalog), 
                       desc="Loading spectra") if show_progress else self.catalog.iterrows()
        
        for idx, row in iterator:
            filename = row['filename']
            teff = row['teff']
            logg = row['logg']
            mh = row['mh']
            
            # Read spectrum
            wave, flux = self.read_spectrum(filename, convert_units=True)
            
            if wave is not None and flux is not None:
                # Interpolate to common grid
                f_interp = interp1d(wave, flux, kind='linear', 
                                   bounds_error=False, fill_value=np.nan)
                flux_binned = f_interp(wavelength_grid)
                
                binned_data.append({
                    'filename': filename,
                    'teff': teff,
                    'logg': logg,
                    'mh': mh,
                    'flux_binned': flux_binned,
                    'wave_binned': wavelength_grid.copy()
                })
        
        df = pd.DataFrame(binned_data)
        
        print(f"\nSuccessfully loaded {len(df)} spectra")
        
        return df
    
    def find_closest(
        self,
        teff: float,
        logg: float,
        mh: float,
        return_distance: bool = True
    ) -> Tuple[int, float]:
        """
        Find the closest AMBRE spectrum to given parameters.
        
        Parameters
        ----------
        teff : float
            Effective temperature (K)
        logg : float
            Surface gravity (cgs)
        mh : float
            Metallicity [M/H] (dex)
        return_distance : bool
            If True, also return normalized distance
            
        Returns
        -------
        closest_idx : int
            Index of closest spectrum in catalog
        distance : float
            Normalized Euclidean distance (if return_distance=True)
        """
        if self.catalog is None:
            raise ValueError("Catalog not created. Call create_catalog() first.")
        
        # Normalize parameters
        teff_norm = (self.catalog['teff'] - self.catalog['teff'].mean()) / self.catalog['teff'].std()
        logg_norm = (self.catalog['logg'] - self.catalog['logg'].mean()) / self.catalog['logg'].std()
        mh_norm = (self.catalog['mh'] - self.catalog['mh'].mean()) / self.catalog['mh'].std()
        
        teff_target_norm = (teff - self.catalog['teff'].mean()) / self.catalog['teff'].std()
        logg_target_norm = (logg - self.catalog['logg'].mean()) / self.catalog['logg'].std()
        mh_target_norm = (mh - self.catalog['mh'].mean()) / self.catalog['mh'].std()
        
        # Calculate Euclidean distance
        distances = np.sqrt(
            (teff_norm - teff_target_norm)**2 +
            (logg_norm - logg_target_norm)**2 +
            (mh_norm - mh_target_norm)**2
        )
        
        closest_idx = np.argmin(distances)
        
        if return_distance:
            return closest_idx, distances.iloc[closest_idx]
        else:
            return closest_idx
    
    def save_cache(self, cache_file: str, binned_df: pd.DataFrame):
        """
        Save binned spectra to cache file.
        
        Parameters
        ----------
        cache_file : str
            Path to cache file (.parquet or .pkl)
        binned_df : pd.DataFrame
            DataFrame with binned spectra
        """
        cache_path = Path(cache_file)
        
        if cache_path.suffix == '.parquet':
            # Parquet doesn't support arrays, use pickle
            print("Warning: Parquet doesn't support array columns, using pickle instead")
            cache_path = cache_path.with_suffix('.pkl')
        
        print(f"Saving cache to {cache_path}...")
        binned_df.to_pickle(cache_path)
        print("Cache saved successfully")
    
    def load_cache(self, cache_file: str) -> pd.DataFrame:
        """
        Load binned spectra from cache file.
        
        Parameters
        ----------
        cache_file : str
            Path to cache file (.pkl)
            
        Returns
        -------
        pd.DataFrame
            Cached binned spectra
        """
        cache_path = Path(cache_file)
        
        if not cache_path.exists():
            raise FileNotFoundError(f"Cache file not found: {cache_path}")
        
        print(f"Loading cache from {cache_path}...")
        df = pd.read_pickle(cache_path)
        
        # Update catalog from cache
        self.catalog = df[['filename', 'teff', 'logg', 'mh']].copy()
        
        print(f"Loaded {len(df)} cached spectra")
        
        return df
