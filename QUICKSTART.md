# gaia-twins — Quick Start

Generate high-resolution synthetic "twin" spectra for Gaia stars by
interpolating the AMBRE stellar-atmosphere grid at Gaia astrophysical
parameters (Teff, log g, [M/H]).

## Installation

```bash
pip install -e ".[dev]"
```

## 1. Build a pre-binned AMBRE parquet grid (recommended)

```bash
python scripts/rebuild_ambre_grid.py \
    --ambre-dir AMBRE \
    --output AMBRE/ambre_complete_binned_10.0A.parquet \
    --wave-min 3000 --wave-max 11000 --wave-step 10.0
```

## 2. Python API

```python
from gaia_twins import SyntheticSpectrumGenerator

gen = SyntheticSpectrumGenerator(ambre_dir="AMBRE")
gen.prepare_ambre(parquet_path="AMBRE/ambre_complete_binned_10.0A.parquet")

results = gen.generate_twins([5853498713190525696])
print(results[["teff", "logg", "mh", "twin_filename"]])
```

One-off spectrum from known parameters:

```python
wave, flux = gen.generate_spectrum(teff=5772.0, logg=4.44, mh=0.02)
```

## 3. CLI

```bash
gaia-twins -i source_ids.txt \
    --parquet AMBRE/ambre_complete_binned_10.0A.parquet \
    -a AMBRE -o results.parquet -f parquet

gaia-twins --help
```

## Tests

```bash
pytest tests/
```
