"""
Example: Command-line interface usage
======================================

This script demonstrates how to use the gaia-synth command-line tool.
"""

# Example 1: Generate spectra from a text file with source IDs
# File: source_ids.txt (one ID per line)
# Command:
"""
gaia-synth -i source_ids.txt -o results.pkl -a ../AMBRE
"""

# Example 2: Generate spectra from command-line arguments
# Command:
"""
gaia-synth -s 5853498713190525696 5762406957886626432 \
    -o results.pkl -a ../AMBRE
"""

# Example 3: Custom wavelength range
# Command:
"""
gaia-synth -i source_ids.txt -o results.pkl -a ../AMBRE \
    --wave-min 400 --wave-max 900 --wave-step 1.0
"""

# Example 4: Use caching for faster processing
# Command:
"""
gaia-synth -i source_ids.txt -o results.pkl -a ../AMBRE \
    --ambre-cache ambre_cache.pkl
"""

# Example 5: Different output formats
# Pickle (includes spectra):
"""
gaia-synth -i source_ids.txt -o results.pkl -a ../AMBRE -f pickle
"""

# Parquet (metadata only):
"""
gaia-synth -i source_ids.txt -o results.parquet -a ../AMBRE -f parquet
"""

# HDF5:
"""
gaia-synth -i source_ids.txt -o results.h5 -a ../AMBRE -f hdf5
"""

# Example 6: Verbose output for debugging
# Command:
"""
gaia-synth -i source_ids.txt -o results.pkl -a ../AMBRE -v
"""

# Example 7: Process CSV file with source_id column
# Command:
"""
gaia-synth -i gaia_sources.csv -o results.pkl -a ../AMBRE
"""

# Example 8: Custom interpolation settings
# Command:
"""
gaia-synth -i source_ids.txt -o results.pkl -a ../AMBRE \
    --interp-method kdtree --n-neighbors 8
"""

# Example 9: Large batch processing
# Command:
"""
gaia-synth -i large_source_list.txt -o results.pkl -a ../AMBRE \
    --batch-size 500 --ambre-cache ambre_cache.pkl -v
"""

print("See above for example commands to run gaia-synth CLI tool")
print("\nFor help on all options, run:")
print("  gaia-synth --help")
