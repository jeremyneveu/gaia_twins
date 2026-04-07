# Tests

Ce dossier contient les tests unitaires pour le package `gaia-synth-spectra`.

## Structure

- `test_validators.py` - Tests pour le module de validation
- `test_binning.py` - Tests pour le module de binning spectral
- `test_normalization.py` - Tests pour le module de normalisation

## Exécuter les tests

### Localement

```bash
# Installer les dépendances de test
pip install -e ".[dev]"

# Exécuter tous les tests
pytest tests/

# Avec couverture de code
pytest tests/ --cov=gaia_synth_spectra --cov-report=html

# Exécuter un fichier de test spécifique
pytest tests/test_validators.py -v

# Exécuter une classe de test spécifique
pytest tests/test_validators.py::TestValidateSourceIds -v

# Exécuter un test spécifique
pytest tests/test_validators.py::TestValidateSourceIds::test_valid_source_ids_list -v
```

### Intégration Continue (GitLab CI)

Les tests s'exécutent automatiquement sur GitLab CI pour :
- Chaque push sur `main` ou `develop`
- Chaque merge request

Les tests sont exécutés sur plusieurs versions de Python :
- Python 3.8
- Python 3.9
- Python 3.10 (principal + rapport de couverture)
- Python 3.11

## Couverture de Code

Le rapport de couverture HTML est généré automatiquement et disponible dans :
- Localement : `htmlcov/index.html`
- GitLab CI : Artefacts du job `test`

## Ajouter de Nouveaux Tests

Pour ajouter de nouveaux tests :

1. Créer un fichier `test_*.py` dans ce dossier
2. Utiliser la convention de nommage pytest :
   - Classes : `Test*`
   - Fonctions : `test_*`
3. Organiser les tests en classes par fonctionnalité
4. Documenter chaque test avec un docstring

Exemple :

```python
"""Tests for my_module."""

import pytest
from gaia_synth_spectra.my_module import my_function


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

- Les tests sont légers et n'utilisent pas de données AMBRE réelles
- Les tests se concentrent sur les fonctions utilitaires et la validation
- Pour tester avec de vraies données AMBRE, utiliser les exemples dans `examples/`
