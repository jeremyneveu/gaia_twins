"""Query Gaia archive for stellar spectra and astrophysical parameters."""

import numpy as np
import pandas as pd
from astroquery.gaia import Gaia
from gaiaxpy import calibrate
from tqdm import tqdm
from typing import List, Tuple, Optional, Union
from pathlib import Path

from ..data.defaults import get_default_cache_dir


class GaiaQuerier:
    """Handle queries to Gaia archive for spectra and astrophysical parameters."""

    #: Cache filename (inside ``cache_dir``) for per-user astrophysical params.
    PARAMS_CACHE_FILE = "gaia_params_cache.parquet"

    def __init__(
        self,
        batch_size: int = 1000,
        cache_dir: Optional[Union[str, Path, bool]] = None,
    ):
        """
        Initialize Gaia querier.

        Parameters
        ----------
        batch_size : int
            Number of sources to query per batch (default: 1000)
        cache_dir : str, Path or bool, optional
            If provided (a path), astrophysical parameters fetched from Gaia
            are persisted to ``cache_dir/gaia_params_cache.parquet`` and served
            from there on subsequent calls for already-seen source IDs (no
            network query). When ``None`` (default) a user-level cache is used
            (see :func:`get_default_cache_dir`), so newly queried source IDs
            are automatically cached. Pass ``False`` to disable caching and
            query the archive every time.
        """
        self.batch_size = batch_size
        if cache_dir is False:
            self.cache_dir: Optional[Path] = None
        elif cache_dir is None:
            self.cache_dir = get_default_cache_dir()
        else:
            self.cache_dir = Path(cache_dir)
        self._params_cache: Optional[pd.DataFrame] = None
        self._params_cache_path: Optional[Path] = None
        if self.cache_dir is not None:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self._params_cache_path = self.cache_dir / self.PARAMS_CACHE_FILE

    # ------------------------------------------------------------------
    # Per-user astrophysical params cache
    # ------------------------------------------------------------------
    def _load_params_cache(self) -> pd.DataFrame:
        """Lazily load (or initialise) the persisted params cache.

        The cache is a DataFrame indexed by ``source_id`` with one row per
        source per provenance family (``gspphot`` / ``gspspec``), i.e. columns
        ``source_id, teff, logg, mh, source``.

        Returns
        -------
        pd.DataFrame
            The (possibly empty) cached parameters.
        """
        if self._params_cache is not None:
            return self._params_cache
        if self._params_cache_path is not None and self._params_cache_path.exists():
            try:
                self._params_cache = pd.read_parquet(self._params_cache_path)
            except Exception:
                # Corrupted / unreadable cache: start from scratch.
                self._params_cache = pd.DataFrame(
                    columns=["source_id", "teff", "logg", "mh", "source"]
                )
        else:
            self._params_cache = pd.DataFrame(
                columns=["source_id", "teff", "logg", "mh", "source"]
            )
        return self._params_cache

    def _save_params_cache(self) -> None:
        """Persist the in-memory params cache to disk (parquet)."""
        if self._params_cache_path is not None and self._params_cache is not None:
            self._params_cache.to_parquet(self._params_cache_path)
    
    def fetch_astrophysical_params(
        self,
        source_ids: List[int],
        use_gspspec: bool = True
    ) -> pd.DataFrame:
        """
        Fetch astrophysical parameters from Gaia DR3.

        When a ``cache_dir`` was provided at construction, already-fetched
        parameters are served from the local parquet cache (no network query)
        and any newly fetched source IDs are appended to it for later calls.
        Without a ``cache_dir`` the behaviour is unchanged (query every time).

        Parameters
        ----------
        source_ids : List[int]
            List of Gaia source IDs
        use_gspspec : bool
            If True, use GSP-Spec parameters, otherwise use GSP-Phot

        Returns
        -------
        pd.DataFrame
            DataFrame indexed by ``source_id`` with columns: teff, logg, mh
        """
        print(f"Fetching astrophysical parameters for {len(source_ids)} sources...")

        source_ids = [int(sid) for sid in source_ids]

        use_cache = self.cache_dir is not None
        cache = None
        need = "gspspec" if use_gspspec else "gspphot"

        served = pd.DataFrame(columns=["source_id", "teff", "logg", "mh", "source"])
        if use_cache:
            cache = self._load_params_cache()
            if len(cache):
                served = cache[cache["source"].astype(str) == need]
                served = served[served["source_id"].isin(source_ids)].copy()

        served_ids = set(served["source_id"]) if len(served) else set()
        missing_ids = [sid for sid in source_ids if sid not in served_ids]

        print(
            f"  -> {len(served)} served from cache, "
            f"{len(missing_ids)} to query from Gaia"
        )

        # ------------------------------------------------------------------
        # Query the archive for the missing IDs (existing batch logic)
        # ------------------------------------------------------------------
        all_params = []
        total_batches = (len(missing_ids) - 1) // self.batch_size + 1 if missing_ids else 0

        for i in range(0, len(missing_ids), self.batch_size):
            batch_ids = missing_ids[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1

            # Convert to SQL format
            gaia_ids_str = np.array2string(
                np.array(batch_ids),
                separator=',',
                max_line_width=np.inf
            )[1:-1].replace("\n ", "")

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

        # Newly fetched batches into a standard, cache-friendly form
        network_rows = pd.DataFrame(columns=["source_id", "teff", "logg", "mh", "source"])
        if all_params:
            net_df = pd.concat(all_params, ignore_index=False)
            if use_gspspec:
                net_df = net_df.rename(columns={
                    'teff_gspspec': 'teff',
                    'logg_gspspec': 'logg',
                    'mh_gspspec': 'mh'
                })
            else:
                net_df = net_df.rename(columns={
                    'teff_gspphot': 'teff',
                    'logg_gspphot': 'logg',
                    'mh_gspphot': 'mh'
                })
            net_df["source"] = need
            net_df = net_df[["source_id", "teff", "logg", "mh", "source"]]
            network_rows = net_df

        # ------------------------------------------------------------------
        # Persist new results in the cache (if configured)
        # ------------------------------------------------------------------
        if use_cache and len(network_rows):
            if len(cache):
                cache = pd.concat([cache, network_rows], ignore_index=True)
                cache = cache.drop_duplicates(subset=["source_id", "source"], keep="last")
                cache = cache.reset_index(drop=True)
            else:
                cache = network_rows.reset_index(drop=True)
            self._params_cache = cache
            self._save_params_cache()

        # ------------------------------------------------------------------
        # Assemble the final result (cache + network), indexed by source_id
        # ------------------------------------------------------------------
        parts = []
        if len(served):
            parts.append(served[["source_id", "teff", "logg", "mh"]])
        if len(network_rows):
            parts.append(network_rows[["source_id", "teff", "logg", "mh"]])

        if parts:
            combined = pd.concat(parts, ignore_index=True)
            combined = combined.drop_duplicates(subset=["source_id"], keep="last")
            combined = combined.set_index("source_id")
            print(f"\nTotal: {len(combined)} sources with astrophysical parameters")
            return combined
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
