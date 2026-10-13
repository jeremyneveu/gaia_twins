"""
Example: Basic usage of gaia-twins
===================================

This example demonstrates how to generate synthetic "twin" spectra from
Gaia source IDs by interpolating the AMBRE stellar-atmosphere grid.
"""

import matplotlib.pyplot as plt

from gaia_twins import SyntheticSpectrumGenerator

# Example Gaia DR3 source IDs (solar-type stars with good XP spectra).
source_ids = [
    5853498713190525696,  # Example source 1
    5762406957886626432,  # Example source 2
]

# Initialize the spectrum generator. The pre-binned AMBRE grid is shipped
# with the package, so no data path or arguments are required.
print("Initializing spectrum generator...")
generator = SyntheticSpectrumGenerator(interpolation_method="linear")

# Load the bundled pre-binned AMBRE grid and build the 4D interpolator.
# (Point the generator at your own AMBRE directory with ambre_dir=... /
# parquet_path=... if you keep the full grid elsewhere.)
print("Loading AMBRE grid...")
generator.prepare_ambre()

# Generate twin spectra (query Gaia, interpolate, match closest AMBRE model).
print(f"Generating twin spectra for {len(source_ids)} sources...")
results = generator.generate_twins(source_ids)

# Display metadata.
print("\nResults:")
print(results[["teff", "logg", "mh", "twin_filename"]])

# Plot the first synthetic spectrum.
if len(results) > 0:
    row = results.iloc[0]

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(
        row["synth_wave"],
        row["synth_flux"],
        label="Synthetic twin (AMBRE)",
        linewidth=1.5,
        alpha=0.8,
    )
    ax.set_xlabel("Wavelength (Å)", fontsize=12)
    ax.set_ylabel("Flux (W/nm/m²)", fontsize=12)
    ax.set_title(
        f"Source {row.name}\n"
        f"Teff={row['teff']:.0f} K, log g={row['logg']:.2f}, "
        f"[M/H]={row['mh']:.2f}\n"
        f"twin: {row.get('twin_filename', 'n/a')}",
        fontsize=13,
    )
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)
    plt.tight_layout()
    plt.savefig("basic_example_spectrum.png", dpi=150)
    print("\nPlot saved as 'basic_example_spectrum.png'")

# Save results (parquet by default; use format="pickle" to keep arrays intact).
output_file = "synthetic_spectra.parquet"
generator.save_spectra(results, output_file, format="parquet")
print(f"\nResults saved to {output_file}")

# Generator info.
info = generator.get_info()
print("\nGenerator configuration:")
for key, value in info.items():
    print(f"  {key}: {value}")
