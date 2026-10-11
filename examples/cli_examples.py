"""
Example: Command-line interface usage
======================================

This script documents how to use the `gaia-twins` command-line tool.
"""

# Example 1: Generate twins from a text file with one source ID per line.
"""
gaia-twins -i source_ids.txt \
    --parquet AMBRE/ambre_complete_binned_10.0A.parquet \
    -a AMBRE -o results.parquet -f parquet
"""

# Example 2: Generate twins from explicit source IDs (pickle keeps arrays).
"""
gaia-twins -s 5853498713190525696 5762406957886626432 \
    --parquet AMBRE/ambre_complete_binned_10.0A.parquet \
    -a AMBRE -o results.pkl -f pickle
"""

# Example 3: Without a parquet grid (slow ZIP path, custom grid in Angstrom).
"""
gaia-twins -i source_ids.txt -a AMBRE -o results.parquet -f parquet \
    --wave-min 4000 --wave-max 9000 --wave-step 10.0
"""

# Example 4: Different interpolation method.
"""
gaia-twins -i source_ids.txt \
    --parquet AMBRE/ambre_complete_binned_10.0A.parquet \
    -a AMBRE -o results.parquet -f parquet --interp-method nearest
"""

# Example 5: Verbose output for debugging.
"""
gaia-twins -i source_ids.txt \
    --parquet AMBRE/ambre_complete_binned_10.0A.parquet \
    -a AMBRE -o results.parquet -f parquet --gspspec -v
"""

# Example 6: Process a CSV/parquet input file with a 'source_id' column.
"""
gaia-twins -i gaia_sources.csv \
    --parquet AMBRE/ambre_complete_binned_10.0A.parquet \
    -a AMBRE -o results.parquet -f parquet
"""

print("See above for example commands to run the gaia-twins CLI tool")
print("\nFor help on all options, run:")
print("  gaia-twins --help")
