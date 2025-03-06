# Système de Contexte pour Monopoly

Ce dossier contient les fichiers de contexte du jeu Monopoly. Le système de contexte permet de sauvegarder l'état global du jeu à chaque événement intéressant.

## Structure des fichiers

- `game_context.json` : Contient l'état actuel du jeu, mis à jour en temps réel.
- `history/` : Dossier contenant l'historique des contextes, avec un fichier pour chaque événement important.
  - Format des fichiers : `timestamp_event_type.json`

## Structure du contexte

Le fichier de contexte contient les informations suivantes :

```json
{
  "timestamp": 1234567890,
  "players": {
    "player_id": {
      "id": "player_id",
      "name": "Nom du joueur",
      "money": 1500,
      "position": 0,
      "goto": 0,
      "dices": [0, 0],
      "properties": [
        {
          "id": "property_id",
          "name": "Nom de la propriété",
          "price": 200,
          "rent": 10,
          "color": "blue"
        }
      ]
    }
  },
  "properties": {
    "property_id": {
      "id": "property_id",
      "name": "Nom de la propriété",
      "price": 200,
      "rent": 10,
      "color": "blue",
      "owner": "player_id"
    }
  },
  "current_auction": {
    "current_bidder": 0,
    "current_price": 100,
    "next_price": 110
  },
  "last_events": [
    {
      "type": "player_money_changed",
      "timestamp": 1234567890,
      "details": {
        "player_id": "player_id",
        "name": "Nom du joueur",
        "old_value": 1500,
        "new_value": 1600,
        "diff": 100
      }
    }
  ]
}
```

## Événements enregistrés

Le système de contexte enregistre les événements suivants :

- `player_added` : Un joueur a rejoint la partie
- `player_removed` : Un joueur a quitté la partie
- `player_money_changed` : L'argent d'un joueur a changé
- `player_name_changed` : Le nom d'un joueur a changé
- `player_dice_changed` : Les dés d'un joueur ont changé
- `player_goto_changed` : La destination d'un joueur a changé
- `player_position_changed` : La position d'un joueur a changé
- `auction_started` : Une enchère a commencé
- `auction_ended` : Une enchère s'est terminée
- `auction_bid` : Une enchère a été faite
- `message_added` : Un message a été ajouté

## Utilisation

Le système de contexte est automatiquement initialisé au démarrage du jeu. Il n'y a pas besoin d'interaction supplémentaire pour l'utiliser.

Pour accéder aux données de contexte, vous pouvez simplement lire le fichier `game_context.json` ou parcourir les fichiers d'historique dans le dossier `history/`. 