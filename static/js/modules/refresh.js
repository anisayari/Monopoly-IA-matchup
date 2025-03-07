/**
 * Module de rafraîchissement
 * Gère le rafraîchissement automatique des données
 */

import data from './data.js';
import ui from './ui.js';

let refreshInterval = null;
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
    },

    stopAutoRefresh() {
        if (refreshInterval) {
            clearInterval(refreshInterval);
            refreshInterval = null;
        }
    }
};

export default refresh; 