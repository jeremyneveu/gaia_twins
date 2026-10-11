# gaia-twins

Generate high-resolution synthetic **"twin"** spectra for Gaia stars by
interpolating the [AMBRE](https://pollux.oreme.org/explore/AMBRE/) grid of
stellar atmosphere models at the astrophysical parameters (Teff, log g, [M/H])
of each target source.

## Features

- Query the Gaia DR3 archive (TAP) for stellar astrophysical parameters.
- Load and 4D-interpolate the AMBRE model grid in (Teff, log g, [M/H],
  wavelength) space.
- Generate a synthetic "twin" spectrum for any Gaia source.
- Pre-binned **parquet grid** fast path (avoids re-parsing ~13k ZIP archives).
- Command-line interface (`gaia-twins`) and Python API.
- Sparse-grid robustness: nearest-neighbour cell filling plus parameter
  clamping for stars outside the grid.

## Installation

```bash
# Editable development install (with pytest, black, flake8)
pip install -e ".[dev]"

# With plotting extras
pip install -e ".[dev,plots]"
```

## Quick Start

### 1. (Optional) Build a pre-binned AMBRE parquet grid

The pipeline can work directly from the raw `*.zip` files, but a pre-binned
parquet is much faster. Build one with:

```bash
python scripts/rebuild_ambre_grid.py \
    --ambre-dir AMBRE \
    --output AMBRE/ambre_complete_binned_10.0A.parquet \
    --wave-min 3000 --wave-max 11000 --wave-step 10.0
```

### 2. Python API

```python
from gaia_twins import SyntheticSpectrumGenerator

generator = SyntheticSpectrumGenerator(
    ambre_dir="AMBRE",
    interpolation_method="linear",
)

# Load the pre-binned AMBRE grid (columns: filename, teff, logg, mh,
# flux_binned, wave_binned) and build the 4D interpolator.
generator.prepare_ambre(
    parquet_path="AMBRE/ambre_complete_binned_10.0A.parquet",
)

# Generate twin spectra for a set of Gaia source IDs (GSP-Phot by default).
results = generator.generate_twins([5853498713190525696], use_gspspec=False)

print(results[["teff", "logg", "mh", "twin_filename"]])
```

`generate_twins(...)` returns a DataFrame indexed by `source_id` with the
stellar parameters, the synthetic spectrum (`synth_wave`, `synth_flux`) and
the matched AMBRE twin file (`twin_filename`, `twin_teff`, `twin_logg`,
`twin_mh`).

If you already have parameters and only want a spectrum:

```python
wave, flux = generator.generate_spectrum(teff=5772.0, logg=4.44, mh=0.02)
```

Persistence helpers:

```python
generator.save_spectra(results, "results.parquet", format="parquet")
back = generator.load_spectra("results.parquet")
info = generator.get_info()          # configuration + grid summary
```

### 3. Command-line interface

```bash
gaia-twins -i source_ids.txt -o results.parquet -f parquet \
    --parquet AMBRE/ambre_complete_binned_10.0A.parquet -a AMBRE

# From explicit source IDs
gaia-twins -s 5853498713190525696 5762406957886626432 \
    --parquet AMBRE/ambre_complete_binned_10.0A.parquet \
    -o results.pkl -f pickle -a AMBRE
```

Key options:

```
  -i, --input FILE        Input file with source IDs (text, CSV or parquet)
  -s, --source-ids ID...  Gaia source IDs (space-separated)
  -a, --ambre-dir DIR     Directory containing AMBRE ZIP files
      --parquet FILE      Pre-binned AMBRE parquet grid (recommended)
  -o, --output FILE       Output file (default: twin_spectra.pkl)
  -f, --format FMT        pickle | parquet | csv | hdf5 (default: pickle)
      --wave-min FLOAT    Min wavelength for the ZIP path (Å, default 3000)
      --wave-max FLOAT    Max wavelength for the ZIP path (Å, default 11000)
      --wave-step FLOAT   Bin width for the ZIP path (Å, default 10)
      --interp-method M   linear | nearest (default: linear)
      --gspspec           Use GSP-Spec instead of GSP-Phot parameters
      --cache-dir DIR     Directory for AMBRE grid caching
  -v, --verbose           Verbose logging
```

> **Note:** `gaia-twins --help` lists the authoritative set of options.

## Command API summary

| Method | Purpose |
|--------|---------|
| `prepare_ambre(parquet_path=..., wavelength_min/max/step)` | Load the binned AMBRE grid and build the 4D interpolator |
| `generate_spectrum(teff, logg, mh, wavelengths=None)` | Interpolate one synthetic spectrum |
| `generate_spectra(source_ids, use_gspspec=False)` | Query Gaia + interpolate for several sources |
| `find_twin(teff, logg, mh)` | Locate the closest AMBRE model |
| `generate_twins(source_ids, use_gspspec=False)` | Spectra + closest-match twin column |
| `save_spectra / load_spectra` | Persist / read results |
| `get_info()` | Configuration + grid summary |

## Rebuilding the AMBRE grid

`scripts/rebuild_ambre_grid.py` reads the raw AMBRE `*.zip` archives, bins
each spectrum onto a common wavelength grid (Å) and writes a single parquet
file compatible with `prepare_ambre(parquet_path=...)`. See
[Quick Start §1](#1-optional-build-a-pre-binned-ambre-parquet-grid).

## Tests

```bash
pytest tests/
```

Coverage configuration, dependency metadata and the `gaia-twins` console
script are all declared in `pyproject.toml`.

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgments

- Gaia mission: <https://www.cosmos.esa.int/gaia>
- AMBRE stellar atmosphere models: <https://pollux.oreme.org/explore/AMBRE/>
- GaiaXPy: <https://gaia-dpci.github.io/GaiaXPy-website/>
