/**
 * Module d'interface utilisateur
 * Gère les éléments d'interface et les interactions
 */

// État de l'interface
let state = {
    activeTab: 'events-tab'
};

/**
 * Initialise les écouteurs d'événements pour l'interface
 */
async function initUI() {
    try {
        // Charger la configuration
        const response = await fetch('/api/config');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const config = await response.json();
        
        // Mettre à jour les champs de configuration
        const dolphinPathInput = document.getElementById('dolphin-path');
        const isoPathInput = document.getElementById('iso-path');
        const refreshIntervalInput = document.getElementById('refresh-interval');
        
        if (dolphinPathInput) {
            dolphinPathInput.value = config.dolphinPath || '';
        }
        
        if (isoPathInput) {
            isoPathInput.value = config.isoPath || '';
        }
        
        if (refreshIntervalInput) {
            refreshIntervalInput.value = (config.refreshInterval || 2000) / 1000;
        }
    } catch (error) {
        console.error('Error loading configuration:', error);
        showNotification('Error loading configuration', 'error');
    }

    // Initialiser les autres composants de l'interface
    this.setupConfigDropdown();
    this.setupDolphinControls();
    this.setupPlayerConfig();
}

/**
 * Change l'onglet actif
 */
function switchTab(tabId) {
    // Mettre à jour l'état
    state.activeTab = tabId;
    
    // Mettre à jour les classes des boutons d'onglet
    const tabButtons = document.querySelectorAll('.tab-button');
    tabButtons.forEach(button => {
        if (button.id === tabId) {
            button.classList.remove('text-gray-400', 'border-transparent', 'hover:text-gray-300', 'hover:border-gray-700');
            button.classList.add('text-blue-500', 'border-blue-500');
        } else {
            button.classList.remove('text-blue-500', 'border-blue-500');
            button.classList.add('text-gray-400', 'border-transparent', 'hover:text-gray-300', 'hover:border-gray-700');
        }
    });
    
    // Afficher le contenu de l'onglet correspondant
    const contentId = tabId.replace('-tab', '-content');
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(content => {
        if (content.id === contentId) {
            content.classList.remove('hidden');
        } else {
            content.classList.add('hidden');
        }
    });
}

/**
 * Configure les contrôles de Dolphin
 */
function setupDolphinControls() {
    const startButton = document.getElementById('start-button');
    if (!startButton) return;

    startButton.addEventListener('click', async () => {
        try {
            // Désactiver le bouton pendant le démarrage
            startButton.disabled = true;
            startButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Starting...';

            // Démarrer Dolphin
            const response = await fetch('/api/dolphin', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            
            if (result.success) {
                showNotification('Dolphin started successfully', 'success');
                updateDolphinStatus(true);
            } else {
                throw new Error(result.error || 'Failed to start Dolphin');
            }
        } catch (error) {
            console.error('Error starting Dolphin:', error);
            showNotification(`Error starting Dolphin: ${error.message}`, 'error');
            
            // Réactiver le bouton en cas d'erreur
            startButton.disabled = false;
            startButton.innerHTML = '<i class="fas fa-play mr-2"></i>Start Dolphin';
        }
    });
}

/**
 * Met à jour le statut de Dolphin dans l'interface
 */
function updateDolphinStatus(running) {
    const startButton = document.getElementById('start-button');
    const dolphinContainer = document.getElementById('dolphin-container');

    if (running) {
        // Mettre à jour le bouton de démarrage
        startButton.innerHTML = '<i class="fas fa-stop mr-2"></i>Stop Dolphin';
        startButton.classList.remove('bg-white', 'hover:bg-zinc-200', 'text-black');
        startButton.classList.add('bg-red-600', 'hover:bg-red-700', 'text-white');
        
        // Mettre à jour le conteneur Dolphin avec un placeholder statique
        dolphinContainer.innerHTML = `
            <div class="relative w-full h-full bg-black flex items-center justify-center">
                <div class="text-center text-white max-w-md">
                    <i class="fas fa-gamepad text-6xl mb-6"></i>
                    <h3 class="text-2xl font-medium mb-4">Monopoly is running</h3>
                    <p class="text-zinc-400 mb-6">The game is now running in a separate window.</p>
                    <div class="bg-zinc-800 p-4 rounded-lg text-left mb-6">
                        <p class="text-sm mb-2"><i class="fas fa-keyboard mr-2"></i><strong>Windows+Tab</strong> or <strong>Alt+Tab</strong></p>
                        <p class="text-zinc-500 text-sm">Use these keyboard shortcuts to switch between windows and access the game.</p>
                    </div>
                    <p class="text-zinc-500 text-sm">When you're done playing, return here and click "Stop Dolphin" to close the emulator.</p>
                </div>
            </div>
        `;

        // Mettre à jour les joueurs après un court délai
        setTimeout(async () => {
            try {
                // Récupérer les valeurs des joueurs depuis localStorage
                const playerConfigs = document.querySelectorAll('.player-config');
                for (let i = 0; i < playerConfigs.length; i++) {
                    const name = localStorage.getItem(`player${i+1}Name`);
                    const money = localStorage.getItem(`player${i+1}Money`);
                    
                    if (name && money) {
                        // Mettre à jour le joueur via l'API
                        await fetch('/api/players', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                                id: i,
                                name: name,
                                money: parseInt(money)
                            })
                        });
                    }
                }
                
                // Afficher une notification de succès
                showNotification('Player information updated successfully', 'success');
            } catch (error) {
                console.error('Error updating players:', error);
            }
        }, 3000);

        // Changer la fonction du bouton pour arrêter Dolphin
        startButton.onclick = async () => {
            try {
                startButton.disabled = true;
                startButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Stopping...';

                const response = await fetch('/api/dolphin', {
                    method: 'DELETE'
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const result = await response.json();
                
                if (result.success) {
                    showNotification('Dolphin stopped successfully', 'success');
                    updateDolphinStatus(false);
                } else {
                    throw new Error(result.error || 'Failed to stop Dolphin');
                }
            } catch (error) {
                console.error('Error stopping Dolphin:', error);
                showNotification(`Error stopping Dolphin: ${error.message}`, 'error');
                
                // Réactiver le bouton en cas d'erreur
                startButton.disabled = false;
                startButton.innerHTML = '<i class="fas fa-stop mr-2"></i>Stop Dolphin';
            }
        };
    } else {
        // Remettre le bouton dans son état initial
        startButton.innerHTML = '<i class="fas fa-play mr-2"></i>Start Dolphin';
        startButton.disabled = false;
        startButton.classList.remove('bg-red-600', 'hover:bg-red-700', 'text-white');
        startButton.classList.add('bg-white', 'hover:bg-zinc-200', 'text-black');
        
        // Remettre le conteneur dans son état initial
        dolphinContainer.innerHTML = `
            <div class="text-center">
                <button id="start-button" class="bg-white hover:bg-zinc-200 text-black px-6 py-3 rounded-lg text-lg transition-colors duration-200 flex items-center">
                    <i class="fas fa-play mr-2"></i>
                    Start Dolphin
                </button>
            </div>
        `;

        // Réinitialiser les contrôles
        setupDolphinControls();
    }
}

/**
 * Met à jour le statut de connexion dans l'interface
 */
function updateConnectionStatus(connected) {
    const connectionStatus = document.getElementById('connection-status');
    const statusDot = connectionStatus.querySelector('span:first-child');
    const statusText = connectionStatus.querySelector('span:last-child');
    
    if (connected) {
        statusDot.className = 'inline-block h-2 w-2 rounded-full bg-green-500 mr-2';
        statusText.textContent = 'Online';
        connectionStatus.className = 'text-sm text-gray-300 flex items-center';
    } else {
        statusDot.className = 'inline-block h-2 w-2 rounded-full bg-red-500 mr-2';
        statusText.textContent = 'Offline';
        connectionStatus.className = 'text-sm text-gray-400 flex items-center';
    }
}

/**
 * Affiche une notification à l'utilisateur
 */
function showNotification(message, type = 'info') {
    // Créer l'élément de notification
    const notification = document.createElement('div');
    notification.className = `fixed bottom-4 right-4 p-3 rounded-lg shadow-lg z-50 flex items-center text-sm ${
        type === 'success' ? 'bg-green-900/80 text-green-200 border border-green-700' :
        type === 'error' ? 'bg-red-900/80 text-red-200 border border-red-700' :
        'bg-blue-900/80 text-blue-200 border border-blue-700'
    }`;
    
    // Ajouter l'icône
    const icon = document.createElement('i');
    icon.className = `fas ${
        type === 'success' ? 'fa-check-circle' :
        type === 'error' ? 'fa-exclamation-circle' :
        'fa-info-circle'
    } mr-2`;
    notification.appendChild(icon);
    
    // Ajouter le message
    const text = document.createElement('span');
    text.textContent = message;
    notification.appendChild(text);
    
    // Ajouter au document
    document.body.appendChild(notification);
    
    // Supprimer après 3 secondes
    setTimeout(() => {
        notification.classList.add('opacity-0', 'transition-opacity', 'duration-500');
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 500);
    }, 3000);
}

/**
 * Crée une fenêtre pour afficher Dolphin
 */
function createDolphinWindow() {
    const dolphinContainer = document.getElementById('dolphin-container');
    
    // Vider le conteneur
    dolphinContainer.innerHTML = '';
    
    // Créer un message d'information
    const infoMessage = document.createElement('div');
    infoMessage.className = 'absolute top-0 left-0 right-0 bg-black/70 text-white p-2 text-xs text-center z-10';
    infoMessage.textContent = 'Dolphin is running. Use Alt+Tab to interact with the window.';
    dolphinContainer.appendChild(infoMessage);
    
    // Créer un conteneur pour les contrôles
    const controlsContainer = document.createElement('div');
    controlsContainer.className = 'absolute bottom-0 left-0 right-0 bg-black/70 p-2 flex justify-center space-x-2 z-10';
    
    // Bouton pour rafraîchir manuellement la capture d'écran
    const refreshButton = document.createElement('button');
    refreshButton.className = 'bg-blue-600 hover:bg-blue-700 text-white py-1 px-2 rounded text-xs flex items-center';
    refreshButton.innerHTML = '<i class="fas fa-sync-alt mr-1"></i> Refresh';
    
    // Ajouter les contrôles au conteneur
    controlsContainer.appendChild(refreshButton);
    dolphinContainer.appendChild(controlsContainer);
    
    // Créer une image pour afficher la capture d'écran de Dolphin
    const screenshotImg = document.createElement('img');
    screenshotImg.className = 'w-full h-full object-contain';
    screenshotImg.alt = 'Dolphin Screenshot';
    
    // Afficher un loader en attendant la première capture
    screenshotImg.src = '/static/img/loading.gif';
    dolphinContainer.appendChild(screenshotImg);
    
    // Variables pour gérer les erreurs et les tentatives
    let errorCount = 0;
    let isCapturing = false;
    let isInitializing = true;
    
    // Fonction pour mettre à jour la capture d'écran
    const updateScreenshot = async () => {
        // Vérifier si Dolphin est en cours d'exécution
        if (!document.getElementById('dolphin-status').textContent.includes('running')) {
            return;
        }
        
        // Éviter les requêtes simultanées
        if (isCapturing) {
            return;
        }
        
        isCapturing = true;
        
        try {
            // Vérifier d'abord si Dolphin est prêt
            const response = await fetch('/api/dolphin/status');
            const status = await response.json();
            
            if (!status.running) {
                if (isInitializing) {
                    screenshotImg.src = '/static/img/loading.gif';
                    return;
                }
                throw new Error('Dolphin is not ready');
            }
            
            // Ajouter un timestamp pour éviter la mise en cache du navigateur
            const timestamp = new Date().getTime();
            
            // Créer une nouvelle image pour éviter les problèmes de cache
            const newImg = new Image();
            newImg.onload = () => {
                // Mettre à jour l'image affichée
                screenshotImg.src = newImg.src;
                errorCount = 0;
                isCapturing = false;
                isInitializing = false;
            };
            
            newImg.onerror = () => {
                errorCount++;
                isCapturing = false;
                
                // Si trop d'erreurs consécutives, afficher un message d'erreur
                if (errorCount > 5) {
                    screenshotImg.src = '/static/img/error.png';
                    showNotification('Cannot capture Dolphin window. The emulator might be minimized or not visible.', 'error');
                }
            };
            
            // Charger la nouvelle image
            newImg.src = `/api/dolphin/screenshot?t=${timestamp}`;
        } catch (error) {
            console.error('Error updating screenshot:', error);
            isCapturing = false;
            
            if (isInitializing) {
                screenshotImg.src = '/static/img/loading.gif';
            } else {
                screenshotImg.src = '/static/img/error.png';
            }
        }
    };
    
    // Mettre à jour la capture d'écran toutes les 500ms
    const screenshotInterval = setInterval(updateScreenshot, 500);
    
    // Ajouter un événement au bouton de rafraîchissement
    refreshButton.addEventListener('click', () => {
        updateScreenshot();
        showNotification('Refreshing Dolphin window', 'info');
    });
    
    // Nettoyer l'intervalle lorsque la fenêtre est fermée
    window.addEventListener('beforeunload', () => {
        clearInterval(screenshotInterval);
    });
    
    // Déclencher la première mise à jour
    setTimeout(updateScreenshot, 1000);
    
    return true;
}

/**
 * Affiche un loader avec un message
 */
function showLoader(message) {
    // Créer le conteneur du loader s'il n'existe pas
    let loader = document.getElementById('global-loader');
    if (!loader) {
        loader = document.createElement('div');
        loader.id = 'global-loader';
        loader.className = 'fixed inset-0 bg-black/80 flex items-center justify-center z-50';
        document.body.appendChild(loader);
    }
    
    // Mettre à jour le contenu du loader
    loader.innerHTML = `
        <div class="text-center">
            <div class="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500 mb-4"></div>
            <div class="text-white text-sm">${message}</div>
        </div>
    `;
    
    // Afficher le loader
    loader.style.display = 'flex';
}

/**
 * Cache le loader global
 */
function hideLoader() {
    const loader = document.getElementById('global-loader');
    if (loader) {
        loader.style.display = 'none';
    }
}

// UI Module
const ui = {
    initUI() {
        this.setupConfigDropdown();
        this.setupDolphinControls();
        this.setupPlayerConfig();
    },

    setupConfigDropdown() {
        const configButton = document.getElementById('config-button');
        const configDropdown = document.getElementById('config-dropdown');

        configButton.addEventListener('click', () => {
            configDropdown.classList.toggle('hidden');
        });

        document.addEventListener('click', (e) => {
            if (!configButton.contains(e.target) && !configDropdown.contains(e.target)) {
                configDropdown.classList.add('hidden');
            }
        });
    },

    setupDolphinControls() {
        const startButton = document.getElementById('start-button');
        const dolphinContainer = document.getElementById('dolphin-container');

        startButton.addEventListener('click', async () => {
            try {
                startButton.disabled = true;
                startButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Starting...';
                
                const response = await fetch('/api/dolphin', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const result = await response.json();
                
                if (result.success) {
                    showNotification('Dolphin started successfully', 'success');
                    updateDolphinStatus(true);
                } else {
                    throw new Error(result.error || 'Failed to start Dolphin');
                }
            } catch (error) {
                console.error('Error starting Dolphin:', error);
                showNotification(`Error starting Dolphin: ${error.message}`, 'error');
                
                // Réactiver le bouton en cas d'erreur
                startButton.disabled = false;
                startButton.innerHTML = '<i class="fas fa-play mr-2"></i>Start Dolphin';
            }
        });
    },

    async stopDolphin() {
        try {
            const response = await fetch('/api/dolphin', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ action: 'stop' })
            });

            if (!response.ok) {
                throw new Error('Failed to stop Dolphin');
            }

            const dolphinContainer = document.getElementById('dolphin-container');
            dolphinContainer.innerHTML = `
                <div class="text-center">
                    <button id="start-button" class="bg-white hover:bg-zinc-200 text-black px-6 py-3 rounded-lg text-lg transition-colors duration-200 flex items-center">
                        <i class="fas fa-play mr-2"></i>
                        Démarrer Dolphin
                    </button>
                </div>
            `;

            this.setupDolphinControls();

        } catch (error) {
            console.error('Error stopping Dolphin:', error);
        }
    },

    setupPlayerConfig() {
        const defaultPlayers = [
            { name: 'GPT 4-o', money: '1500' },
            { name: 'Claude 3.5', money: '1500' }
        ];

        const playerConfigs = document.querySelectorAll('.player-config');
        
        playerConfigs.forEach((config, index) => {
            const nameInput = config.querySelector('input[type="text"]');
            const moneyInput = config.querySelector('input[type="number"]');

            // Initialiser le localStorage avec les valeurs par défaut si non existantes
            if (!localStorage.getItem(`player${index+1}Name`)) {
                localStorage.setItem(`player${index+1}Name`, defaultPlayers[index].name);
            }
            if (!localStorage.getItem(`player${index+1}Money`)) {
                localStorage.setItem(`player${index+1}Money`, defaultPlayers[index].money);
            }

            nameInput.value = localStorage.getItem(`player${index+1}Name`);
            moneyInput.value = localStorage.getItem(`player${index+1}Money`);

            // Fonction pour mettre à jour les joueurs via l'API
            const updatePlayerViaAPI = async (playerId, name, money) => {
                try {
                    const response = await fetch('/api/players', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            id: playerId,
                            name: name,
                            money: parseInt(money)
                        })
                    });
                    
                    if (!response.ok) {
                        console.error(`Failed to update player ${playerId}`);
                    }
                } catch (error) {
                    console.error('Error updating player:', error);
                }
            };

            nameInput.addEventListener('change', () => {
                localStorage.setItem(`player${index+1}Name`, nameInput.value);
                // Mettre à jour le joueur via l'API si Dolphin est en cours d'exécution
                updatePlayerViaAPI(index, nameInput.value, moneyInput.value);
            });

            moneyInput.addEventListener('change', () => {
                localStorage.setItem(`player${index+1}Money`, moneyInput.value);
                // Mettre à jour le joueur via l'API si Dolphin est en cours d'exécution
                updatePlayerViaAPI(index, nameInput.value, moneyInput.value);
            });
        });
        
        // Mettre à jour les joueurs au démarrage de Dolphin
        document.getElementById('start-button').addEventListener('click', async () => {
            // Attendre un peu que Dolphin démarre
            setTimeout(async () => {
                // Mettre à jour les joueurs avec les valeurs du localStorage
                for (let i = 0; i < playerConfigs.length; i++) {
                    const name = localStorage.getItem(`player${i+1}Name`);
                    const money = localStorage.getItem(`player${i+1}Money`);
                    if (name && money) {
                        await fetch('/api/players', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                                id: i,
                                name: name,
                                money: parseInt(money)
                            })
                        }).catch(error => console.error('Error updating player:', error));
                    }
                }
            }, 5000); // Attendre 5 secondes pour que Dolphin démarre complètement
        });
    },

    updateGameInfo(context) {
        const playersList = document.getElementById('players-list');
        const eventsList = document.getElementById('events-list');

        if (context.players) {
            playersList.innerHTML = Object.entries(context.players)
                .map(([id, player]) => `
                    <div class="bg-zinc-800 border border-zinc-700 rounded p-3">
                        <div class="flex justify-between items-center mb-2">
                            <div class="font-medium">${player.name}</div>
                            <div class="text-white">${player.money}€</div>
                        </div>
                        <div class="text-sm text-zinc-400">Position: ${player.position}</div>
                    </div>
                `).join('');
        }

        if (context.events) {
            eventsList.innerHTML = context.events
                .map(event => `
                    <div class="bg-zinc-800 border border-zinc-700 rounded p-2 text-sm">
                        <span class="text-white font-medium">${event.player}</span>
                        <span class="text-zinc-400">${event.action}:</span>
                        <span class="text-white">${event.details}</span>
                    </div>
                `).join('');
        }
    },

    updateTerminal(output) {
        const terminalOutput = document.getElementById('terminal-output');
        
        // Convertir les codes de couleur ANSI en classes CSS
        const formattedOutput = output.map(line => {
            // Remplacer les emojis par des spans avec des classes
            let formattedLine = line
                .replace(/💰/g, '<span class="emoji">💰</span>')
                .replace(/💸/g, '<span class="emoji">💸</span>')
                .replace(/👤/g, '<span class="emoji">👤</span>')
                .replace(/🎲/g, '<span class="emoji">🎲</span>')
                .replace(/✨/g, '<span class="emoji">✨</span>')
                .replace(/👋/g, '<span class="emoji">👋</span>')
                .replace(/📢/g, '<span class="emoji">📢</span>')
                .replace(/🗑️/g, '<span class="emoji">🗑️</span>')
                .replace(/ℹ️/g, '<span class="emoji">ℹ️</span>')
                .replace(/🚶/g, '<span class="emoji">🚶</span>');
            
            // Remplacer les codes de couleur par des classes CSS
            if (line.includes('a rejoint la partie')) {
                return `<span class="text-green-400">${formattedLine}</span>`;
            } else if (line.includes('a quitté la partie')) {
                return `<span class="text-red-400">${formattedLine}</span>`;
            } else if (line.includes('a lancé les dés')) {
                return `<span class="text-yellow-400">${formattedLine}</span>`;
            } else if (line.includes('a changé son nom')) {
                return `<span class="text-yellow-400">${formattedLine}</span>`;
            } else if (line.includes('💰')) {
                return `<span class="text-cyan-400">${formattedLine.split('💰')[0]}</span><span class="emoji">💰</span><span class="text-green-400">${formattedLine.split('💰')[1]}</span>`;
            } else if (line.includes('💸')) {
                return `<span class="text-cyan-400">${formattedLine.split('💸')[0]}</span><span class="emoji">💸</span><span class="text-red-400">${formattedLine.split('💸')[1]}</span>`;
            } else if (line.includes('📢')) {
                return `<span class="text-purple-400">${formattedLine.split(':')[0]}:</span><span class="text-white">${formattedLine.split(':')[1] || ''}</span>`;
            } else if (line.includes('ℹ️')) {
                return `<span class="text-cyan-400">${formattedLine}</span>`;
            } else {
                return formattedLine;
            }
        });
        
        // Mettre à jour le contenu avec le formatage HTML
        terminalOutput.innerHTML = formattedOutput.join('<br>');
        
        // Faire défiler vers le bas
        terminalOutput.scrollTop = terminalOutput.scrollHeight;
    }
};

export default ui; 