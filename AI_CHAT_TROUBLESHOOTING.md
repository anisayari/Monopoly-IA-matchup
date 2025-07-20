# Guide de dépannage AI Chat Monitor

## Le problème
Le moniteur AI Chat ne reçoit pas de messages pendant le jeu.

## Solutions implémentées

### 1. Ajout de logs de debug
Le service AI affiche maintenant des logs pour chaque étape:
- `[AI Service] Decision requested for {player}` - Quand une décision est demandée
- `[AI Service] Popup: {text}` - Le texte du popup
- `[AI Service] Options: {options}` - Les options disponibles
- `[AI Chat] Sent {type} for {player}` - Quand un message est envoyé au chat
- `[AI Chat] Monitor not running on port 8003` - Si le serveur n'est pas accessible

### 2. Scripts de test

#### test_ai_chat_simple.py
Test basique du serveur AI Chat:
```bash
python test_ai_chat_simple.py
```

#### test_ai_service_direct.py
Test direct du service AI:
```bash
python test_ai_service_direct.py
```

## Étapes de vérification

### 1. Vérifier que le serveur AI Chat est lancé
```bash
# Lancer le serveur
START_AI_CHAT.bat

# Dans une autre fenêtre, tester la connexion
python test_ai_chat_simple.py
```

### 2. Vérifier que le service AI est appelé
Pendant le jeu, regardez la console principale pour voir:
- Les logs `[AI Service]` apparaissent quand une décision est demandée
- Les logs `[AI Chat]` confirment l'envoi au serveur

### 3. Vérifier les ports
Le serveur AI Chat doit être sur le port 8003:
```bash
netstat -an | findstr 8003
```

### 4. Tester l'intégration complète
1. Lancer START_AI_CHAT.bat
2. Lancer START_MONOPOLY.bat
3. Observer les deux consoles pendant le jeu

## Problèmes courants

### "Monitor not running on port 8003"
- Le serveur AI Chat n'est pas lancé
- Solution: Lancer START_AI_CHAT.bat avant le jeu

### Pas de logs "[AI Service]"
- Le service AI n'est pas appelé par le jeu
- Vérifier que l'IA est activée dans game_settings.json

### Messages envoyés mais pas affichés
- Problème de format des données
- Vérifier les logs d'erreur dans la console AI Chat

## Architecture
```
Game → Decision Service → AI Service → AI Chat Monitor (8003)
                                    └→ AI Actions Monitor (8004)
```

Le service AI envoie:
- **Thoughts** (analysis, decision) au port 8003
- **Chat** messages au port 8003  
- **Actions** au port 8004
- **Context** au port 8004