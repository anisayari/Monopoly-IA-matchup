/**
 * Module de rafraîchissement
 * Gère le rafraîchissement automatique des données
 */

import data from './data.js';
import ui from './ui.js';

let refreshInterval = null;
let statusCheckInterval = null;
const DEFAULT_INTERVAL = 1000; // 1 seconde

const refresh = {
    startAutoRefresh(interval = DEFAULT_INTERVAL) {
        if (refreshInterval) {
            clearInterval(refreshInterval);
        }

        refreshInterval = setInterval(async () => {
            // Mettre à jour le contexte du jeu
            const context = await data.getGameContext();
            if (context) {
                ui.updateGameInfo(context);
            }
            
            // Mettre à jour le terminal
            try {
                const response = await fetch('/api/terminal');
                if (response.ok) {
                    const terminalOutput = await response.json();
                    ui.updateTerminal(terminalOutput);
                }
            } catch (error) {
                console.error('Error updating terminal:', error);
            }
        }, interval);
        
        // Démarrer la vérification du statut après un délai pour laisser les systèmes démarrer
        setTimeout(() => {
            this.startStatusCheck();
        }, 5000);
    },

    stopAutoRefresh() {
        if (refreshInterval) {
            clearInterval(refreshInterval);
            refreshInterval = null;
        }
        if (statusCheckInterval) {
            clearInterval(statusCheckInterval);
            statusCheckInterval = null;
        }
    },
    
    startStatusCheck() {
        if (statusCheckInterval) {
            clearInterval(statusCheckInterval);
        }
        
        statusCheckInterval = setInterval(async () => {
            try {
                // Vérifier les statuts de tous les systèmes
                const [dolphinRes, omniparserRes, aiRes, monitorRes, calibrationRes] = await Promise.all([
                    fetch('/api/dolphin/status').catch(() => null),
                    fetch('/api/omniparser/status').catch(() => null),
                    fetch('/api/ai/status').catch(() => null),
                    fetch('/api/monitor/status').catch(() => null),
                    fetch('/api/calibration/status').catch(() => null)
                ]);
                
                // Mettre à jour les indicateurs
                if (dolphinRes) {
                    const dolphinStatus = await dolphinRes.json();
                    const dolphinIndicator = document.getElementById('dolphin-status-indicator');
                    if (dolphinIndicator) {
                        dolphinIndicator.className = `inline-block w-2 h-2 rounded-full ${dolphinStatus.running ? 'bg-green-500' : 'bg-red-500'}`;
                    }
                    
                    // Vérifier si Dolphin s'est fermé
                    const startButton = document.getElementById('start-button');
                    
                    if (!dolphinStatus.running && startButton && startButton.textContent && startButton.textContent.includes('Stop')) {
                        // Dolphin s'est fermé, réinitialiser l'interface
                        console.log('Dolphin s\'est fermé de manière inattendue');
                        ui.updateDolphinStatus(false);
                        ui.showNotification('Dolphin s\'est fermé', 'warning');
                    }
                }
                
                if (omniparserRes) {
                    const omniparserStatus = await omniparserRes.json();
                    const omniparserIndicator = document.getElementById('omniparser-status-indicator');
                    if (omniparserIndicator) {
                        omniparserIndicator.className = `inline-block w-2 h-2 rounded-full ${omniparserStatus.running ? 'bg-green-500' : 'bg-red-500'}`;
                    }
                }
                
                if (aiRes) {
                    const aiStatus = await aiRes.json();
                    const aiIndicator = document.getElementById('ai-status-indicator');
                    if (aiIndicator) {
                        aiIndicator.className = `inline-block w-2 h-2 rounded-full ${aiStatus.running ? 'bg-green-500' : 'bg-red-500'}`;
                    }
                }
                
                // Monitor status
                if (monitorRes) {
                    const monitorStatus = await monitorRes.json();
                    const monitorIndicator = document.getElementById('monitor-status-indicator');
                    if (monitorIndicator) {
                        monitorIndicator.className = `inline-block w-2 h-2 rounded-full ${monitorStatus.running ? 'bg-green-500' : 'bg-red-500'}`;
                    }
                }
                
                // Calibration status
                if (calibrationRes) {
                    const calibrationStatus = await calibrationRes.json();
                    const calibrationIndicator = document.getElementById('calibration-status-indicator');
                    if (calibrationIndicator) {
                        calibrationIndicator.className = `inline-block w-2 h-2 rounded-full ${calibrationStatus.valid ? 'bg-green-500' : 'bg-yellow-500'}`;
                        calibrationIndicator.title = calibrationStatus.message || 'Statut de calibration inconnu';
                    }
                }
                
            } catch (error) {
                console.error('Erreur lors de la vérification du statut:', error);
            }
        }, 3000); // Vérifier toutes les 3 secondes
    }
};

export default refresh; 