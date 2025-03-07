/**
 * Module de configuration
 * Gère le chargement et la sauvegarde de la configuration
 */

import ui from './ui.js';

// Configuration par défaut
const DEFAULT_CONFIG = {
    dolphinPath: "C:\\Users\\ayari\\Downloads\\dolphin-2412-x64\\Dolphin-x64\\Dolphin.exe",
    isoPath: "C:\\Users\\ayari\\Downloads\\Monopoly Collection (Europe) (En,Fr)\\Monopoly Collection (Europe) (En,Fr).rvz",
    refreshInterval: 2000
};

// État de la configuration
let config = { ...DEFAULT_CONFIG };

/**
 * Charge la configuration depuis l'API
 */
async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        config = { ...DEFAULT_CONFIG, ...data };
        
        // Mettre à jour les champs de configuration dans l'interface
        updateConfigFields();
        
        ui.showNotification('Configuration loaded', 'success');
        return config;
    } catch (error) {
        console.error('Error loading config:', error);
        ui.showNotification('Error loading configuration', 'error');
        return null;
    }
}

/**
 * Met à jour les champs de configuration dans l'interface
 */
function updateConfigFields() {
    const dolphinPathInput = document.getElementById('dolphin-path');
    const isoPathInput = document.getElementById('iso-path');
    const refreshIntervalInput = document.getElementById('refresh-interval');
    
    if (dolphinPathInput) {
        dolphinPathInput.value = config.dolphinPath || DEFAULT_CONFIG.dolphinPath;
    }
    
    if (isoPathInput) {
        isoPathInput.value = config.isoPath || DEFAULT_CONFIG.isoPath;
    }
    
    if (refreshIntervalInput) {
        refreshIntervalInput.value = (config.refreshInterval || DEFAULT_CONFIG.refreshInterval) / 1000;
    }
}

/**
 * Sauvegarde la configuration via l'API
 */
async function saveConfig(newConfig) {
    try {
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(newConfig)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        config = { ...config, ...newConfig };
        ui.showNotification('Configuration saved', 'success');
        return true;
    } catch (error) {
        console.error('Error saving config:', error);
        ui.showNotification('Error saving configuration', 'error');
        return false;
    }
}

/**
 * Obtient une valeur de configuration
 */
function getConfig(key) {
    return config[key] || DEFAULT_CONFIG[key];
}

/**
 * Obtient toute la configuration
 */
function getAllConfig() {
    return { ...config };
}

export default {
    loadConfig,
    saveConfig,
    getConfig,
    getAllConfig,
    updateConfigFields
}; 