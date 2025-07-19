/**
 * Monitoring centralisé en temps réel
 */

class MonopolyMonitoring {
    constructor() {
        this.socket = null;
        this.activePopups = new Map();
        this.eventHistory = [];
        this.stats = {
            total: 0,
            ai_decisions: 0,
            avg_time: 0,
            success_rate: 100
        };
        
        this.init();
    }
    
    init() {
        // Initialiser Socket.IO
        this.socket = io({
            transports: ['websocket', 'polling']
        });
        
        // Setup event listeners
        this.setupSocketEvents();
        this.setupUIEvents();
        
        // Vérifier les statuts
        this.checkSystemStatus();
        setInterval(() => this.checkSystemStatus(), 5000);
    }
    
    setupSocketEvents() {
        // Connexion
        this.socket.on('connect', () => {
            console.log('✅ Connecté au serveur');
            this.updateStatus('eventbus-status', true);
        });
        
        this.socket.on('disconnect', () => {
            console.log('❌ Déconnecté du serveur');
            this.updateStatus('eventbus-status', false);
        });
        
        // Events métier
        this.socket.on('popup.detected', (event) => {
            this.onPopupDetected(event);
        });
        
        this.socket.on('popup.analyzed', (event) => {
            this.onPopupAnalyzed(event);
        });
        
        this.socket.on('ai.decision_made', (event) => {
            this.onDecisionMade(event);
        });
        
        this.socket.on('popup.executed', (event) => {
            this.onPopupExecuted(event);
        });
        
        this.socket.on('service.error', (event) => {
            this.onServiceError(event);
        });
        
        // Events RAM
        this.socket.on('ram.memory_updated', (event) => {
            this.onMemoryUpdated(event);
        });
        
        this.socket.on('ram.game_state_changed', (event) => {
            this.onGameStateChanged(event);
        });
    }
    
    setupUIEvents() {
        // Boutons de contrôle
        document.getElementById('start-monitor').addEventListener('click', () => {
            this.startMonitor();
        });
        
        document.getElementById('stop-monitor').addEventListener('click', () => {
            this.stopMonitor();
        });
        
        document.getElementById('clear-timeline').addEventListener('click', () => {
            this.clearTimeline();
        });
        
        document.getElementById('clear-terminal').addEventListener('click', () => {
            this.clearTerminal();
        });
        
        // Mode auto
        document.getElementById('auto-mode').addEventListener('change', (e) => {
            this.setAutoMode(e.target.checked);
        });
    }
    
    // Event Handlers
    onPopupDetected(event) {
        const data = event.data;
        const popupId = data.id;
        
        // Ajouter aux popups actifs
        this.activePopups.set(popupId, {
            ...data,
            status: 'detected',
            startTime: new Date()
        });
        
        // Log dans le terminal
        this.addTerminalLine('popup', `Popup détecté: ${data.title || 'Unknown'} [ID: ${popupId}]`);
        
        // Mettre à jour l'UI
        this.addPopupCard(popupId, data);
        this.addTimelineEvent('popup', `Nouveau popup détecté: "${data.text}"`, 'blue');
        
        // Stats
        this.stats.total++;
        this.updateStats();
        
        // Alerte sonore si activée
        if (document.getElementById('sound-alerts').checked) {
            this.playSound('popup');
        }
    }
    
    onPopupAnalyzed(event) {
        const data = event.data;
        const popup = this.activePopups.get(data.popup_id);
        
        if (popup) {
            popup.options = data.options;
            popup.text_content = data.text_content;
            popup.popup_type = data.popup_type;
            popup.status = 'analyzed';
            this.updatePopupCard(data.popup_id);
            
            // Log dans le terminal
            this.addTerminalLine('popup', `Analyse complète: Type=${data.popup_type}, Options=${data.options.length}`);
            data.options.forEach(opt => {
                this.addTerminalLine('info', `  - Option: ${opt.name} (${opt.type})`);
            });
            
            this.addTimelineEvent('analyze', `${data.options.length} options trouvées`, 'green');
        }
    }
    
    onDecisionMade(event) {
        const data = event.data;
        const popup = this.activePopups.get(data.popup_id);
        
        if (popup) {
            popup.decision = data.decision;
            popup.reason = data.reason;
            popup.status = 'decided';
            this.updatePopupCard(data.popup_id);
            
            // Log dans le terminal
            this.addTerminalLine('ai', `Décision prise: "${data.decision}"`, {reason: data.reason});
            
            this.addTimelineEvent('ai', `IA choisit: ${data.decision} (${data.reason})`, 'purple');
            
            // Stats
            this.stats.ai_decisions++;
            this.updateStats();
        }
    }
    
    onPopupExecuted(event) {
        const data = event.data;
        const popup = this.activePopups.get(data.popup_id);
        
        if (popup) {
            popup.status = 'executed';
            const duration = (new Date() - popup.startTime) / 1000;
            
            // Log dans le terminal
            this.addTerminalLine('action', `Action exécutée: Clic sur "${data.decision}" à (${data.coordinates[0]}, ${data.coordinates[1]})`);
            this.addTerminalLine('success', `Popup traité en ${duration.toFixed(1)}s`);
            
            this.addTimelineEvent('execute', `Exécuté en ${duration.toFixed(1)}s`, 'green');
            
            // Retirer après un délai
            setTimeout(() => {
                this.removePopupCard(data.popup_id);
                this.activePopups.delete(data.popup_id);
            }, 2000);
            
            // Mettre à jour le temps moyen
            this.updateAverageTime(duration);
        }
    }
    
    onServiceError(event) {
        const data = event.data;
        this.addTerminalLine('error', `Erreur ${data.service}: ${data.error}`);
        this.addTimelineEvent('error', `Erreur ${data.service}: ${data.error}`, 'red');
    }
    
    // UI Methods
    addPopupCard(id, data) {
        const container = document.getElementById('active-popups');
        const card = document.createElement('div');
        card.id = `popup-${id}`;
        card.className = 'popup-card bg-zinc-800 border border-zinc-700 rounded p-3 cursor-pointer hover:border-zinc-600';
        card.onclick = () => this.showPopupDetails(id);
        
        card.innerHTML = `
            <div class="flex justify-between items-start mb-2">
                <span class="text-xs text-zinc-500">#${id.substring(0, 8)}</span>
                <span class="status-badge text-xs px-2 py-1 rounded bg-blue-900 text-blue-300">detected</span>
            </div>
            <p class="text-sm text-white mb-2 line-clamp-2">${this.escapeHtml(data.text)}</p>
            <div class="options-list text-xs text-zinc-400"></div>
            <div class="decision-info text-xs text-green-400 mt-2 hidden"></div>
        `;
        
        container.insertBefore(card, container.firstChild);
        this.updatePopupCount();
    }
    
    updatePopupCard(id) {
        const card = document.getElementById(`popup-${id}`);
        if (!card) return;
        
        const popup = this.activePopups.get(id);
        const statusBadge = card.querySelector('.status-badge');
        const optionsList = card.querySelector('.options-list');
        const decisionInfo = card.querySelector('.decision-info');
        
        // Update status
        const statusColors = {
            'detected': 'bg-blue-900 text-blue-300',
            'analyzed': 'bg-yellow-900 text-yellow-300',
            'decided': 'bg-purple-900 text-purple-300',
            'executed': 'bg-green-900 text-green-300'
        };
        
        statusBadge.className = `status-badge text-xs px-2 py-1 rounded ${statusColors[popup.status]}`;
        statusBadge.textContent = popup.status;
        
        // Update options
        if (popup.options) {
            optionsList.textContent = `Options: ${popup.options.map(o => o.name).join(', ')}`;
        }
        
        // Update decision
        if (popup.decision) {
            decisionInfo.classList.remove('hidden');
            decisionInfo.innerHTML = `<i class="fas fa-robot"></i> ${popup.decision}`;
        }
    }
    
    removePopupCard(id) {
        const card = document.getElementById(`popup-${id}`);
        if (card) {
            card.style.opacity = '0';
            card.style.transform = 'translateX(-20px)';
            setTimeout(() => {
                card.remove();
                this.updatePopupCount();
            }, 300);
        }
    }
    
    addTimelineEvent(type, message, color) {
        const timeline = document.getElementById('event-timeline');
        const event = document.createElement('div');
        event.className = 'event-item bg-zinc-800 border-l-4 border-' + color + '-500 p-2 text-sm';
        
        const icons = {
            'popup': 'fa-window-restore',
            'analyze': 'fa-eye',
            'ai': 'fa-robot',
            'execute': 'fa-check-circle',
            'error': 'fa-exclamation-triangle'
        };
        
        const time = new Date().toLocaleTimeString();
        
        event.innerHTML = `
            <div class="flex items-center justify-between">
                <span class="flex items-center">
                    <i class="fas ${icons[type] || 'fa-info'} mr-2 text-${color}-400"></i>
                    ${this.escapeHtml(message)}
                </span>
                <span class="text-xs text-zinc-500">${time}</span>
            </div>
        `;
        
        timeline.insertBefore(event, timeline.firstChild);
        
        // Limiter l'historique
        if (timeline.children.length > 100) {
            timeline.removeChild(timeline.lastChild);
        }
    }
    
    showPopupDetails(id) {
        const popup = this.activePopups.get(id);
        if (!popup) return;
        
        const details = document.getElementById('popup-details');
        details.innerHTML = `
            <div class="space-y-4">
                <div>
                    <h4 class="text-xs text-zinc-400 mb-1">ID</h4>
                    <p class="font-mono text-sm">${id}</p>
                </div>
                <div>
                    <h4 class="text-xs text-zinc-400 mb-1">Texte</h4>
                    <p class="text-sm">${this.escapeHtml(popup.text)}</p>
                </div>
                ${popup.options ? `
                <div>
                    <h4 class="text-xs text-zinc-400 mb-1">Options détectées</h4>
                    <ul class="text-sm space-y-1">
                        ${popup.options.map(o => `
                            <li class="flex items-center">
                                <i class="fas fa-mouse-pointer mr-2 text-xs"></i>
                                ${o.name} 
                                <span class="text-xs text-zinc-500 ml-2">(conf: ${(o.confidence * 100).toFixed(0)}%)</span>
                            </li>
                        `).join('')}
                    </ul>
                </div>
                ` : ''}
                ${popup.decision ? `
                <div>
                    <h4 class="text-xs text-zinc-400 mb-1">Décision</h4>
                    <p class="text-sm text-green-400">${popup.decision}</p>
                    ${popup.reason ? `<p class="text-xs text-zinc-500 mt-1">${popup.reason}</p>` : ''}
                </div>
                ` : ''}
                <div>
                    <h4 class="text-xs text-zinc-400 mb-1">Statut</h4>
                    <p class="text-sm">${popup.status}</p>
                </div>
                ${popup.screenshot_base64 ? `
                <div>
                    <h4 class="text-xs text-zinc-400 mb-1">Screenshot</h4>
                    <img src="data:image/png;base64,${popup.screenshot_base64.substring(0, 100)}..." 
                         class="w-full rounded border border-zinc-700 cursor-pointer"
                         onclick="window.open('data:image/png;base64,${popup.screenshot_base64}', '_blank')">
                </div>
                ` : ''}
            </div>
        `;
    }
    
    // Control Methods
    async startMonitor() {
        try {
            const response = await fetch('/api/monitor/start', { method: 'POST' });
            if (response.ok) {
                document.getElementById('start-monitor').disabled = true;
                document.getElementById('stop-monitor').disabled = false;
                this.updateStatus('monitor-status', true);
                this.addTimelineEvent('info', 'Monitor démarré', 'green');
            }
        } catch (error) {
            console.error('Erreur démarrage monitor:', error);
        }
    }
    
    async stopMonitor() {
        try {
            const response = await fetch('/api/monitor/stop', { method: 'POST' });
            if (response.ok) {
                document.getElementById('start-monitor').disabled = false;
                document.getElementById('stop-monitor').disabled = true;
                this.updateStatus('monitor-status', false);
                this.addTimelineEvent('info', 'Monitor arrêté', 'red');
            }
        } catch (error) {
            console.error('Erreur arrêt monitor:', error);
        }
    }
    
    setAutoMode(enabled) {
        // Envoyer au serveur
        fetch('/api/monitor/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ auto_mode: enabled })
        });
    }
    
    // Helper Methods
    updatePopupCount() {
        document.getElementById('popup-count').textContent = 
            document.getElementById('active-popups').children.length;
    }
    
    updateStats() {
        document.getElementById('stat-total').textContent = this.stats.total;
        document.getElementById('stat-ai').textContent = this.stats.ai_decisions;
        document.getElementById('stat-time').textContent = this.stats.avg_time.toFixed(1) + 's';
        document.getElementById('stat-success').textContent = this.stats.success_rate + '%';
    }
    
    updateAverageTime(newTime) {
        // Calcul simple de la moyenne mobile
        const count = this.stats.total;
        this.stats.avg_time = ((this.stats.avg_time * (count - 1)) + newTime) / count;
        this.updateStats();
    }
    
    updateStatus(elementId, online) {
        const element = document.getElementById(elementId);
        element.className = `inline-block w-2 h-2 rounded-full ${online ? 'bg-green-500' : 'bg-red-500'}`;
    }
    
    async checkSystemStatus() {
        // Check AI
        try {
            const response = await fetch('/api/ai/status');
            const data = await response.json();
            this.updateStatus('ai-status', data.available || false);
        } catch {
            this.updateStatus('ai-status', false);
        }
        
        // Check Monitor
        try {
            const response = await fetch('/api/monitor/status');
            const data = await response.json();
            this.updateStatus('monitor-status', data.running || false);
        } catch {
            this.updateStatus('monitor-status', false);
        }
    }
    
    clearTimeline() {
        document.getElementById('event-timeline').innerHTML = '';
        this.addTimelineEvent('info', 'Timeline effacée', 'gray');
    }
    
    clearTerminal() {
        document.getElementById('activity-terminal').innerHTML = 
            '<div class="terminal-line">[SYSTEM] Terminal d\'activité réinitialisé...</div>';
    }
    
    addTerminalLine(type, message, details = null) {
        const terminal = document.getElementById('activity-terminal');
        const timestamp = new Date().toLocaleTimeString('fr-FR');
        const line = document.createElement('div');
        line.className = 'terminal-line';
        
        let prefix = '';
        let colorClass = '';
        
        switch(type) {
            case 'ram':
                prefix = '[RAM]';
                colorClass = 'terminal-ram';
                break;
            case 'popup':
                prefix = '[POPUP]';
                colorClass = 'terminal-popup';
                break;
            case 'ai':
                prefix = '[AI]';
                colorClass = 'terminal-ai';
                break;
            case 'action':
                prefix = '[ACTION]';
                colorClass = 'terminal-action';
                break;
            case 'error':
                prefix = '[ERROR]';
                colorClass = 'terminal-error';
                break;
            case 'success':
                prefix = '[OK]';
                colorClass = 'terminal-success';
                break;
            default:
                prefix = '[INFO]';
                colorClass = 'terminal-info';
        }
        
        line.innerHTML = `<span class="terminal-info">${timestamp}</span> <span class="${colorClass}">${prefix}</span> ${this.escapeHtml(message)}`;
        
        if (details) {
            line.innerHTML += ` <span class="terminal-info">${this.escapeHtml(JSON.stringify(details))}</span>`;
        }
        
        terminal.appendChild(line);
        
        // Auto-scroll
        terminal.scrollTop = terminal.scrollHeight;
        
        // Limiter le nombre de lignes
        while (terminal.children.length > 100) {
            terminal.removeChild(terminal.firstChild);
        }
    }
    
    // Méthodes pour les événements RAM
    onMemoryUpdated(event) {
        const data = event.data;
        this.addTerminalLine('ram', `Mémoire mise à jour: ${data.address} -> ${data.value}`);
        this.addTimelineEvent('ram', `RAM Update: ${data.address}`, 'blue');
    }
    
    onGameStateChanged(event) {
        const data = event.data;
        this.addTerminalLine('ram', `État de jeu changé: ${data.old_state} -> ${data.new_state}`);
        this.addTimelineEvent('ram', `Game State: ${data.new_state}`, 'purple');
    }
    
    playSound(type) {
        // Implémenter si nécessaire
        const audio = new Audio(`/static/sounds/${type}.mp3`);
        audio.play().catch(() => {});
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialiser au chargement
document.addEventListener('DOMContentLoaded', () => {
    window.monitoring = new MonopolyMonitoring();
});