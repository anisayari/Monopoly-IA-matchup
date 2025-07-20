# Documentation: Maisons et Hôtels dans le Contexte de Jeu

## Vue d'ensemble

Le système de contexte récupère maintenant automatiquement le nombre de maisons et d'hôtels sur chaque propriété à chaque tour. Ces informations sont disponibles dans le fichier `contexte/game_context.json` et peuvent être utilisées par l'IA pour prendre des décisions.

## Structure des données

### Pour chaque propriété

Chaque propriété dans `context.global.properties` contient maintenant :

```json
{
  "id": 1,
  "name": "Old Kent Road",
  "group": "brown",
  "price": 60,
  "rent": [2, 10, 30, 90, 160, 250],
  "current_rent": 10,      // Loyer actuel basé sur les constructions
  "house_price": 50,
  "owner": "player1",
  "houses": 1,             // 0-4 maisons, 5 = hôtel
  "has_hotel": false,      // true si houses == 5
  "coordinates": {...}
}
```

### Résumé global des constructions

Un nouveau champ `context.global.buildings_summary` fournit un résumé :

```json
{
  "total_houses": 8,       // Total de maisons sur le plateau
  "total_hotels": 2,       // Total d'hôtels sur le plateau
  "properties_with_houses": [
    {
      "name": "Old Kent Road",
      "houses": 2,
      "owner": "player1",
      "group": "brown"
    }
  ],
  "properties_with_hotels": [
    {
      "name": "Mayfair",
      "owner": "player2",
      "group": "dark_blue"
    }
  ]
}
```

## Utilisation par l'IA

### 1. Évaluer les loyers potentiels

L'IA peut utiliser `current_rent` pour connaître le loyer exact qu'un joueur devrait payer sur une propriété :

```python
# Dans ai_service.py
property = context["global"]["properties"][position]
if property["owner"] and property["owner"] != current_player:
    rent_to_pay = property["current_rent"]
```

### 2. Décider de construire

L'IA peut vérifier s'il est rentable de construire :

```python
# Vérifier si on peut construire
if property["houses"] < 4:  # Peut construire une maison
    cost = property["house_price"]
    rent_increase = property["rent"][property["houses"] + 1] - property["current_rent"]
elif property["houses"] == 4:  # Peut construire un hôtel
    # Passer de 4 maisons à 1 hôtel
```

### 3. Évaluer les dangers

L'IA peut identifier les propriétés dangereuses :

```python
# Propriétés avec hôtels = danger maximum
dangerous_properties = [
    p for p in context["global"]["properties"] 
    if p["has_hotel"] and p["owner"] != current_player
]
```

### 4. Stratégies de monopole

L'IA peut prioriser la construction sur des groupes complets :

```python
# Vérifier si on a un monopole sur un groupe de couleur
my_properties = [p for p in properties if p["owner"] == current_player]
color_groups = {}
for prop in my_properties:
    color = prop["group"]
    if color not in color_groups:
        color_groups[color] = []
    color_groups[color].append(prop)

# Si on a toutes les propriétés d'une couleur, construire
```

## Test et vérification

Pour tester que les données sont correctement récupérées :

```bash
# Test simple des fonctions de lecture
python test_simple_house.py

# Test complet avec visualisation
python test_house_reading.py

# Test du contexte avec les maisons
python test_context_houses.py
```

## Notes importantes

1. **Valeurs des maisons** :
   - 0 = Aucune construction
   - 1-4 = Nombre de maisons
   - 5 = Un hôtel

2. **Loyers** :
   - L'array `rent` contient tous les loyers possibles : [base, 1 maison, 2 maisons, 3 maisons, 4 maisons, hôtel]
   - `current_rent` est calculé automatiquement selon le nombre de constructions

3. **Mise à jour** :
   - Les données sont mises à jour automatiquement à chaque tour
   - L'IA n'a pas besoin de faire d'appel supplémentaire

4. **Gestion des erreurs** :
   - Si la lecture échoue, `houses` sera à 0 par défaut
   - L'IA doit toujours vérifier que les données existent avant de les utiliser