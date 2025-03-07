/**
 * Module Dolphin
 * Gère l'interaction avec l'émulateur Dolphin
 */

import ui from './ui.js';

// État de Dolphin
let state = {
    running: false,
    windowCreated: false
};

/**
 * Démarre l'émulateur Dolphin
 */
async function startDolphin(savePath) {
    try {
        // Afficher le loader
        ui.showLoader('Starting Dolphin and initializing game...');
        
        const response = await fetch('/api/dolphin', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action: 'start',
                save_file: savePath
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            state.running = true;
            ui.updateDolphinStatus(true);
            ui.showNotification('Dolphin started successfully', 'success');
            
            // Créer l'iframe pour afficher Dolphin si ce n'est pas déjà fait
            if (!state.windowCreated) {
                state.windowCreated = ui.createDolphinWindow();
            }
            
            // Mettre à jour le statut de connexion
            ui.updateConnectionStatus(true);
            
            // Cacher le loader
            ui.hideLoader();
            
            return true;
        } else {
            ui.hideLoader();
            ui.showNotification(`Error: ${result.error}`, 'error');
            return false;
        }
    } catch (error) {
        ui.hideLoader();
        console.error('Error starting Dolphin:', error);
        ui.showNotification('Error starting Dolphin', 'error');
        return false;
    }
}

/**
 * Arrête l'émulateur Dolphin
 */
async function stopDolphin() {
    try {
        const response = await fetch('/api/dolphin', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action: 'stop'
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            state.running = false;
            state.windowCreated = false;
            ui.updateDolphinStatus(false);
            ui.showNotification('Dolphin stopped successfully', 'success');
            
            // Mettre à jour le statut de connexion
            ui.updateConnectionStatus(false);
            
            return true;
        } else {
            ui.showNotification(`Error: ${result.error}`, 'error');
            return false;
        }
    } catch (error) {
        console.error('Error stopping Dolphin:', error);
        ui.showNotification('Error stopping Dolphin', 'error');
        return false;
    }
}

/**
 * Redémarre le jeu Monopoly
 */
async function restartGame(restartDolphin = false) {
    try {
        const response = await fetch('/api/restart', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                restart_dolphin: restartDolphin
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            ui.showNotification('Game restarted successfully', 'success');
            
            if (restartDolphin) {
                state.running = true;
                ui.updateDolphinStatus(true);
                ui.updateConnectionStatus(true);
                
                // Créer l'iframe pour afficher Dolphin si ce n'est pas déjà fait
                if (!state.windowCreated) {
                    state.windowCreated = ui.createDolphinWindow();
                }
            }
            
            return true;
        } else {
            ui.showNotification(`Error: ${result.error}`, 'error');
            return false;
        }
    } catch (error) {
        console.error('Error restarting game:', error);
        ui.showNotification('Error restarting game', 'error');
        return false;
    }
}

/**
 * Vérifie si Dolphin est en cours d'exécution
 */
function isRunning() {
    return state.running;
}

export default {
    startDolphin,
    stopDolphin,
    restartGame,
    isRunning
}; 