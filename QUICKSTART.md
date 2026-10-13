# gaia-twins — Quick Start

Generate high-resolution synthetic "twin" spectra for Gaia stars by
interpolating the AMBRE stellar-atmosphere grid at Gaia astrophysical
parameters (Teff, log g, [M/H]).

## Installation

```bash
pip install -e ".[dev]"
```

## 1. Python API (defaults)

The package ships a pre-binned AMBRE grid, so nothing needs to be configured:

```python
from gaia_twins import SyntheticSpectrumGenerator

gen = SyntheticSpectrumGenerator()   # bundled grid used automatically
gen.prepare_ambre()

results = gen.generate_twins([5853498713190525696])
print(results[["teff", "logg", "mh", "twin_filename"]])
```

One-off spectrum from known parameters:

```python
wave, flux = gen.generate_spectrum(teff=5772.0, logg=4.44, mh=0.02)
```

By default, fetched Gaia parameters are cached in `~/.cache/gaia-twins` (set
`GAIA_TWINS_CACHE_DIR` to change, or pass `cache_dir=False` to disable).

Using your own full AMBRE grid (ZIPs or parquet):

```python
gen = SyntheticSpectrumGenerator(ambre_dir="AMBRE")
gen.prepare_ambre(parquet_path="AMBRE/ambre_complete_binned_10.0A.parquet")
```

## 2. CLI

```bash
# Out of the box (bundled grid used automatically)
gaia-twins -i source_ids.txt -o results.parquet -f parquet

# With a custom AMBRE directory
gaia-twins -i source_ids.txt -a AMBRE \
    --parquet AMBRE/ambre_complete_binned_10.0A.parquet -o results.parquet -f parquet

gaia-twins --help
```

## 3. Tests

```bash
pytest tests/
```
