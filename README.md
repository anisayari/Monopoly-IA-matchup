# MonopolyIA

Un projet d'automatisation du jeu Monopoly utilisant Dolphin Memory Engine pour lire et écrire dans la mémoire du jeu.

## Structure du projet

```
monopolyIA/
├── src/                    # Code source
│   ├── core/              # Fonctionnalités de base
│   │   ├── memory_reader.py   # Lecture/écriture mémoire
│   │   └── memory_addresses.py # Adresses mémoire
│   ├── models/            # Modèles de données
│   │   ├── player.py      # Classe joueur
│   │   ├── property.py    # Classe propriété
│   │   └── enums.py       # Énumérations
│   └── game/              # Logique du jeu
│       └── monopoly.py    # Classe principale
└── main.py                # Point d'entrée

```

## Installation

1. Cloner le repository
2. Installer les dépendances :
```bash
pip install -r requirements.txt
```

## Utilisation

```python
from src import MonopolyGame

game = MonopolyGame()

# Accès aux informations des joueurs
print(f"{game.blue_player.label} has ${game.blue_player.money}")
print(f"{game.red_player.label} has ${game.red_player.money}")

# Modification des valeurs
game.blue_player.money = 5000
game.red_player.label = "Player 2"

# Accès aux propriétés
for prop in game.properties:
    print(f"{prop.name}: ${prop.price}")
```

## Fonctionnalités

- Lecture/écriture de la mémoire du jeu
- Gestion des joueurs (argent, position, dés)
- Gestion des propriétés
- Lecture des dialogues du jeu

## Notes techniques

Pour trouver les messages dans la mémoire du jeu :
```javascript
// Convertir le texte en Array Bytes (Node.js)
Array.from(Buffer.from("Pentonville Road"))
    .map(e=>([e.toString(16).padStart(2, "0"),"00"]))
    .flat()
    .join(' ')
``` #   M o n o p o l y - I A - m a t c h u p  
 