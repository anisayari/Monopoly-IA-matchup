/**
 * Module d'interface utilisateur
 * Gère les éléments d'interface et les interactions
 */

import config from './config.js';

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
        const configData = await response.json();
        
        // Mettre à jour les champs de configuration
        const dolphinPathInput = document.getElementById('dolphin-path');
        const isoPathInput = document.getElementById('iso-path');
        const savePathInput = document.getElementById('save-path');
        const memoryEnginePathInput = document.getElementById('memory-engine-path');
        const refreshIntervalInput = document.getElementById('refresh-interval');
        
        if (dolphinPathInput) {
            dolphinPathInput.value = configData.dolphinPath || '';
        }
        
        if (isoPathInput) {
            isoPathInput.value = configData.isoPath || '';
        }
        
        if (savePathInput) {
            savePathInput.value = configData.savePath || '';
        }
        
        if (memoryEnginePathInput) {
            memoryEnginePathInput.value = configData.memoryEnginePath || '';
        }
        
        if (refreshIntervalInput) {
            refreshIntervalInput.value = (configData.refreshInterval || 2000) / 1000;
        }
    } catch (error) {
        console.error('Error loading configuration:', error);
        showNotification('Error loading configuration', 'error');
    }

    // Initialiser les autres composants de l'interface
    this.setupConfigDropdown();
    this.setupDolphinControls();
    this.setupPlayerConfig();
    
    // Initialiser le bouton de sauvegarde de configuration
    config.initSaveButton();
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
        
        // Créer la fenêtre de partage d'écran au lieu du message statique
        createDolphinWindow();

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
    
    // Créer le conteneur vidéo pour le partage d'écran
    const videoContainer = document.createElement('div');
    videoContainer.className = 'video-crop-container';
    
    // Créer l'élément vidéo
    const video = document.createElement('video');
    video.id = 'dolphin-video';
    video.className = 'w-full h-full object-contain';
    video.autoplay = true;
    video.playsInline = true;
    videoContainer.appendChild(video);
    
    // Message initial
    const messageContainer = document.createElement('div');
    messageContainer.id = 'dolphin-message';
    messageContainer.className = 'absolute inset-0 flex flex-col items-center justify-center text-white text-center p-8';
    messageContainer.innerHTML = `
        <div class="mb-6">
            <i class="fas fa-spinner fa-spin text-6xl mb-4"></i>
            <h3 class="text-xl font-medium mb-2">Configuration du partage d'écran...</h3>
            <p class="text-sm text-zinc-400 mb-2">Une boîte de dialogue va s'ouvrir dans 5 secondes</p>
            <div class="bg-zinc-800 border border-zinc-700 rounded-lg p-4 mt-4 text-left max-w-md">
                <p class="text-sm font-medium mb-2">📋 Instructions :</p>
                <ol class="text-sm text-zinc-300 space-y-1 list-decimal list-inside">
                    <li>Attendez la boîte de dialogue de partage</li>
                    <li>Sélectionnez l'onglet <span class="text-white font-medium">"Fenêtre"</span></li>
                    <li>Cherchez <span class="text-white font-medium">"Dolphin 2412"</span></li>
                    <li>Cliquez sur la fenêtre Dolphin</li>
                    <li>Cliquez sur <span class="text-white font-medium">"Partager"</span></li>
                </ol>
            </div>
        </div>
    `;
    videoContainer.appendChild(messageContainer);
    
    // Créer un conteneur pour les contrôles
    const controlsContainer = document.createElement('div');
    controlsContainer.id = 'video-controls';
    controlsContainer.className = 'absolute bottom-0 left-0 right-0 bg-black/70 p-2 flex justify-center space-x-2 z-10 hidden';
    
    // Bouton pour arrêter le partage
    const stopShareButton = document.createElement('button');
    stopShareButton.className = 'bg-red-600 hover:bg-red-700 text-white py-1 px-3 rounded text-sm flex items-center';
    stopShareButton.innerHTML = '<i class="fas fa-stop mr-1"></i> Arrêter le partage';
    
    controlsContainer.appendChild(stopShareButton);
    videoContainer.appendChild(controlsContainer);
    
    dolphinContainer.appendChild(videoContainer);
    
    // Variable pour stocker le stream
    let mediaStream = null;
    
    // Fonction pour démarrer le partage d'écran
    const startScreenShare = async () => {
        try {
            // Options pour le partage d'écran - privilégier les fenêtres
            const displayMediaOptions = {
                video: {
                    displaySurface: 'window',
                    logicalSurface: true,
                    cursor: 'always'
                },
                audio: false,
                preferCurrentTab: false
            };
            
            // Demander à l'utilisateur de sélectionner une fenêtre
            mediaStream = await navigator.mediaDevices.getDisplayMedia(displayMediaOptions);
            
            // Attacher le stream à l'élément vidéo
            video.srcObject = mediaStream;
            
            // Masquer le message et afficher les contrôles
            messageContainer.classList.add('hidden');
            controlsContainer.classList.remove('hidden');
            
            // Gérer l'arrêt du partage par l'utilisateur
            mediaStream.getVideoTracks()[0].addEventListener('ended', () => {
                stopScreenShare();
            });
            
            showNotification('Partage d\'écran démarré', 'success');
        } catch (error) {
            console.error('Erreur lors du partage d\'écran:', error);
            // Si l'utilisateur annule, afficher le bouton de partage manuel
            messageContainer.innerHTML = `
                <div class="mb-6">
                    <i class="fas fa-desktop text-6xl mb-4"></i>
                    <h3 class="text-xl font-medium mb-2">Monopoly est en cours d'exécution</h3>
                    <p class="text-sm text-zinc-400 mb-4">Le jeu tourne dans une fenêtre séparée.</p>
                </div>
                <button id="share-screen-btn" class="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg flex items-center">
                    <i class="fas fa-share-square mr-2"></i>
                    Partager la fenêtre Dolphin
                </button>
                <p class="text-xs text-zinc-500 mt-4">Cliquez sur le bouton pour sélectionner et afficher la fenêtre Dolphin ici</p>
            `;
            
            // Réattacher l'événement au bouton
            const shareButton = document.getElementById('share-screen-btn');
            if (shareButton) {
                shareButton.addEventListener('click', startScreenShare);
            }
        }
    };
    
    // Configurer le bouton d'arrêt
    stopShareButton.addEventListener('click', () => {
        stopScreenShare();
    });
    
    // Fonction pour arrêter le partage
    const stopScreenShare = () => {
        if (mediaStream) {
            mediaStream.getTracks().forEach(track => track.stop());
            mediaStream = null;
            video.srcObject = null;
        }
        
        // Réafficher le message avec le bouton de partage
        messageContainer.classList.remove('hidden');
        controlsContainer.classList.add('hidden');
        messageContainer.innerHTML = `
            <div class="mb-6">
                <i class="fas fa-desktop text-6xl mb-4"></i>
                <h3 class="text-xl font-medium mb-2">Monopoly est en cours d'exécution</h3>
                <p class="text-sm text-zinc-400 mb-4">Le jeu tourne dans une fenêtre séparée.</p>
            </div>
            <button id="share-screen-btn" class="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg flex items-center">
                <i class="fas fa-share-square mr-2"></i>
                Partager la fenêtre Dolphin
            </button>
            <p class="text-xs text-zinc-500 mt-4">Cliquez sur le bouton pour sélectionner et afficher la fenêtre Dolphin ici</p>
        `;
        
        // Réattacher l'événement au bouton
        const shareButton = document.getElementById('share-screen-btn');
        if (shareButton) {
            shareButton.addEventListener('click', startScreenShare);
        }
        
        showNotification('Partage d\'écran arrêté', 'info');
    };
    
    // Nettoyer lors de la fermeture
    window.addEventListener('beforeunload', () => {
        stopScreenShare();
    });
    
    // Démarrer automatiquement le partage d'écran après un délai pour que Dolphin ait le temps de s'ouvrir
    let countdown = 5;
    const countdownElement = document.createElement('div');
    countdownElement.className = 'text-3xl font-bold text-blue-400 mt-4';
    countdownElement.textContent = countdown;
    messageContainer.querySelector('.mb-6').appendChild(countdownElement);
    
    const countdownInterval = setInterval(() => {
        countdown--;
        countdownElement.textContent = countdown;
        
        if (countdown === 0) {
            clearInterval(countdownInterval);
            countdownElement.textContent = '🖱️';
            startScreenShare();
        }
    }, 1000);
    
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

        configButton.addEventListener('click', async () => {
            configDropdown.classList.toggle('hidden');
            
            // Si on ouvre le dropdown, charger la configuration actuelle
            if (!configDropdown.classList.contains('hidden')) {
                try {
                    const response = await fetch('/api/config');
                    if (response.ok) {
                        const configData = await response.json();
                        
                        // Mettre à jour les champs
                        const dolphinPath = document.getElementById('dolphin-path');
                        const isoPath = document.getElementById('iso-path');
                        const savePath = document.getElementById('save-path');
                        const memoryEnginePath = document.getElementById('memory-engine-path');
                        const refreshInterval = document.getElementById('refresh-interval');
                        
                        if (dolphinPath) dolphinPath.value = configData.dolphinPath || '';
                        if (isoPath) isoPath.value = configData.isoPath || '';
                        if (savePath) savePath.value = configData.savePath || '';
                        if (memoryEnginePath) memoryEnginePath.value = configData.memoryEnginePath || '';
                        if (refreshInterval) refreshInterval.value = (configData.refreshInterval || 2000) / 1000;
                    }
                } catch (error) {
                    console.error('Erreur lors du chargement de la configuration:', error);
                }
            }
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

    async updateGameInfo(context) {
        const playersList = document.getElementById('players-list');
        const eventsList = document.getElementById('events-list');

        if (context.players) {
            // Charger les paramètres de jeu pour obtenir les infos AI
            let gameSettings = null;
            try {
                const response = await fetch('/api/game-settings');
                if (response.ok) {
                    gameSettings = await response.json();
                }
            } catch (error) {
                console.error('Error loading game settings:', error);
            }
            
            playersList.innerHTML = Object.entries(context.players)
                .map(([id, player]) => {
                    // Récupérer les infos AI depuis les paramètres
                    let aiInfo = '';
                    if (gameSettings && gameSettings.players[id]) {
                        const playerSettings = gameSettings.players[id];
                        const provider = playerSettings.provider;
                        const model = playerSettings.ai_model;
                        
                        // Obtenir le nom du modèle depuis les providers disponibles
                        let modelName = model;
                        if (gameSettings.available_providers && 
                            gameSettings.available_providers[provider] && 
                            gameSettings.available_providers[provider].models) {
                            const modelData = gameSettings.available_providers[provider].models.find(m => m.id === model);
                            if (modelData) {
                                modelName = modelData.name;
                            }
                        }
                        
                        const providerIcons = {
                            'openai': 'fas fa-robot',
                            'anthropic': 'fas fa-brain',
                            'gemini': 'fas fa-gem'
                        };
                        
                        aiInfo = `
                            <div class="text-xs text-zinc-500 mt-1 flex items-center">
                                <i class="${providerIcons[provider] || 'fas fa-microchip'} mr-1"></i>
                                ${modelName}
                            </div>
                        `;
                    }
                    
                    return `
                        <div class="bg-zinc-800 border border-zinc-700 rounded p-3">
                            <div class="flex justify-between items-center mb-2">
                                <div class="font-medium">${player.name}</div>
                                <div class="text-white">${player.money}€</div>
                            </div>
                            <div class="text-sm text-zinc-400">Position: ${player.position}</div>
                            ${aiInfo}
                        </div>
                    `;
                }).join('');
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
        
        // Mise à jour du contexte des propriétés
        this.updatePropertiesContext(context);
    },
    
    updatePropertiesContext(context) {
        const propertiesContextDiv = document.getElementById('properties-context');
        if (!propertiesContextDiv || !context.players) return;
        
        let contextHTML = '';
        
        // Parcourir tous les joueurs
        Object.entries(context.players).forEach(([playerId, playerData]) => {
            const properties = playerData.properties || [];
            if (properties.length === 0) return;
            
            contextHTML += `<div class="mb-4">`;
            contextHTML += `<div class="text-yellow-400 font-bold">${playerData.name} (${properties.length} propriétés)</div>`;
            
            // Grouper les propriétés par groupe/couleur
            const groupedProperties = {};
            let mortgagedCount = 0;
            
            properties.forEach(prop => {
                const group = prop.group || 'unknown';
                if (!groupedProperties[group]) {
                    groupedProperties[group] = [];
                }
                groupedProperties[group].push(prop);
                if (prop.is_mortgaged) mortgagedCount++;
            });
            
            // Afficher les propriétés hypothéquées en premier s'il y en a
            if (mortgagedCount > 0) {
                contextHTML += `<div class="text-red-400 mt-1">⚠️ ${mortgagedCount} propriétés hypothéquées</div>`;
            }
            
            // Afficher par groupe
            Object.entries(groupedProperties).forEach(([group, props]) => {
                const groupColors = {
                    'brown': 'text-yellow-600',
                    'light blue': 'text-blue-400',
                    'pink': 'text-pink-400',
                    'orange': 'text-orange-400',
                    'red': 'text-red-500',
                    'yellow': 'text-yellow-400',
                    'green': 'text-green-500',
                    'dark blue': 'text-blue-700',
                    'station': 'text-gray-400',
                    'utility': 'text-purple-400'
                };
                
                const colorClass = groupColors[group.toLowerCase()] || 'text-zinc-400';
                contextHTML += `<div class="mt-2">`;
                contextHTML += `<div class="${colorClass} font-semibold">${group.toUpperCase()}</div>`;
                
                props.forEach(prop => {
                    let status = '';
                    if (prop.is_mortgaged) {
                        status = '<span class="text-red-400">HYPO</span>';
                    } else if (prop.houses === 5) {
                        status = '<span class="text-purple-400">HÔTEL</span>';
                    } else if (prop.houses > 0) {
                        status = `<span class="text-green-400">${prop.houses}🏠</span>`;
                    }
                    
                    contextHTML += `<div class="ml-2 text-zinc-300">• ${prop.name} ${status}</div>`;
                });
                
                contextHTML += `</div>`;
            });
            
            contextHTML += `</div>`;
        });
        
        // Afficher les propriétés disponibles sur le plateau
        if (context.global && context.global.properties) {
            const availableProps = context.global.properties.filter(p => !p.owner);
            if (availableProps.length > 0) {
                contextHTML += `<div class="mt-4 pt-4 border-t border-zinc-700">`;
                contextHTML += `<div class="text-green-400 font-bold mb-2">Propriétés disponibles (${availableProps.length})</div>`;
                contextHTML += `<div class="text-xs text-zinc-400">`;
                availableProps.forEach(prop => {
                    contextHTML += `${prop.name}, `;
                });
                contextHTML = contextHTML.slice(0, -2); // Enlever la dernière virgule
                contextHTML += `</div></div>`;
            }
        }
        
        if (contextHTML === '') {
            contextHTML = '<div class="text-zinc-400">Aucune propriété possédée</div>';
        }
        
        propertiesContextDiv.innerHTML = contextHTML;
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