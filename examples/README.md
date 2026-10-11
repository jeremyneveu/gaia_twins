# Examples

This directory contains example scripts demonstrating how to use the
`gaia-twins` package.

## Files

- **basic_usage.py**: Python API — generate synthetic "twin" spectra from
  Gaia source IDs by interpolating the AMBRE grid.
- **cli_examples.py**: Documented `gaia-twins` command-line invocations.

## Running the Examples

### Python API Example

```bash
cd examples/
python basic_usage.py
```

Before running, make sure:
- The pre-binned AMBRE grid exists
  (`AMBRE/ambre_complete_binned_10.0A.parquet`, see
  `scripts/rebuild_ambre_grid.py`), and
- You update the `ambre_dir` / `parquet_path` paths to match your data.

### CLI Examples

`cli_examples.py` contains documented commands. To run one:

1. Create a text file with source IDs (one per line):
```bash
echo "5853498713190525696" > source_ids.txt
echo "5762406957886626432" >> source_ids.txt
```

2. Run the CLI tool:
```bash
gaia-twins -i source_ids.txt \
    --parquet AMBRE/ambre_complete_binned_10.0A.parquet \
    -a AMBRE -o results.pkl -f pickle
```

3. Load and inspect results:
```python
import pandas as pd
results = pd.read_pickle('results.pkl')
print(results)
```

## Requirements

Before running the examples, install the package:

```bash
pip install -e ..
```

## Output

The examples will generate:
- `basic_example_spectrum.png`: Plot of a generated synthetic twin spectrum
- `synthetic_spectra.parquet`: DataFrame with generated twin spectra
