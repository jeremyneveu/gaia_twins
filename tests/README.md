# Tests

Tests unitaires pour le package `gaia-twins`.

## Structure

- `test_ambre_loader.py` - Chargement et catalogage des archives AMBRE
  (ZIP), lecture des spectres, binning, parquet et `find_closest`.
- `test_binning.py` - Binning spectral (utilitaires).
- `test_interpolator.py` - Interpolation 4D de la grille AMBRE.
- `test_normalization.py` - Normalisation spectrale (utilitaires).
- `test_spectrum_generator.py` - Génération de spectres synthétiques,
  métadonnées et persistance.
- `test_validators.py` - Validation des entrées (source IDs, longueurs
  d'onde, paramètres, formats).

## Exécuter les tests

### Localement

```bash
# Installer les dépendances de test
pip install -e ".[dev]"

# Exécuter tous les tests
pytest tests/

# Avec couverture de code
pytest tests/ --cov=gaia_twins --cov-report=html

# Exécuter un fichier de test spécifique
pytest tests/test_interpolator.py -v

# Exécuter un test spécifique
pytest tests/test_ambre_loader.py::TestFindClosest::test_closest_match -v
```

## Couverture de Code

Le rapport de couverture HTML peut être généré localement :

```bash
pytest tests/ --cov=gaia_twins --cov-report=html
# Disponible dans htmlcov/index.html
```

## Ajouter de Nouveaux Tests

1. Créer un fichier `test_*.py` dans ce dossier.
2. Utiliser la convention de nommage pytest :
   - Classes : `Test*`
   - Fonctions : `test_*`
3. Organiser les tests en classes par fonctionnalité.
4. Documenter chaque test avec un docstring.

Exemple :

```python
"""Tests for my_module."""

import pytest
from gaia_twins.src.my_module import my_function


class TestMyFunction:
    """Test my_function."""

    def test_basic_case(self):
        """Test basic functionality."""
        result = my_function(input_value)
        assert result == expected_value

    def test_edge_case(self):
        """Test edge case."""
        with pytest.raises(ValueError):
            my_function(invalid_input)
```

## Notes

- Les tests sont légers et n'utilisent pas de données AMBRE réelles.
- Pour tester avec de vraies données AMBRE, utiliser les exemples dans
  `examples/` et le script `scripts/rebuild_ambre_grid.py`.
