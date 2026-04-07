"""Query Gaia archive for stellar spectra and astrophysical parameters."""

import numpy as np
import pandas as pd
from astroquery.gaia import Gaia
from gaiaxpy import calibrate
from tqdm import tqdm
from typing import List, Tuple, Optional


class GaiaQuerier:
    """Handle queries to Gaia archive for spectra and astrophysical parameters."""
    
    def __init__(self, batch_size: int = 1000):
        """
        Initialize Gaia querier.
        
        Parameters
        ----------
        batch_size : int
            Number of sources to query per batch (default: 1000)
        """
        self.batch_size = batch_size
    
    def fetch_astrophysical_params(
        self, 
        source_ids: List[int],
        use_gspspec: bool = True
    ) -> pd.DataFrame:
        """
        Fetch astrophysical parameters from Gaia DR3.
        
        Parameters
        ----------
        source_ids : List[int]
            List of Gaia source IDs
        use_gspspec : bool
            If True, use GSP-Spec parameters, otherwise use GSP-Phot
            
        Returns
        -------
        pd.DataFrame
            DataFrame with columns: source_id, teff, logg, mh
        """
        print(f"Fetching astrophysical parameters for {len(source_ids)} sources...")
        
        all_params = []
        total_batches = (len(source_ids) - 1) // self.batch_size + 1
        
        for i in range(0, len(source_ids), self.batch_size):
            batch_ids = source_ids[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            
            # Convert to SQL format
            gaia_ids_str = np.array2string(
                np.array(batch_ids), 
                separator=',', 
                max_line_width=np.inf
            )[1:-1].replace('\n ', '')
            
            print(f"Batch {batch_num}/{total_batches} ({len(batch_ids)} IDs)")
            
            # Query parameters
            if use_gspspec:
                table = "gaiadr3.gaia_source"
                columns = "source_id, teff_gspspec, logg_gspspec, mh_gspspec"
            else:
                table = "gaiadr3.astrophysical_parameters"
                columns = "source_id, teff_gspphot, logg_gspphot, mh_gspphot"
            
            qry = f"SELECT {columns} FROM {table} WHERE source_id IN ({gaia_ids_str})"
            
            try:
                job = Gaia.launch_job(qry)
                batch_params = job.get_results().to_pandas()
                
                if len(batch_params) > 0:
                    all_params.append(batch_params)
                    print(f"  -> {len(batch_params)} results found")
                else:
                    print(f"  -> No results found")
                    
            except Exception as e:
                print(f"  -> Error: {e}")
                continue
        
        # Combine all batches
        if all_params:
            df = pd.concat(all_params, ignore_index=False)
            
            # Rename columns to standard names
            if use_gspspec:
                df = df.rename(columns={
                    'teff_gspspec': 'teff',
                    'logg_gspspec': 'logg',
                    'mh_gspspec': 'mh'
                })
            else:
                df = df.rename(columns={
                    'teff_gspphot': 'teff',
                    'logg_gspphot': 'logg',
                    'mh_gspphot': 'mh'
                })
            
            df.set_index('source_id', inplace=True)
            print(f"\nTotal: {len(df)} sources with astrophysical parameters")
            return df
        else:
            print("\nNo astrophysical parameters retrieved")
            return pd.DataFrame()
    
    def fetch_spectra(
        self,
        source_ids: List[int],
        sampling: Optional[np.ndarray] = None
    ) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Fetch XP spectra from Gaia using GaiaXPy.
        
        Parameters
        ----------
        source_ids : List[int]
            List of Gaia source IDs
        sampling : np.ndarray, optional
            Wavelength sampling array in Angstroms
            If None, uses default GaiaXPy sampling
            
        Returns
        -------
        spectra_df : pd.DataFrame
            DataFrame with source_id as index and flux column
        wavelengths : np.ndarray
            Wavelength array in Angstroms
        """
        print(f"Fetching XP spectra for {len(source_ids)} sources...")
        
        try:
            # Calibrate spectra
            if sampling is not None:
                # Convert to nm for GaiaXPy
                sampling_nm = sampling / 10.0
                spectra, sampling_out = calibrate(
                    source_ids,
                    sampling=sampling_nm,
                    save_file=False
                )
            else:
                spectra, sampling_out = calibrate(
                    source_ids,
                    save_file=False
                )
            
            # Convert back to Angstroms
            wavelengths = sampling_out * 10.0
            
            # Create DataFrame
            spectra_df = pd.DataFrame(spectra)
            spectra_df.set_index('source_id', inplace=True)
            
            print(f"Retrieved {len(spectra_df)} spectra")
            print(f"Wavelength range: {wavelengths.min():.1f} - {wavelengths.max():.1f} Å")
            
            return spectra_df, wavelengths
            
        except Exception as e:
            print(f"Error fetching spectra: {e}")
            return pd.DataFrame(), np.array([])
    
    def fetch_all(
        self,
        source_ids: List[int],
        wavelength_sampling: Optional[np.ndarray] = None,
        use_gspspec: bool = False
    ) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Fetch both spectra and astrophysical parameters.
        
        Parameters
        ----------
        source_ids : List[int]
            List of Gaia source IDs
        wavelength_sampling : np.ndarray, optional
            Wavelength sampling for spectra
        use_gspspec : bool
            Use GSP-Spec instead of GSP-Phot for parameters
            
        Returns
        -------
        combined_df : pd.DataFrame
            DataFrame with spectra and astrophysical parameters
        wavelengths : np.ndarray
            Wavelength array
        """
        # Fetch spectra
        spectra_df, wavelengths = self.fetch_spectra(source_ids, wavelength_sampling)
        
        # Fetch parameters
        params_df = self.fetch_astrophysical_params(source_ids, use_gspspec)
        
        # Merge
        if len(spectra_df) > 0 and len(params_df) > 0:
            combined_df = spectra_df.join(params_df, how='left')
            print(f"\nCombined data: {len(combined_df)} sources")
            print(f"With astrophysical params: {combined_df['teff'].notna().sum()}")
            return combined_df, wavelengths
        elif len(spectra_df) > 0:
            return spectra_df, wavelengths
        else:
            return pd.DataFrame(), wavelengths
