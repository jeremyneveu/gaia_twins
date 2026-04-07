# Gaia Synthetic Spectra Generator

Generate synthetic stellar spectra from Gaia source IDs using AMBRE stellar atmosphere models.

## Features

- Query Gaia DR3 archive for stellar astrophysical parameters and XP spectra
- Load and interpolate AMBRE stellar atmosphere model spectra
- 4D interpolation in (Teff, log g, [M/H], wavelength) space
- Generate synthetic spectra binned to user-defined wavelength sampling
- Command-line interface and Python API
- Efficient processing with caching and batch queries

## Installation

### From source

```bash
git clone https://github.com/yourusername/gaia-synth-spectra.git
cd gaia-synth-spectra
pip install -e .
```

### With development dependencies

```bash
pip install -e ".[dev]"
```

## Dependencies

- Python >= 3.8
- numpy >= 1.20.0
- pandas >= 1.3.0
- scipy >= 1.7.0
- astropy >= 5.0
- astroquery >= 0.4.6
- gaiaxpy >= 2.0.0
- scikit-learn >= 1.0.0

All dependencies are automatically installed via `pip install`.

## Quick Start

### Python API

```python
from gaia_synth_spectra import SyntheticSpectrumGenerator

# Initialize generator
generator = SyntheticSpectrumGenerator(
    ambre_dir='path/to/AMBRE',
    wavelength_min=330.0,  # nm
    wavelength_max=1050.0,  # nm
    wavelength_step=0.5,   # nm
    interpolation_method='knn',
    n_neighbors=4
)

# Prepare AMBRE data (loads and caches spectra)
generator.prepare_ambre(cache_file='ambre_cache.pkl')

# Generate synthetic spectra
source_ids = [5853498713190525696, 5762406957886626432]
results = generator.generate_spectra(source_ids)

# Results DataFrame contains:
# - source_id: Gaia DR3 source ID
# - teff_gspphot, logg_gspphot, mh_gspphot: Astrophysical parameters
# - synth_wave: Wavelength array (nm)
# - synth_flux: Synthetic flux array (W/nm/m²)
# - gaia_wave: Gaia XP wavelength array
# - gaia_flux: Gaia XP flux array
```

### Command-line Interface

Generate spectra from a list of source IDs:

```bash
# From file with source IDs
gaia-synth -i source_ids.txt -o results.pkl -a /path/to/AMBRE

# From command-line arguments
gaia-synth -s 5853498713190525696 5762406957886626432 \
    -o results.pkl -a /path/to/AMBRE

# With custom wavelength range
gaia-synth -i source_ids.csv -o results.pkl -a /path/to/AMBRE \
    --wave-min 400 --wave-max 900 --wave-step 1.0

# With caching
gaia-synth -i source_ids.txt -o results.pkl -a /path/to/AMBRE \
    --ambre-cache ambre_cache.pkl

# Verbose output
gaia-synth -i source_ids.txt -o results.pkl -a /path/to/AMBRE -v
```

#### CLI Options

```
Required arguments:
  -i, --input FILE         Input file with source IDs (CSV, Parquet, or text)
  -s, --source-ids ID...   Gaia source IDs (space-separated)
  -o, --output FILE        Output file path
  -a, --ambre-dir DIR      Directory containing AMBRE ZIP files

Optional arguments:
  -f, --format FORMAT      Output format: pickle, parquet, hdf5, csv (default: pickle)
  --ambre-cache FILE       Path to AMBRE cache file (pickle)
  --wave-min FLOAT         Minimum wavelength in nm (default: 330.0)
  --wave-max FLOAT         Maximum wavelength in nm (default: 1050.0)
  --wave-step FLOAT        Wavelength step in nm (default: 0.5)
  --interp-method METHOD   Interpolation method: knn, kdtree (default: knn)
  --n-neighbors INT        Number of neighbors for KNN (default: 4)
  --batch-size INT         Batch size for Gaia queries (default: 1000)
  -v, --verbose            Verbose output
```

## AMBRE Data

The package requires AMBRE stellar atmosphere model spectra. These should be organized as:

```
AMBRE/
  ambre_p3500g+0.0z-0.00t0.00.zip
  ambre_p3500g+0.0z-0.50t0.00.zip
  ...
```

Each ZIP file contains a `.spec` file with columns:
- wavelength (Å)
- flux (erg/s/cm²/Å)
- normalized_flux

File naming convention: `ambre_p{Teff}g{logg}z{mh}t{alpha}.zip`
- Teff: Effective temperature (K)
- logg: Surface gravity (log₁₀ cm/s²)
- mh: Metallicity [M/H]
- alpha: Alpha enhancement [α/Fe]

## Python API Details

### SyntheticSpectrumGenerator

Main class for generating synthetic spectra.

```python
class SyntheticSpectrumGenerator:
    def __init__(
        self,
        ambre_dir: str,
        wavelength_min: float = 330.0,
        wavelength_max: float = 1050.0,
        wavelength_step: float = 0.5,
        interpolation_method: str = 'knn',
        n_neighbors: int = 4,
        batch_size: int = 1000
    )
    
    def prepare_ambre(self, cache_file: Optional[str] = None)
        """Load and cache AMBRE spectra."""
    
    def generate_spectra(
        self,
        source_ids: List[int],
        normalize: bool = True
    ) -> pd.DataFrame
        """Generate synthetic spectra for given source IDs."""
    
    def get_info(self) -> dict
        """Get generator configuration information."""
```

### GaiaQuerier

Query Gaia archive for astrophysical parameters and spectra.

```python
from gaia_synth_spectra.core import GaiaQuerier

querier = GaiaQuerier(batch_size=1000)
params = querier.fetch_astrophysical_params(source_ids)
spectra = querier.fetch_spectra(source_ids)
all_data = querier.fetch_all(source_ids)
```

### AmbreLoader

Load AMBRE stellar atmosphere models.

```python
from gaia_synth_spectra.core import AmbreLoader

loader = AmbreLoader(ambre_dir='path/to/AMBRE')
catalog = loader.create_catalog()
spectrum = loader.read_spectrum('ambre_p5000g+4.0z+0.00t0.00.zip')
binned = loader.load_binned_spectra(wave_grid, cache_file='cache.pkl')
```

### AmbreInterpolator

4D interpolation of AMBRE spectra.

```python
from gaia_synth_spectra.core import AmbreInterpolator

interpolator = AmbreInterpolator(
    ambre_data=binned_spectra,
    method='knn',
    n_neighbors=4
)
synth_flux = interpolator.interpolate(teff=5000, logg=4.0, mh=0.0)
```

## Utilities

### Binning

```python
from gaia_synth_spectra.utils.binning import bin_spectrum, rebin_spectrum

# Bin spectrum to regular grid
wave_binned, flux_binned = bin_spectrum(
    wavelength, flux, wave_min=400, wave_max=900, wave_step=1.0
)

# Rebin to new grid
flux_rebinned = rebin_spectrum(
    wavelength, flux, new_wavelength
)
```

### Normalization

```python
from gaia_synth_spectra.utils.normalization import normalize_spectrum

# Normalize synthetic spectrum to match Gaia
synth_flux_norm = normalize_spectrum(
    synth_wave, synth_flux,
    gaia_wave, gaia_flux,
    method='integral'
)
```

## Performance Tips

1. **Use caching**: Specify `cache_file` when calling `prepare_ambre()` to avoid reloading AMBRE spectra
2. **Batch processing**: Process source IDs in batches of ~1000 to avoid Gaia query timeouts
3. **Interpolation method**: KNN is faster than KDTree for most cases
4. **Output format**: Use pickle format to save array columns (spectra)

## Examples

See the `examples/` directory for Jupyter notebooks:
- `basic_usage.ipynb`: Basic usage examples
- `advanced_features.ipynb`: Advanced features and customization
- `performance_comparison.ipynb`: Performance comparison of interpolation methods

## Citation

If you use this package in your research, please cite:

```
@software{gaia_synth_spectra,
  author = {Your Name},
  title = {Gaia Synthetic Spectra Generator},
  year = {2025},
  url = {https://github.com/yourusername/gaia-synth-spectra}
}
```

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## Acknowledgments

- Gaia mission: https://www.cosmos.esa.int/gaia
- AMBRE stellar atmosphere models: http://ambre.oca.eu/
- GaiaXPy: https://gaia-dpci.github.io/GaiaXPy-website/
