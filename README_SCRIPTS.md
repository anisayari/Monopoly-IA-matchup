# 📜 Scripts Guide - Monopoly IA

## 🚀 Script Principal

### `START_MONOPOLY.bat`
Le script principal pour démarrer tout le système. Il offre 3 modes :

1. **Mode Intégré** (Recommandé avec Windows Terminal)
   - Tout dans une seule fenêtre divisée en 4 panneaux
   - Layout 2x2 : Flask, OmniParser, Monitor, AI Actions
   - Navigation facile avec Alt+Flèches

2. **Mode Classique**
   - Fenêtres séparées pour chaque service
   - Plus traditionnel mais plus de fenêtres

3. **Mode Minimal**
   - Démarre seulement Flask
   - Les autres services peuvent être lancés depuis l'interface Admin

**Fonctionnalités :**
- ✅ Vérification automatique de la calibration
- ✅ Détection de Windows Terminal
- ✅ Options de démarrage flexibles
- ✅ Vérification de l'état du système

## 🛠️ Scripts Utilitaires

### `cleanup_dolphin.bat`
Nettoie les processus Dolphin et Memory Engine restants.

### `stop_port_8000.bat`
Arrête les processus utilisant le port 8000 (OmniParser).

### `start_omniparser_native.bat`
Lance OmniParser en mode natif (sans Docker).

### `check_dependencies.py`
Vérifie que toutes les dépendances Python sont installées.

### `check_calibration.py`
Vérifie si la calibration est valide.

## 🗑️ Scripts Supprimés (Obsolètes)

Les scripts suivants ont été supprimés car leurs fonctionnalités sont intégrées dans `START_MONOPOLY.bat` :
- `start_all_v2.bat`
- `start_monopoly_ia_v2.bat` 
- `start_monopoly_ia_v3.bat`
- `start_all_integrated.bat`
- `start_all_tmux.bat`
- `launch_ai_actions_terminal.bat`
- `launch_omniparser_terminal.bat`
- `start_omniparser_with_monitor.bat`

## 💡 Utilisation Recommandée

1. **Pour démarrer le système complet :**
   ```batch
   START_MONOPOLY.bat
   ```
   Choisissez le mode 1 (Intégré) si vous avez Windows Terminal.

2. **Pour nettoyer après utilisation :**
   ```batch
   cleanup_dolphin.bat
   ```

3. **En cas de problème avec OmniParser :**
   ```batch
   stop_port_8000.bat
   start_omniparser_native.bat
   ```

## 📝 Notes

- Le script principal gère automatiquement la calibration
- Redis est optionnel (pour la persistance des événements)
- Tous les services peuvent être contrôlés depuis l'interface Admin
- La calibration peut être refaite à tout moment depuis l'Admin