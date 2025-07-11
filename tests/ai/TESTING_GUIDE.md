# Guide de Test pour le Module AI

## Vue d'ensemble

Les tests du module AI sont conçus pour fonctionner sans dépendances externes. Tous les modules externes (dolphin_memory_engine, pyautogui, etc.) sont mockés.

## Scripts de Test Disponibles

### 1. **run_tests_final.sh** (Recommandé)
Le script principal qui gère toutes les dépendances et lance les tests correctement.

```bash
# Lancer tous les tests
./run_tests_final.sh

# Options disponibles
./run_tests_final.sh all      # Tous les tests (défaut)
./run_tests_final.sh minimal   # Tests minimaux
./run_tests_final.sh quick     # Tests rapides d'import
./run_tests_final.sh help      # Aide
```

### 2. **test_ai_minimal.py**
Tests minimaux qui vérifient les composants de base.

```bash
python3 test_ai_minimal.py
```

### 3. **run_ai_tests.py**
Runner Python avec mocking complet (peut avoir des problèmes de threading).

```bash
python3 run_ai_tests.py
```

## Structure des Tests

### Tests Unitaires

1. **test_game_event_listener.py**
   - Teste la détection d'événements
   - Vérifie la création de contextes de décision
   - Valide les patterns de messages

2. **test_ai_game_manager.py**
   - Teste l'orchestration AI
   - Vérifie la synchronisation d'état
   - Teste la gestion multi-joueurs

3. **test_action_executor.py**
   - Teste la logique d'exécution d'actions
   - Vérifie la détection d'éléments UI
   - Teste la gestion d'erreurs

### Tests d'Intégration

4. **test_integration.py**
   - Teste le workflow complet
   - Vérifie les interactions entre composants

5. **test_offline_simulation.py**
   - Simule des scénarios complets
   - Teste sans dépendances externes

## Résolution de Problèmes

### Erreur "No module named 'dolphin_memory_engine'"
Les tests incluent des mocks pour cette dépendance. Utilisez `run_tests_final.sh`.

### Tests qui ne se terminent pas
Certains tests peuvent créer des threads. Utilisez les tests minimaux :
```bash
./run_tests_final.sh minimal
```

### Erreur d'import
Assurez-vous d'être dans le répertoire racine du projet :
```bash
cd /Users/anisayari/Desktop/projects/Monopoly-IA-matchup
./run_tests_final.sh
```

## Résultats Attendus

Avec `./run_tests_final.sh`, vous devriez voir :

```
✅ All tests passed!
```

Les composants testés incluent :
- ✓ Types de décisions (9 types)
- ✓ Contextes de décision
- ✓ Éléments UI
- ✓ Listener d'événements
- ✓ Exécuteur d'actions

## Développement de Nouveaux Tests

Pour ajouter de nouveaux tests :

1. Créez votre fichier de test dans `tests/ai/`
2. Importez les mocks nécessaires
3. Ajoutez votre test aux scripts de lancement

Exemple :
```python
import sys
import os
import unittest
from unittest.mock import Mock

# Mock les dépendances
sys.modules['dolphin_memory_engine'] = Mock()

# Votre test ici
class TestNewFeature(unittest.TestCase):
    def test_something(self):
        self.assertTrue(True)
```

## CI/CD

Les tests sont conçus pour fonctionner en environnement CI :
- Pas de dépendances système requises
- Tous les modules externes sont mockés
- Exécution rapide (< 10 secondes)
- Code de sortie approprié (0 = succès, 1 = échec)