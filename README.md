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

### 1. Python API (defaults — nothing to configure)

Starting with `v0.1.0`, a pre-binned AMBRE grid (10 Å) is **shipped inside the
package**, so the library works out of the box after `pip install`. No data
folder or argument is required:

```python
from gaia_twins import SyntheticSpectrumGenerator

generator = SyntheticSpectrumGenerator()  # bundled grid is used automatically

# Load the bundled pre-binned AMBRE grid and build the 4D interpolator.
generator.prepare_ambre()

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

By default, stellar parameters fetched from Gaia are **cached** in a user-level
directory (`~/.cache/gaia-twins`) so already-queried source IDs are served
locally and new ones are appended automatically. Pass `cache_dir=False` to
disable caching, or set `GAIA_TWINS_CACHE_DIR` to customise the location.

### 2. Using a custom / full AMBRE grid

If you keep the full AMBRE archive (ZIPs or your own pre-binned parquet),
point the library at it — either via env var or explicit arguments:

```bash
export GAIA_TWINS_AMBRE_DIR=/path/to/AMBRE
```

```python
generator = SyntheticSpectrumGenerator(ambre_dir="/path/to/AMBRE")
generator.prepare_ambre(parquet_path="/path/to/AMBRE/ambre_complete_binned_10.0A.parquet")
```

The full raw grid can be rebuilt with `scripts/rebuild_ambre_grid.py`
(see [Rebuilding the AMBRE grid](#rebuilding-the-ambre-grid)).

### 3. Command-line interface

```bash
# Works out of the box (bundled grid used automatically)
gaia-twins -i source_ids.txt -o results.parquet -f parquet

# From explicit source IDs, with a custom AMBRE directory
gaia-twins -s 5853498713190525696 5762406957886626432 \
    -a /path/to/AMBRE --parquet /path/to/AMBRE/ambre_complete_binned_10.0A.parquet \
    -o results.pkl -f pickle
```

Key options:

```
  -i, --input FILE        Input file with source IDs (text, CSV or parquet)
  -s, --source-ids ID...  Gaia source IDs (space-separated)
  -a, --ambre-dir DIR     Directory containing AMBRE ZIP files (default: bundled grid)
      --parquet FILE      Pre-binned AMBRE parquet grid (default: bundled grid)
  -o, --output FILE       Output file (default: twin_spectra.pkl)
  -f, --format FMT        pickle | parquet | csv | hdf5 (default: pickle)
      --wave-min FLOAT    Min wavelength for the ZIP path (Å, default 3000)
      --wave-max FLOAT    Max wavelength for the ZIP path (Å, default 11000)
      --wave-step FLOAT   Bin width for the ZIP path (Å, default 10)
      --interp-method M   linear | nearest (default: linear)
      --gspspec           Use GSP-Spec instead of GSP-Phot parameters
      --cache-dir DIR     Directory for AMBRE grid + Gaia params caching
  -v, --verbose           Verbose logging
```

> **Note:** `gaia-twins --help` lists the authoritative set of options.

### Environment variables

| Variable | Purpose |
|----------|---------|
| `GAIA_TWINS_AMBRE_DIR` | Directory holding a full AMBRE grid (overrides the bundled data) |
| `GAIA_TWINS_DATA_DIR`  | Alternative override for the AMBRE data directory |
| `GAIA_TWINS_CACHE_DIR` | Directory used for the persistent cache |

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
