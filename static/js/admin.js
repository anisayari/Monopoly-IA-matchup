/**
 * Admin Panel JavaScript
 */

// État de l'application
let state = {
    systems: {
        dolphin: false,
        omniparser: false,
        ai: false,
        ram: true
    },
    logs: [],
    terminal: [],
    autoScroll: true,
    logFilter: 'all',
    startTime: Date.now()
};

// Initialisation
document.addEventListener('DOMContentLoaded', () => {
    console.log('Initializing Admin Panel...');
    
    // Initialiser les onglets
    initTabs();
    
    // Initialiser les contrôles des systèmes
    initSystemControls();
    
    // Initialiser la configuration
    initConfig();
    
    // Initialiser les logs
    initLogs();
    
    // Initialiser le terminal
    initTerminal();
    
    // Démarrer la mise à jour des statuts
    updateAllStatuses();
    setInterval(updateAllStatuses, 5000);
    
    // Démarrer la mise à jour du monitoring
    updateMonitoring();
    setInterval(updateMonitoring, 1000);
    
    console.log('Admin Panel initialized');
});

/**
 * Initialise le système d'onglets
 */
function initTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetTab = button.dataset.tab;
            
            // Mettre à jour les boutons
            tabButtons.forEach(btn => {
                btn.classList.remove('active');
            });
            button.classList.add('active');
            
            // Mettre à jour les contenus
            tabContents.forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(`${targetTab}-tab`).classList.add('active');
        });
    });
}

/**
 * Initialise les contrôles des systèmes
 */
function initSystemControls() {
    // Dolphin
    document.getElementById('dolphin-toggle')?.addEventListener('click', toggleDolphin);
    
    // OmniParser
    document.getElementById('omniparser-toggle')?.addEventListener('click', toggleOmniParser);
    
    // AI Actions
    document.getElementById('ai-toggle')?.addEventListener('click', toggleAI);
    
    // Calibration
    document.getElementById('calibration-start')?.addEventListener('click', startCalibration);
    document.getElementById('view-calibration')?.addEventListener('click', viewCalibration);
}

/**
 * Initialise la configuration
 */
async function initConfig() {
    try {
        const response = await fetch('/api/config');
        const config = await response.json();
        
        document.getElementById('dolphin-path').value = config.dolphinPath || '';
        document.getElementById('iso-path').value = config.isoPath || '';
        document.getElementById('save-path').value = config.savePath || '';
        document.getElementById('refresh-interval').value = (config.refreshInterval || 2000) / 1000;
    } catch (error) {
        console.error('Error loading config:', error);
    }
    
    // Bouton de sauvegarde
    document.getElementById('save-config-button')?.addEventListener('click', async () => {
        const configData = {
            dolphin_path: document.getElementById('dolphin-path').value,
            monopoly_iso_path: document.getElementById('iso-path').value,
            save_file_path: document.getElementById('save-path').value,
            refresh_interval: parseInt(document.getElementById('refresh-interval').value) * 1000
        };
        
        try {
            const response = await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(configData)
            });
            
            if (response.ok) {
                addLog('Configuration sauvegardée avec succès', 'success');
            } else {
                addLog('Erreur lors de la sauvegarde de la configuration', 'error');
            }
        } catch (error) {
            addLog('Erreur lors de la sauvegarde de la configuration: ' + error.message, 'error');
        }
    });
}

/**
 * Initialise le système de logs
 */
function initLogs() {
    // Filtre de logs
    document.getElementById('log-filter')?.addEventListener('change', (e) => {
        state.logFilter = e.target.value;
        renderLogs();
    });
    
    // Vider les logs
    document.getElementById('clear-logs')?.addEventListener('click', () => {
        state.logs = [];
        renderLogs();
        addLog('Logs vidés', 'info');
    });
    
    // Exporter les logs
    document.getElementById('export-logs')?.addEventListener('click', () => {
        const logsText = state.logs.map(log => 
            `[${log.timestamp}] [${log.type.toUpperCase()}] ${log.message}`
        ).join('\n');
        
        const blob = new Blob([logsText], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `monopoly-logs-${new Date().toISOString()}.txt`;
        a.click();
        URL.revokeObjectURL(url);
        
        addLog('Logs exportés', 'success');
    });
    
    // Charger les logs existants via WebSocket ou polling
    loadLogs();
}

/**
 * Initialise le terminal
 */
function initTerminal() {
    // Vider le terminal
    document.getElementById('clear-terminal')?.addEventListener('click', () => {
        state.terminal = [];
        renderTerminal();
    });
    
    // Toggle auto-scroll
    const autoScrollBtn = document.getElementById('auto-scroll-toggle');
    autoScrollBtn?.addEventListener('click', () => {
        state.autoScroll = !state.autoScroll;
        autoScrollBtn.innerHTML = `<i class="fas fa-arrow-down mr-1"></i>Auto-scroll: ${state.autoScroll ? 'ON' : 'OFF'}`;
    });
    
    // Charger le terminal
    loadTerminal();
    setInterval(loadTerminal, 1000);
}

/**
 * Ajoute un log
 */
function addLog(message, type = 'info') {
    const log = {
        timestamp: new Date().toLocaleTimeString(),
        message,
        type
    };
    
    state.logs.push(log);
    if (state.logs.length > 1000) {
        state.logs.shift();
    }
    
    renderLogs();
}

/**
 * Affiche les logs
 */
function renderLogs() {
    const container = document.getElementById('logs-container');
    const filteredLogs = state.logFilter === 'all' 
        ? state.logs 
        : state.logs.filter(log => log.type === state.logFilter);
    
    container.innerHTML = filteredLogs.map(log => `
        <div class="log-entry log-${log.type}">
            <span class="text-zinc-500">[${log.timestamp}]</span>
            <span class="font-semibold">[${log.type.toUpperCase()}]</span>
            <span>${log.message}</span>
        </div>
    `).join('');
    
    if (state.autoScroll) {
        container.scrollTop = container.scrollHeight;
    }
}

/**
 * Affiche le terminal
 */
function renderTerminal() {
    const container = document.getElementById('terminal-output');
    container.innerHTML = state.terminal.join('<br>');
    
    if (state.autoScroll) {
        container.scrollTop = container.scrollHeight;
    }
}

/**
 * Charge les logs depuis l'API
 */
async function loadLogs() {
    try {
        const response = await fetch('/api/logs');
        const logs = await response.json();
        
        logs.forEach(log => {
            if (!state.logs.some(l => l.timestamp === log.timestamp && l.message === log.message)) {
                state.logs.push(log);
            }
        });
        
        renderLogs();
    } catch (error) {
        console.error('Error loading logs:', error);
    }
}

/**
 * Charge le terminal depuis l'API
 */
async function loadTerminal() {
    try {
        const response = await fetch('/api/terminal');
        const terminal = await response.json();
        
        state.terminal = terminal;
        renderTerminal();
    } catch (error) {
        console.error('Error loading terminal:', error);
    }
}

/**
 * Met à jour tous les statuts
 */
async function updateAllStatuses() {
    // Dolphin
    try {
        const response = await fetch('/api/dolphin/status');
        const data = await response.json();
        state.systems.dolphin = data.running;
        state.systems.ram = data.game_initialized;
    } catch (error) {
        state.systems.dolphin = false;
        state.systems.ram = false;
    }
    
    // OmniParser
    try {
        const response = await fetch('/api/omniparser/status');
        const data = await response.json();
        state.systems.omniparser = data.running;
    } catch (error) {
        state.systems.omniparser = false;
    }
    
    // AI Actions
    try {
        const response = await fetch('/api/ai/status');
        const data = await response.json();
        state.systems.ai = data.running;
    } catch (error) {
        state.systems.ai = false;
    }
    
    updateUIStatuses();
}

/**
 * Met à jour l'interface avec les statuts
 */
function updateUIStatuses() {
    // Indicateurs
    updateIndicator('dolphin-status-indicator', state.systems.dolphin);
    updateIndicator('omniparser-status-indicator', state.systems.omniparser);
    updateIndicator('ai-status-indicator', state.systems.ai);
    updateIndicator('ram-status-indicator', state.systems.ram);
    
    // Textes d'état
    updateAdminStatus('dolphin-admin-status', state.systems.dolphin);
    updateAdminStatus('omniparser-admin-status', state.systems.omniparser);
    updateAdminStatus('ai-admin-status', state.systems.ai);
    updateAdminStatus('ram-admin-status', state.systems.ram);
    
    // Boutons
    updateToggleButton('dolphin-toggle', state.systems.dolphin, 'Dolphin');
    updateToggleButton('omniparser-toggle', state.systems.omniparser, 'OmniParser');
    updateToggleButton('ai-toggle', state.systems.ai, 'AI Actions');
}

/**
 * Met à jour un indicateur
 */
function updateIndicator(id, isRunning) {
    const indicator = document.getElementById(id);
    if (indicator) {
        indicator.className = `inline-block w-2 h-2 rounded-full ${isRunning ? 'bg-green-500' : 'bg-red-500'}`;
    }
}

/**
 * Met à jour un statut admin
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
            ? 'w-full bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded text-sm mt-3'
            : 'w-full bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm mt-3';
    }
}

/**
 * Toggle Dolphin
 */
async function toggleDolphin() {
    try {
        const method = state.systems.dolphin ? 'DELETE' : 'POST';
        const response = await fetch('/api/dolphin', { method });
        
        if (response.ok) {
            addLog(`Dolphin ${state.systems.dolphin ? 'arrêté' : 'démarré'}`, 'success');
            setTimeout(updateAllStatuses, 1000);
        } else {
            addLog(`Erreur lors du contrôle de Dolphin`, 'error');
        }
    } catch (error) {
        addLog(`Erreur lors du contrôle de Dolphin: ${error.message}`, 'error');
    }
}

/**
 * Toggle OmniParser
 */
async function toggleOmniParser() {
    try {
        const method = state.systems.omniparser ? 'DELETE' : 'POST';
        const response = await fetch('/api/omniparser', { method });
        
        if (response.ok) {
            addLog(`OmniParser ${state.systems.omniparser ? 'arrêté' : 'démarré'}`, 'success');
            setTimeout(updateAllStatuses, 1000);
        } else {
            addLog(`Erreur lors du contrôle d'OmniParser`, 'error');
        }
    } catch (error) {
        addLog(`Erreur lors du contrôle d'OmniParser: ${error.message}`, 'error');
    }
}

/**
 * Toggle AI Actions
 */
async function toggleAI() {
    try {
        const script = document.getElementById('ai-script-select')?.value || 'test_search_popup.py';
        
        if (state.systems.ai) {
            const response = await fetch('/api/ai', { method: 'DELETE' });
            if (response.ok) {
                addLog('AI Actions arrêté', 'success');
            }
        } else {
            const response = await fetch('/api/ai', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ script })
            });
            if (response.ok) {
                addLog(`AI Actions démarré avec ${script}`, 'success');
            }
        }
        
        setTimeout(updateAllStatuses, 1000);
    } catch (error) {
        addLog(`Erreur lors du contrôle des AI Actions: ${error.message}`, 'error');
    }
}

/**
 * Lance la calibration
 */
async function startCalibration() {
    try {
        const response = await fetch('/api/calibration', { method: 'POST' });
        if (response.ok) {
            addLog('Calibration lancée', 'info');
            
            const button = document.getElementById('calibration-start');
            if (button) {
                button.disabled = true;
                button.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Calibration en cours...';
                
                setTimeout(() => {
                    button.disabled = false;
                    button.innerHTML = '<i class="fas fa-play mr-2"></i>Lancer la calibration';
                    addLog('Calibration terminée', 'success');
                }, 30000);
            }
        }
    } catch (error) {
        addLog(`Erreur lors du lancement de la calibration: ${error.message}`, 'error');
    }
}

/**
 * Affiche la calibration actuelle
 */
async function viewCalibration() {
    try {
        const response = await fetch('/api/calibration/current');
        const calibration = await response.json();
        
        addLog('Calibration actuelle chargée', 'info');
        console.log('Calibration:', calibration);
        
        // TODO: Afficher la calibration dans une modal ou un nouvel onglet
    } catch (error) {
        addLog(`Erreur lors du chargement de la calibration: ${error.message}`, 'error');
    }
}

/**
 * Met à jour le monitoring
 */
function updateMonitoring() {
    // Uptime
    const uptime = Date.now() - state.startTime;
    const hours = Math.floor(uptime / 3600000);
    const minutes = Math.floor((uptime % 3600000) / 60000);
    const seconds = Math.floor((uptime % 60000) / 1000);
    document.getElementById('uptime').textContent = 
        `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    
    // Process count
    let processCount = 0;
    if (state.systems.dolphin) processCount++;
    if (state.systems.omniparser) processCount++;
    if (state.systems.ai) processCount++;
    if (state.systems.ram) processCount++;
    document.getElementById('process-count').textContent = processCount;
    
    // TODO: Implémenter CPU et Memory usage réels
    document.getElementById('cpu-usage').textContent = '--';
    document.getElementById('memory-usage').textContent = '-- MB';
}