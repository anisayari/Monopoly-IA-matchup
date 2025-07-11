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

## 🤖 AI System Overview

The AI system consists of three main components:

1. **GameEventListener**: Monitors real game events and detects when AI decisions are needed
2. **AIGameManager**: Central orchestrator that syncs game state and requests AI decisions
3. **ActionExecutor**: Executes AI decisions using OmniParser for UI interaction

The system supports multiple AI players simultaneously and can use different OpenAI models (GPT-4, GPT-3.5, etc.)

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
│       ├── game_event_listener.py  # Game event detection
│       ├── ai_game_manager.py      # AI orchestration
│       ├── action_executor.py      # UI interaction via OmniParser
│       └── ai_integration.py       # Helper for easy integration
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

### 🚀 Quick Start

```bash
# Launch the interactive launcher
python launcher.py
```

This opens an interactive menu where you can:
- ✅ Check prerequisites (Dolphin, OpenAI API key, etc.)
- 🎮 Launch console mode
- 🌐 Launch web interface
- 🤖 Launch AI mode
- 🧪 Run tests

### Launch Modes

#### 1. Console Mode (without AI)
Displays real-time game events in the terminal.

#### 2. Web Interface
Opens a browser interface to monitor the game at http://localhost:5000

#### 3. AI Mode 🤖
Let AI players control the game automatically.

### Prerequisites for AI Mode
1. Set OpenAI API key: `export OPENAI_API_KEY="your-api-key"`
2. Start OmniParser (for automatic clicks):
   ```bash
   cd omniparserserver
   docker-compose up
   ```

### AI Configuration Options
- Choose which players should be AI-controlled (e.g., 0, 1, 2)
- Select AI model (GPT-4, GPT-3.5-turbo)
- Adjust temperature for AI behavior (0.0-1.0)

## Interface Web

Une interface web a été ajoutée pour faciliter la gestion et la visualisation du jeu Monopoly. Cette interface permet de :

- Visualiser le contexte du jeu en temps réel
- Modifier les informations des joueurs (nom, argent)
- Démarrer et arrêter l'émulateur Dolphin
- Redémarrer le jeu
- Configurer les chemins des fichiers nécessaires

### Installation

Pour utiliser l'interface web, assurez-vous d'avoir installé les dépendances supplémentaires :

```bash
pip install -r requirements.txt
```

### Démarrage de l'interface web

Pour démarrer l'interface web, exécutez :

```bash
python run_web.py
```

L'interface sera accessible à l'adresse http://localhost:5000 dans votre navigateur.

## 🧪 Testing

### Running AI Module Tests

The project includes comprehensive tests for the AI system:

```bash
# Run all AI tests
./run_tests_final.sh

# Run specific test types
./run_tests_final.sh minimal   # Basic component tests
./run_tests_final.sh quick     # Quick import tests
```

### Test Structure

```
tests/ai/
├── test_game_event_listener.py  # Event detection tests
├── test_ai_game_manager.py      # AI orchestration tests
├── test_action_executor.py      # Action execution tests
├── test_integration.py          # Integration tests
├── test_offline_simulation.py   # Offline simulation tests
└── mock_helpers.py              # Test utilities
```

All tests run without external dependencies (Dolphin, OmniParser, etc.) using mocks.

### Configuration

Avant d'utiliser l'interface, vous devez configurer les chemins dans l'onglet "Configuration" :

- **Chemin de Dolphin** : Chemin vers l'exécutable Dolphin (ex: `C:\Program Files\Dolphin\Dolphin.exe`)
- **Chemin de l'ISO Monopoly** : Chemin vers le fichier ISO du jeu Monopoly
- **Chemin du fichier de sauvegarde** : Chemin vers le fichier de sauvegarde à utiliser

Vous pouvez également modifier ces chemins directement dans le fichier `config.py`.

### Fonctionnalités

#### Contrôle de Dolphin
- Démarrer/arrêter l'émulateur Dolphin
- Redémarrer le jeu Monopoly

#### Gestion des joueurs
- Modifier le nom des joueurs
- Ajuster le montant d'argent des joueurs

#### Visualisation du contexte
- Événements du jeu
- Informations sur les joueurs
- Propriétés et leur statut
- Plateau de jeu
- JSON brut du contexte

#### Terminal
- Affichage de la sortie du terminal en temps réel

### Utilisation en parallèle avec le backend

Vous pouvez toujours utiliser le backend séparément pour le débogage en exécutant :

```bash
python main.py
```

L'interface web détectera automatiquement les changements dans le fichier de contexte.

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
│       ├── game_event_listener.py  # Détection des événements
│       ├── ai_game_manager.py      # Orchestration IA
│       ├── action_executor.py      # Interaction UI via OmniParser
│       └── ai_integration.py       # Helper pour intégration facile
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

## 🤖 Vue d'ensemble du système IA

Le système IA se compose de trois composants principaux :

1. **GameEventListener** : Surveille les événements du jeu et détecte quand des décisions IA sont nécessaires
2. **AIGameManager** : Orchestrateur central qui synchronise l'état du jeu et demande des décisions à l'IA
3. **ActionExecutor** : Exécute les décisions de l'IA en utilisant OmniParser pour l'interaction UI

Le système prend en charge plusieurs joueurs IA simultanément et peut utiliser différents modèles OpenAI (GPT-4, GPT-3.5, etc.)

## 🔧 Utilisation

### 🚀 Démarrage Rapide

```bash
# Lancer le launcher interactif
python launcher.py
```

Cela ouvre un menu interactif où vous pouvez :
- ✅ Vérifier les prérequis (Dolphin, clé API OpenAI, etc.)
- 🎮 Lancer le mode console
- 🌐 Lancer l'interface web
- 🤖 Lancer le mode IA
- 🧪 Exécuter les tests

### Modes de Lancement

#### 1. Mode Console (sans IA)
Affiche les événements du jeu en temps réel dans le terminal.

#### 2. Interface Web
Ouvre une interface navigateur pour surveiller le jeu sur http://localhost:5000

#### 3. Mode IA 🤖
Laisse les joueurs IA contrôler le jeu automatiquement.

### Prérequis pour le Mode IA
1. Définir la clé API OpenAI : `export OPENAI_API_KEY="votre-clé-api"`
2. Démarrer OmniParser (pour les clics automatiques) :
   ```bash
   cd omniparserserver
   docker-compose up
   ```

### Options de Configuration IA
- Choisir quels joueurs sont contrôlés par l'IA (ex: 0, 1, 2)
- Sélectionner le modèle IA (GPT-4, GPT-3.5-turbo)
- Ajuster la température pour le comportement de l'IA (0.0-1.0)

## 🧪 Tests

### Exécution des tests du module IA

Le projet comprend des tests complets pour le système IA :

```bash
# Exécuter tous les tests IA
./run_tests_final.sh

# Exécuter des types de tests spécifiques
./run_tests_final.sh minimal   # Tests de composants de base
./run_tests_final.sh quick     # Tests d'import rapides
```

### Structure des tests

```
tests/ai/
├── test_game_event_listener.py  # Tests de détection d'événements
├── test_ai_game_manager.py      # Tests d'orchestration IA
├── test_action_executor.py      # Tests d'exécution d'actions
├── test_integration.py          # Tests d'intégration
├── test_offline_simulation.py   # Tests de simulation hors ligne
└── mock_helpers.py              # Utilitaires de test
```

Tous les tests s'exécutent sans dépendances externes (Dolphin, OmniParser, etc.) en utilisant des mocks.

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
