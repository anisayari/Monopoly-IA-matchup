⚠️ **Project Status: Under Construction** - This project is actively being developed.
⚠️ **Statut du Projet : En Construction** - Ce projet est en cours de développement.

# 🎲 MonopolyIA - LLM Matchup Arena

[English](#english) | [Français](#français)

# English

A groundbreaking framework for evaluating Large Language Models (LLMs) performance through Monopoly gameplay, combining game memory analysis and artificial intelligence.

## 🎯 Project Goal

This project aims to create a standardized environment to:
- Evaluate LLMs' strategic reasoning capabilities
- Compare different models in a complex game context
- Analyze AI decision-making in simulated economic situations
- Measure LLM performance in a rule-based environment

## 🏗️ Architecture

```
monopolyIA/
├── src/
│   ├── core/              # Core engine
│   │   ├── memory_reader.py   # Dolphin interface
│   │   └── memory_addresses.py # Memory mapping
│   ├── models/            # Data structures
│   │   ├── player.py      # Player management
│   │   ├── property.py    # Property management
│   │   └── enums.py       # Constants and enums
│   ├── game/              # Game logic
│   │   └── monopoly.py    # Main controller
│   └── ai/               # AI integration
│       ├── agents/       # LLM models
│       └── evaluator.py  # Performance metrics
└── main.py               # Entry point
```

## 🚀 Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/MonopolyIA-matchup.git
cd MonopolyIA-matchup
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Environment setup:
- Install Dolphin Emulator
- Configure paths in `config.yaml`
- Set up LLM API credentials (if needed)

## 💡 Features

### Core Features
- 🎮 Dolphin Memory Engine Integration
- 🤖 Multi-LLM Support (Claude, GPT-4, etc.)
- 📊 Real-time Performance Metrics
- 🔄 Replay System for Post-game Analysis

### Monitoring
- 💰 Transaction and Asset Tracking
- 📍 Position and Movement Monitoring
- 🎲 Game Decision Analysis
- 📈 Progress Graphs

## 🔧 Usage

### Basic Configuration
```python
from src import MonopolyGame
from src.ai import LLMAgent

# Initialize a game
game = MonopolyGame()

# Configure AI agents
agent1 = LLMAgent(model="claude-3", name="Claude")
agent2 = LLMAgent(model="gpt-4", name="GPT-4")

# Start a match
game.start_match(agent1, agent2)
```

---

# Français

Un framework innovant pour évaluer les performances des modèles de langage (LLMs) à travers des parties de Monopoly, combinant l'analyse de mémoire de jeu et l'intelligence artificielle.

## 🎯 Objectif du Projet

Ce projet vise à créer un environnement standardisé permettant de :
- Évaluer les capacités de raisonnement stratégique des LLMs
- Comparer différents modèles dans un contexte de jeu complexe
- Analyser la prise de décision des IA dans des situations économiques simulées
- Mesurer la performance des LLMs dans un environnement aux règles strictes

## 🏗️ Architecture

```
monopolyIA/
├── src/
│   ├── core/              # Moteur principal
│   │   ├── memory_reader.py   # Interface avec Dolphin
│   │   └── memory_addresses.py # Mapping mémoire
│   ├── models/            # Structures de données
│   │   ├── player.py      # Gestion des joueurs
│   │   ├── property.py    # Gestion des propriétés
│   │   └── enums.py       # Constantes et énumérations
│   ├── game/              # Logique de jeu
│   │   └── monopoly.py    # Contrôleur principal
│   └── ai/               # Intégration IA
│       ├── agents/       # Différents modèles LLM
│       └── evaluator.py  # Métriques de performance
└── main.py               # Point d'entrée
```

## 🚀 Installation

1. Cloner le repository :
```bash
git clone https://github.com/votre-username/MonopolyIA-matchup.git
cd MonopolyIA-matchup
```

2. Installer les dépendances :
```bash
pip install -r requirements.txt
```

3. Configuration de l'environnement :
- Installer Dolphin Emulator
- Configurer les chemins d'accès dans `config.yaml`
- Préparer les credentials API pour les LLMs (si nécessaire)

## 💡 Fonctionnalités

### Fonctionnalités Principales
- 🎮 Interface avec Dolphin Memory Engine
- 🤖 Support multi-LLM (Claude, GPT-4, etc.)
- 📊 Métriques de performance en temps réel
- 🔄 Système de replay pour analyse post-partie

### Surveillance
- 💰 Suivi des transactions et des actifs
- 📍 Tracking des positions et mouvements
- 🎲 Analyse des décisions de jeu
- 📈 Graphiques de progression

## 🔧 Utilisation

### Configuration de Base
```python
from src import MonopolyGame
from src.ai import LLMAgent

# Initialiser une partie
game = MonopolyGame()

# Configurer les agents IA
agent1 = LLMAgent(model="claude-3", name="Claude")
agent2 = LLMAgent(model="gpt-4", name="GPT-4")

# Démarrer un match
game.start_match(agent1, agent2)
```

## 📊 Métriques d'Évaluation

- Taux de victoire
- Rentabilité des investissements
- Temps de décision moyen
- Qualité des négociations
- Adaptabilité stratégique

## 🤝 Contribution

Les contributions sont les bienvenues ! Consultez notre guide de contribution pour plus de détails.

## 📝 License

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.
