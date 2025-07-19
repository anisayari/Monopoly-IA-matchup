/**
 * Module d'administration
 * Gère le panneau d'administration et le contrôle des systèmes
 */

import ui from './ui.js';

// État des systèmes
let systemStatus = {
    dolphin: false,
    omniparser: false,
    ai: false,
    ram: true // Le RAM listener est toujours actif avec le jeu
};

// Processus en cours
let processes = {
    ai: null,
    calibration: null
};

/**
 * Initialise le module admin
 */
function init() {
    setupEventListeners();
    updateAllStatuses();
    
    // Vérifier l'état des systèmes toutes les 5 secondes
    setInterval(updateAllStatuses, 5000);
}

/**
 * Configure les écouteurs d'événements
 */
function setupEventListeners() {
    // Bouton Admin
    const adminButton = document.getElementById('admin-button');
    if (adminButton) {
        adminButton.addEventListener('click', showAdminModal);
    }
    
    // Fermer la modal
    const closeButton = document.getElementById('close-admin-modal');
    if (closeButton) {
        closeButton.addEventListener('click', hideAdminModal);
    }
    
    // Clic en dehors de la modal
    const adminModal = document.getElementById('admin-modal');
    if (adminModal) {
        adminModal.addEventListener('click', (e) => {
            if (e.target === adminModal) {
                hideAdminModal();
            }
        });
    }
    
    // Boutons de contrôle
    document.getElementById('dolphin-toggle')?.addEventListener('click', toggleDolphin);
    document.getElementById('omniparser-toggle')?.addEventListener('click', toggleOmniParser);
    document.getElementById('ai-toggle')?.addEventListener('click', toggleAI);
    document.getElementById('calibration-start')?.addEventListener('click', startCalibration);
}

/**
 * Affiche la modal d'administration
 */
function showAdminModal() {
    const modal = document.getElementById('admin-modal');
    if (modal) {
        modal.classList.remove('hidden');
        updateAllStatuses();
    }
}

/**
 * Cache la modal d'administration
 */
function hideAdminModal() {
    const modal = document.getElementById('admin-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

/**
 * Met à jour l'état de tous les systèmes
 */
async function updateAllStatuses() {
    // Vérifier l'état de Dolphin
    try {
        const response = await fetch('/api/dolphin/status');
        const data = await response.json();
        systemStatus.dolphin = data.running;
        systemStatus.ram = data.game_initialized;
    } catch (error) {
        systemStatus.dolphin = false;
        systemStatus.ram = false;
    }
    
    // Vérifier l'état d'OmniParser
    try {
        const response = await fetch('/api/omniparser/status');
        const data = await response.json();
        systemStatus.omniparser = data.running;
    } catch (error) {
        systemStatus.omniparser = false;
    }
    
    // Vérifier l'état des AI Actions
    try {
        const response = await fetch('/api/ai/status');
        const data = await response.json();
        systemStatus.ai = data.running;
    } catch (error) {
        systemStatus.ai = false;
    }
    
    // Vérifier l'état de la calibration
    try {
        const response = await fetch('/api/calibration/status');
        const data = await response.json();
        systemStatus.calibration = data.valid;
        
        // Stocker les infos pour l'affichage
        systemStatus.calibrationInfo = data;
    } catch (error) {
        systemStatus.calibration = false;
        systemStatus.calibrationInfo = null;
    }
    
    updateUIStatuses();
}

/**
 * Met à jour l'interface avec les états actuels
 */
function updateUIStatuses() {
    // Indicateurs dans la navbar
    updateIndicator('dolphin-status-indicator', systemStatus.dolphin);
    updateIndicator('omniparser-status-indicator', systemStatus.omniparser);
    updateIndicator('ai-status-indicator', systemStatus.ai);
    updateIndicator('ram-status-indicator', systemStatus.ram);
    updateIndicator('calibration-status-indicator', systemStatus.calibration);
    
    // États dans le panneau admin
    updateAdminStatus('dolphin-admin-status', systemStatus.dolphin);
    updateAdminStatus('omniparser-admin-status', systemStatus.omniparser);
    updateAdminStatus('ai-admin-status', systemStatus.ai);
    updateAdminStatus('ram-admin-status', systemStatus.ram);
    
    // Mettre à jour l'affichage de calibration
    updateCalibrationDisplay();
    
    // Boutons
    updateToggleButton('dolphin-toggle', systemStatus.dolphin, 'Dolphin');
    updateToggleButton('omniparser-toggle', systemStatus.omniparser, 'OmniParser');
    updateToggleButton('ai-toggle', systemStatus.ai, 'AI Actions');
}

/**
 * Met à jour un indicateur d'état
 */
function updateIndicator(id, isRunning) {
    const indicator = document.getElementById(id);
    if (indicator) {
        indicator.className = `inline-block w-2 h-2 rounded-full ${isRunning ? 'bg-green-500' : 'bg-red-500'}`;
    }
}

/**
 * Met à jour un texte d'état dans le panneau admin
 */
function updateAdminStatus(id, isRunning) {
    const status = document.getElementById(id);
    if (status) {
        status.textContent = isRunning ? 'Actif' : 'Arrêté';
        status.className = `text-sm font-medium ${isRunning ? 'text-green-400' : 'text-red-400'}`;
    }
}

/**
 * Met à jour un bouton toggle
 */
function updateToggleButton(id, isRunning, systemName) {
    const button = document.getElementById(id);
    if (button) {
        button.innerHTML = isRunning 
            ? `<i class="fas fa-stop mr-2"></i>Arrêter ${systemName}`
            : `<i class="fas fa-play mr-2"></i>Démarrer ${systemName}`;
        button.className = isRunning
            ? 'w-full bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded text-sm'
            : 'w-full bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm';
    }
}

/**
 * Toggle Dolphin
 */
async function toggleDolphin() {
    try {
        if (systemStatus.dolphin) {
            const response = await fetch('/api/dolphin', { method: 'DELETE' });
            if (response.ok) {
                ui.showNotification('Dolphin arrêté', 'success');
            }
        } else {
            const response = await fetch('/api/dolphin', { method: 'POST' });
            if (response.ok) {
                ui.showNotification('Dolphin démarré', 'success');
            }
        }
        setTimeout(updateAllStatuses, 1000);
    } catch (error) {
        ui.showNotification('Erreur lors du contrôle de Dolphin', 'error');
    }
}

/**
 * Toggle OmniParser
 */
async function toggleOmniParser() {
    try {
        if (systemStatus.omniparser) {
            const response = await fetch('/api/omniparser', { method: 'DELETE' });
            if (response.ok) {
                ui.showNotification('OmniParser arrêté', 'success');
            }
        } else {
            const response = await fetch('/api/omniparser', { method: 'POST' });
            if (response.ok) {
                ui.showNotification('OmniParser démarré', 'success');
            }
        }
        setTimeout(updateAllStatuses, 1000);
    } catch (error) {
        ui.showNotification('Erreur lors du contrôle d\'OmniParser', 'error');
    }
}

/**
 * Toggle AI Actions
 */
async function toggleAI() {
    try {
        const scriptSelect = document.getElementById('ai-script-select');
        const script = scriptSelect?.value || 'test_search_popup.py';
        
        if (systemStatus.ai) {
            const response = await fetch('/api/ai', { method: 'DELETE' });
            if (response.ok) {
                ui.showNotification('AI Actions arrêté', 'success');
            }
        } else {
            const response = await fetch('/api/ai', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ script })
            });
            if (response.ok) {
                ui.showNotification('AI Actions démarré', 'success');
            }
        }
        setTimeout(updateAllStatuses, 1000);
    } catch (error) {
        ui.showNotification('Erreur lors du contrôle des AI Actions', 'error');
    }
}

/**
 * Met à jour l'affichage de calibration dans le panneau admin
 */
function updateCalibrationDisplay() {
    const badge = document.getElementById('calibration-status-badge');
    const info = document.getElementById('calibration-info');
    
    if (badge) {
        if (systemStatus.calibration) {
            badge.textContent = 'Configurée';
            badge.className = 'ml-2 px-2 py-1 text-xs rounded-full bg-green-600 text-white';
        } else {
            badge.textContent = 'Non configurée';
            badge.className = 'ml-2 px-2 py-1 text-xs rounded-full bg-red-600 text-white';
        }
    }
    
    if (info) {
        if (systemStatus.calibration && systemStatus.calibrationInfo?.calibration_info) {
            const cal = systemStatus.calibrationInfo.calibration_info;
            info.innerHTML = `
                <div>Dernière calibration: ${cal.timestamp || 'Inconnue'}</div>
                <div>Fenêtre: ${(cal.window_title || 'Inconnue').substring(0, 50)}${cal.window_title?.length > 50 ? '...' : ''}</div>
                <div>Points: ${cal.points ? cal.points.length : 0}/4</div>
            `;
        } else {
            const message = systemStatus.calibrationInfo?.message || 'Calibration requise';
            info.innerHTML = `<div class="text-yellow-400">${message}</div>`;
        }
    }
}

/**
 * Lance la calibration
 */
async function startCalibration() {
    try {
        const response = await fetch('/api/calibration', { method: 'POST' });
        if (response.ok) {
            ui.showNotification('Calibration lancée dans un nouveau terminal', 'success');
            
            // Désactiver le bouton pendant la calibration
            const button = document.getElementById('calibration-start');
            if (button) {
                button.disabled = true;
                button.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Calibration en cours...';
                button.className = 'bg-gray-600 text-white px-4 py-2 rounded text-sm cursor-not-allowed';
                
                // Réactiver après 30 secondes et mettre à jour le statut
                setTimeout(() => {
                    button.disabled = false;
                    button.innerHTML = '<i class="fas fa-play mr-2"></i>Lancer la calibration';
                    button.className = 'bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded text-sm';
                    updateAllStatuses(); // Mettre à jour le statut
                }, 30000);
            }
        } else {
            const error = await response.json();
            ui.showNotification(error.error || 'Erreur lors du lancement de la calibration', 'error');
        }
    } catch (error) {
        ui.showNotification('Erreur lors du lancement de la calibration', 'error');
        console.error('Calibration error:', error);
    }
}

// Exporter les fonctions
export default {
    init,
    updateAllStatuses,
    showAdminModal,
    hideAdminModal
};