# Examples

This directory contains example scripts demonstrating how to use the `gaia-synth-spectra` package.

## Files

- **basic_usage.py**: Basic example showing how to generate synthetic spectra from Gaia source IDs
- **cli_examples.py**: Examples of using the command-line interface

## Running the Examples

### Python API Example

```bash
cd examples/
python basic_usage.py
```

Make sure to update the `ambre_dir` path to point to your AMBRE data directory.

### CLI Examples

The `cli_examples.py` file contains documented command examples. To run them:

1. Create a text file with source IDs (one per line):
```bash
echo "5853498713190525696" > source_ids.txt
echo "5762406957886626432" >> source_ids.txt
```

2. Run the CLI tool:
```bash
gaia-synth -i source_ids.txt -o results.pkl -a /path/to/AMBRE
```

3. Load and inspect results:
```python
import pandas as pd
results = pd.read_pickle('results.pkl')
print(results)
```

## Requirements

Before running the examples, make sure the package is installed:

```bash
pip install -e ..
```

## Output

The examples will generate:
- `basic_example_spectrum.png`: Plot comparing synthetic and Gaia spectra
- `synthetic_spectra.pkl`: DataFrame with generated spectra
- `ambre_cache.pkl`: Cached AMBRE spectra (optional, but recommended for speed)
