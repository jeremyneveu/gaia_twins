"""
Example: Basic usage of gaia-synth-spectra
===========================================

This example demonstrates basic usage of the package to generate
synthetic spectra from Gaia source IDs.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from gaia_synth_spectra import SyntheticSpectrumGenerator

# Example Gaia DR3 source IDs
# These are solar-type stars with good XP spectra
source_ids = [
    5853498713190525696,  # Example source 1
    5762406957886626432,  # Example source 2
]

# Initialize the spectrum generator
print("Initializing spectrum generator...")
generator = SyntheticSpectrumGenerator(
    ambre_dir='../AMBRE',  # Path to AMBRE directory
    wavelength_min=330.0,   # nm
    wavelength_max=1050.0,  # nm
    wavelength_step=0.5,    # nm
    interpolation_method='knn',
    n_neighbors=4
)

# Prepare AMBRE data (this will cache the spectra)
print("Loading AMBRE spectra...")
generator.prepare_ambre(cache_file='ambre_cache.pkl')

# Generate synthetic spectra
print(f"Generating synthetic spectra for {len(source_ids)} sources...")
results = generator.generate_spectra(source_ids)

# Display results
print("\nResults:")
print(results[['source_id', 'teff_gspphot', 'logg_gspphot', 'mh_gspphot']])

# Plot first spectrum
if len(results) > 0:
    idx = 0
    row = results.iloc[idx]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Plot synthetic spectrum
    ax.plot(
        row['synth_wave'], 
        row['synth_flux'],
        label='Synthetic (AMBRE)',
        linewidth=1.5,
        alpha=0.8
    )
    
    # Plot Gaia XP spectrum
    if 'gaia_wave' in results.columns:
        ax.plot(
            row['gaia_wave'],
            row['gaia_flux'],
            label='Gaia XP',
            linewidth=1.5,
            alpha=0.8
        )
    
    ax.set_xlabel('Wavelength (nm)', fontsize=12)
    ax.set_ylabel('Flux (W/nm/m²)', fontsize=12)
    ax.set_title(
        f"Source {row['source_id']}\n"
        f"Teff={row['teff_gspphot']:.0f} K, "
        f"log g={row['logg_gspphot']:.2f}, "
        f"[M/H]={row['mh_gspphot']:.2f}",
        fontsize=14
    )
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('basic_example_spectrum.png', dpi=150)
    print("\nPlot saved as 'basic_example_spectrum.png'")
    plt.show()

# Save results
output_file = 'synthetic_spectra.pkl'
results.to_pickle(output_file)
print(f"\nResults saved to {output_file}")

# Get generator info
info = generator.get_info()
print("\nGenerator configuration:")
for key, value in info.items():
    print(f"  {key}: {value}")
