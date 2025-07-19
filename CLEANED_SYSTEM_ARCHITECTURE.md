# Monopoly IA - Architecture Système Nettoyée

## Vue d'ensemble
Après le nettoyage des fichiers obsolètes, le système Monopoly IA est maintenant simplifié et centralisé autour d'un seul point d'entrée.

## Structure des fichiers batch

### Fichiers conservés:
- **START_MONOPOLY.bat** - Script principal qui lance tout le système
- **kill_port_8000.bat** - Utilitaire pour libérer le port 8000
- **cleanup_dolphin.bat** - Utilitaire pour arrêter les processus Dolphin
- **toggle_autolaunch.bat** - Configure le lancement automatique de Dolphin
- **cleanup_obsolete_files.bat** - Script de nettoyage des fichiers obsolètes

### Fichiers supprimés:
- Tous les scripts launch_*.bat
- Tous les scripts start_*.bat (sauf START_MONOPOLY.bat)
- Scripts Docker GPU dans omniparserserver/
- stop_port_8000.bat (redondant avec kill_port_8000.bat)

## Architecture des services

### 1. Service Flask (Port 5000)
- **Fichier**: app.py
- **Rôle**: Interface web principale, API REST, coordination des services
- **Routes principales**:
  - `/` - Dashboard principal
  - `/admin` - Panneau d'administration
  - `/monitoring` - Interface de monitoring
  - `/api/*` - Endpoints API

### 2. Service OmniParser (Port 8000)
- **Fichier**: omniparser_lite.py ou omniparser_server_native.py
- **Rôle**: Détection d'éléments UI via vision par ordinateur
- **Utilise**: Modèle YOLO pour la détection

### 3. Monitor Centralisé
- **Fichier**: monitor_centralized.py
- **Rôle**: Surveillance de la mémoire Dolphin pour détecter les popups
- **Communication**: Via API Flask sur `/api/popups/*`

### 4. Service AI Actions
- **Fichier**: ai_actions_server.py
- **Rôle**: Gestion du contexte de jeu et des décisions IA
- **Intégration**: OpenAI API avec gpt-4.1-mini

### 5. Service AI Chat
- **Fichier**: ai_chat_server.py
- **Rôle**: Affichage des pensées et discussions des IA
- **Interface**: Terminal dédié avec codes couleur par joueur

## Flux de démarrage

1. **START_MONOPOLY.bat** vérifie:
   - Nettoyage des fichiers obsolètes
   - Libération du port 8000
   - Calibration valide
   - Mode de terminal (intégré/classique/minimal)

2. **Mode intégré** (Windows Terminal):
   ```
   +------------------+------------------+
   |      Flask       |    OmniParser    |
   |      (5000)      |      (8000)      |
   +------------------+------------------+
   | Monitor (Popups) | AI Chat/Thoughts |
   +------------------+------------------+
   |         AI Actions (Context)        |
   +-------------------------------------+
   ```

3. **Mode classique**: Fenêtres séparées pour chaque service

4. **Auto-launch**: Si config/autolaunch.txt existe, lance Dolphin automatiquement

## Configuration

### Fichiers de configuration:
- `/config/game_settings.json` - Paramètres du jeu et des joueurs
- `/config/autolaunch.txt` - Active le lancement automatique
- `/monitor_config.json` - Configuration du monitoring
- `/calibration/calibration_data.json` - Données de calibration Wiimote

### Variables d'environnement:
- `OPENAI_API_KEY` - Clé API OpenAI (requise)

## Communication inter-services

1. **Event-driven**: Architecture basée sur les événements via EventBus
2. **API REST**: Communication centralisée via Flask
3. **WebSockets**: Non utilisé actuellement (possible amélioration future)

## Points d'amélioration identifiés

1. **Logging centralisé**: Implémenter un système de logs unifié
2. **Gestion d'erreurs**: Améliorer la récupération après erreurs
3. **Performance**: Optimiser la détection de popups
4. **UI**: Améliorer l'interface web avec plus de feedback temps réel

## Commandes utiles

### Démarrage du système:
```batch
START_MONOPOLY.bat
```

### Nettoyage:
```batch
cleanup_obsolete_files.bat  # Supprimer les fichiers obsolètes
cleanup_dolphin.bat         # Arrêter Dolphin
kill_port_8000.bat         # Libérer le port 8000
```

### Configuration:
```batch
toggle_autolaunch.bat      # Activer/désactiver le lancement auto
```

## Maintenance

- Toujours utiliser START_MONOPOLY.bat pour lancer le système
- Vérifier régulièrement la calibration
- Surveiller les logs dans le panneau d'administration
- Utiliser le monitoring pour debug les popups non détectés