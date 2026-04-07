"""Main synthetic spectrum generator combining Gaia data and AMBRE models."""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Optional, Union
from tqdm import tqdm

from .gaia_query import GaiaQuerier
from .ambre_loader import AmbreLoader
from .interpolator import AmbreInterpolator
from ..utils.normalization import normalize_spectrum


class SyntheticSpectrumGenerator:
    """
    Generate synthetic spectra from Gaia source IDs using AMBRE models.
    
    This is the main user-facing class that combines all functionality.
    """
    
    def __init__(
        self,
        ambre_dir: str = "AMBRE",
        cache_dir: Optional[str] = None,
        interpolation_method: str = 'knn',
        n_neighbors: int = 4
    ):
        """
        Initialize synthetic spectrum generator.
        
        Parameters
        ----------
        ambre_dir : str
            Directory containing AMBRE ZIP files
        cache_dir : str, optional
            Directory for caching processed data
        interpolation_method : str
            Interpolation method: 'knn' or 'kdtree'
        n_neighbors : int
            Number of neighbors for interpolation
        """
        self.ambre_dir = Path(ambre_dir)
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.interpolation_method = interpolation_method
        self.n_neighbors = n_neighbors
        
        # Components
        self.gaia_querier = GaiaQuerier()
        self.ambre_loader = AmbreLoader(str(self.ambre_dir))
        self.interpolator = None
        
        # Data
        self.ambre_binned = None
        self.wavelength_grid = None
        
        # Create cache directory if needed
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def prepare_ambre(
        self,
        wavelength_min: float = 3000.0,
        wavelength_max: float = 11000.0,
        wavelength_step: float = 10.0,
        use_cache: bool = True
    ):
        """
        Prepare AMBRE spectra for interpolation.
        
        Parameters
        ----------
        wavelength_min : float
            Minimum wavelength in Angstroms
        wavelength_max : float
            Maximum wavelength in Angstroms
        wavelength_step : float
            Wavelength step in Angstroms
        use_cache : bool
            Use cached data if available
        """
        # Define wavelength grid
        self.wavelength_grid = np.arange(
            wavelength_min,
            wavelength_max + wavelength_step,
            wavelength_step
        )
        
        print(f"Wavelength grid: {wavelength_min:.0f} - {wavelength_max:.0f} Å")
        print(f"Step: {wavelength_step:.1f} Å ({len(self.wavelength_grid)} points)")
        
        # Check for cache
        cache_file = None
        if use_cache and self.cache_dir:
            cache_file = self.cache_dir / f"ambre_binned_{wavelength_step:.1f}A.pkl"
            
            if cache_file.exists():
                print(f"Loading cached AMBRE data from {cache_file}")
                self.ambre_binned = self.ambre_loader.load_cache(str(cache_file))
                self._build_interpolator()
                return
        
        # Load and bin spectra
        self.ambre_binned = self.ambre_loader.load_binned_spectra(
            self.wavelength_grid,
            show_progress=True
        )
        
        # Save to cache
        if cache_file:
            self.ambre_loader.save_cache(str(cache_file), self.ambre_binned)
        
        # Build interpolator
        self._build_interpolator()
    
    def _build_interpolator(self):
        """Build the 4D interpolator."""
        if self.ambre_binned is None or len(self.ambre_binned) == 0:
            raise ValueError("No AMBRE data loaded. Call prepare_ambre() first.")
        
        self.interpolator = AmbreInterpolator(
            self.ambre_binned,
            method=self.interpolation_method,
            n_neighbors=self.n_neighbors
        )
    
    def generate_spectra(
        self,
        source_ids: Union[List[int], int],
        wavelength_sampling: Optional[np.ndarray] = None,
        normalize: bool = True,
        use_gspspec: bool = False
    ) -> pd.DataFrame:
        """
        Generate synthetic spectra for given Gaia source IDs.
        
        Parameters
        ----------
        source_ids : List[int] or int
            Gaia source ID(s)
        wavelength_sampling : np.ndarray, optional
            Output wavelength sampling. If None, uses AMBRE grid.
        normalize : bool
            Normalize synthetic spectra to match Gaia flux
        use_gspspec : bool
            Use GSP-Spec parameters instead of GSP-Phot
            
        Returns
        -------
        pd.DataFrame
            DataFrame with columns:
            - source_id (index)
            - teff, logg, mh (input parameters)
            - synth_flux (synthetic spectrum)
            - synth_wave (wavelength array)
            - gaia_flux (optional, if Gaia spectra available)
            - gaia_wave (optional)
        """
        # Convert single ID to list
        if isinstance(source_ids, int):
            source_ids = [source_ids]
        
        # Check interpolator is ready
        if self.interpolator is None:
            raise ValueError("Interpolator not ready. Call prepare_ambre() first.")
        
        # Output wavelength grid
        if wavelength_sampling is None:
            output_wave = self.wavelength_grid
        else:
            output_wave = wavelength_sampling
        
        print(f"\nGenerating synthetic spectra for {len(source_ids)} sources...")
        
        # Fetch Gaia data
        gaia_data, gaia_wave = self.gaia_querier.fetch_all(
            source_ids,
            wavelength_sampling=None,  # Use default Gaia sampling
            use_gspspec=use_gspspec
        )
        
        if len(gaia_data) == 0:
            print("No Gaia data retrieved")
            return pd.DataFrame()
        
        # Generate synthetic spectra
        results = []
        
        for source_id, row in tqdm(gaia_data.iterrows(), 
                                   total=len(gaia_data),
                                   desc="Generating spectra"):
            
            # Check if astrophysical parameters are available
            if pd.isna(row['teff']) or pd.isna(row['logg']) or pd.isna(row['mh']):
                continue
            
            teff = row['teff']
            logg = row['logg']
            mh = row['mh']
            
            # Check bounds
            is_valid, message = self.interpolator.check_bounds(teff, logg, mh)
            if not is_valid:
                print(f"Warning: source_id {source_id}: {message}")
                # Continue anyway with extrapolation
            
            # Generate synthetic spectrum
            synth_flux = self.interpolator.interpolate(
                output_wave, teff, logg, mh
            )
            
            # Normalize if requested
            if normalize and 'flux' in row and not pd.isna(row['flux']).all():
                gaia_flux = row['flux']
                synth_flux_norm = normalize_spectrum(
                    output_wave, synth_flux,
                    gaia_wave, gaia_flux
                )
            else:
                synth_flux_norm = synth_flux
            
            # Store results
            result = {
                'source_id': source_id,
                'teff': teff,
                'logg': logg,
                'mh': mh,
                'synth_flux': synth_flux_norm,
                'synth_wave': output_wave.copy()
            }
            
            # Add Gaia spectrum if available
            if 'flux' in row:
                result['gaia_flux'] = row['flux']
                result['gaia_wave'] = gaia_wave.copy()
            
            results.append(result)
        
        # Create DataFrame
        df = pd.DataFrame(results)
        df.set_index('source_id', inplace=True)
        
        print(f"\nGenerated {len(df)} synthetic spectra")
        
        return df
    
    def save_spectra(
        self,
        spectra_df: pd.DataFrame,
        output_file: str
    ):
        """
        Save synthetic spectra to file.
        
        Parameters
        ----------
        spectra_df : pd.DataFrame
            DataFrame with synthetic spectra
        output_file : str
            Output file path (.pkl or .h5)
        """
        output_path = Path(output_file)
        
        print(f"Saving spectra to {output_path}...")
        
        if output_path.suffix == '.pkl':
            spectra_df.to_pickle(output_path)
        elif output_path.suffix == '.h5':
            spectra_df.to_hdf(output_path, key='spectra', mode='w')
        else:
            raise ValueError(f"Unsupported format: {output_path.suffix}")
        
        print("Spectra saved successfully")
    
    def load_spectra(self, input_file: str) -> pd.DataFrame:
        """
        Load synthetic spectra from file.
        
        Parameters
        ----------
        input_file : str
            Input file path
            
        Returns
        -------
        pd.DataFrame
            Loaded spectra
        """
        input_path = Path(input_file)
        
        print(f"Loading spectra from {input_path}...")
        
        if input_path.suffix == '.pkl':
            df = pd.read_pickle(input_path)
        elif input_path.suffix == '.h5':
            df = pd.read_hdf(input_path, key='spectra')
        else:
            raise ValueError(f"Unsupported format: {input_path.suffix}")
        
        print(f"Loaded {len(df)} spectra")
        
        return df
    
    def get_info(self) -> dict:
        """
        Get information about the generator configuration.
        
        Returns
        -------
        dict
            Configuration and status information
        """
        info = {
            'ambre_dir': str(self.ambre_dir),
            'cache_dir': str(self.cache_dir) if self.cache_dir else None,
            'interpolation_method': self.interpolation_method,
            'n_neighbors': self.n_neighbors,
            'ambre_loaded': self.ambre_binned is not None,
            'interpolator_ready': self.interpolator is not None
        }
        
        if self.wavelength_grid is not None:
            info['wavelength_grid'] = {
                'min': float(self.wavelength_grid.min()),
                'max': float(self.wavelength_grid.max()),
                'step': float(np.diff(self.wavelength_grid).mean()),
                'n_points': len(self.wavelength_grid)
            }
        
        if self.interpolator is not None:
            info['interpolator_info'] = self.interpolator.get_grid_info()
        
        return info
