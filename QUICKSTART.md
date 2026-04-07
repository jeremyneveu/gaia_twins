# gaia-synth-spectra

Package Python pour générer des spectres synthétiques stellaires à partir d'IDs Gaia en utilisant les modèles AMBRE.

## Installation

```bash
# Mode utilisateur
pip install .

# Mode développement (avec pytest, black, flake8)
pip install -e ".[dev]"

# Avec matplotlib pour les plots
pip install -e ".[dev,plots]"
```

## Utilisation Rapide

### Python API
```python
from gaia_synth_spectra import SyntheticSpectrumGenerator

generator = SyntheticSpectrumGenerator(
    ambre_dir='path/to/AMBRE',
    wavelength_min=330.0,
    wavelength_max=1050.0,
    wavelength_step=0.5
)

generator.prepare_ambre(cache_file='ambre_cache.pkl')
results = generator.generate_spectra([5853498713190525696])
```

### CLI
```bash
gaia-synth -i source_ids.txt -o results.pkl -a /path/to/AMBRE
```

## Tests

```bash
pytest tests/ -v
pytest tests/ --cov=gaia_synth_spectra --cov-report=html
```

## Configuration

Tout est dans **`pyproject.toml`** :
- ✅ Métadonnées du package
- ✅ Dépendances (principales et optionnelles)
- ✅ Scripts CLI (`gaia-synth`)
- ✅ Configuration pytest
- ✅ Configuration coverage
- ✅ Configuration black

Plus besoin de `setup.py`, `setup.cfg`, ou `requirements.txt` !

## Structure

```
gaia_synth_spectra/
├── pyproject.toml              # Configuration unique (TOML)
├── .gitlab-ci.yml              # CI/CD
├── gaia_synth_spectra/
│   ├── src/                    # Code principal (renommé de core/)
│   │   ├── gaia_query.py
│   │   ├── ambre_loader.py
│   │   ├── interpolator.py
│   │   └── spectrum_generator.py
│   ├── utils/                  # Utilitaires
│   │   ├── binning.py
│   │   ├── normalization.py
│   │   └── validators.py
│   └── cli/                    # Interface ligne de commande
│       └── main.py
└── tests/                      # Tests unitaires (44 tests)
    ├── test_validators.py
    ├── test_binning.py
    └── test_normalization.py
```

## Documentation

- **README.md** - Documentation complète
- **CHANGES.md** - Historique des modifications
- **MIGRATION_TOML.md** - Migration vers TOML unique
- **tests/README.md** - Guide des tests
- **examples/** - Exemples d'utilisation

## Licence

MIT
