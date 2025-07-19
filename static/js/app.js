/**
 * Monopoly Manager - Application JavaScript
 * Point d'entrée principal qui utilise les modules
 */

// Importer les modules
import config from './modules/config.js';
import ui from './modules/ui.js';
import dolphin from './modules/dolphin.js';
import data from './modules/data.js';
import refresh from './modules/refresh.js';
import admin from './modules/admin.js';

// Configuration
const REFRESH_INTERVAL = 2000; // ms
let autoRefresh = true;
let refreshTimer = null;
let dolphinWindowCreated = false;

// Éléments DOM
const elements = {
    // Contrôles
    startDolphinBtn: document.getElementById('start-dolphin'),
    stopDolphinBtn: document.getElementById('stop-dolphin'),
    restartGameBtn: document.getElementById('restart-game'),
    configForm: document.getElementById('config-form'),
    dolphinPath: document.getElementById('dolphin-path'),
    isoPath: document.getElementById('iso-path'),
    savePath: document.getElementById('save-path'),
    refreshInterval: document.getElementById('refresh-interval'),
    
    // Game Settings
    gameSettingsBtn: document.getElementById('game-settings-btn'),
    gameSettingsModal: document.getElementById('game-settings-modal'),
    closeGameSettings: document.getElementById('close-game-settings'),
    cancelGameSettings: document.getElementById('cancel-game-settings'),
    saveGameSettings: document.getElementById('save-game-settings'),
    player1Name: document.getElementById('player1-name'),
    player1Model: document.getElementById('player1-model'),
    player2Name: document.getElementById('player2-name'),
    player2Model: document.getElementById('player2-model'),
    aiEnabled: document.getElementById('ai-enabled'),
    
    // Affichage
    playersContainer: document.getElementById('players-container'),
    dolphinStatus: document.getElementById('dolphin-status'),
    dolphinContainer: document.getElementById('dolphin-container'),
    terminalOutput: document.getElementById('terminal-output'),
    autoRefreshToggle: document.getElementById('auto-refresh'),
    connectionStatus: document.getElementById('connection-status'),
    
    // Onglets de contexte
    tabButtons: document.querySelectorAll('.tab-button'),
    tabContents: document.querySelectorAll('.tab-content'),
    eventsTab: document.getElementById('events-tab'),
    playersTab: document.getElementById('players-tab'),
    propertiesTab: document.getElementById('properties-tab'),
    boardTab: document.getElementById('board-tab'),
    rawTab: document.getElementById('raw-tab'),
    
    // Conteneurs de contenu
    eventsContainer: document.getElementById('events-container'),
    playersDetailsContainer: document.getElementById('players-details-container'),
    propertiesContainer: document.getElementById('properties-container'),
    boardContainer: document.getElementById('board-container'),
    rawContext: document.getElementById('raw-context')
};

// État de l'application
let appState = {
    dolphinRunning: false,
    context: null,
    players: [],
    terminal: [],
    activeTab: 'events-tab'
};

// Initialisation de l'application
document.addEventListener('DOMContentLoaded', async () => {
    console.log('Initializing Monopoly Manager...');
    
    // Initialiser l'interface utilisateur
    ui.initUI();
    
    // Initialiser le module admin
    admin.init();
    
    // Vérifier si Dolphin est déjà en cours d'exécution
    try {
        const response = await fetch('/api/dolphin/status');
        const status = await response.json();
        
        if (status.running) {
            // Restaurer l'état de Dolphin
            ui.updateDolphinStatus(true);
            // Démarrer la vérification automatique
            refresh.startAutoRefresh();
        }
    } catch (error) {
        console.error('Error checking Dolphin status:', error);
    }
    
    console.log('Monopoly Manager initialized successfully');
});

/**
 * Configure les écouteurs d'événements pour les contrôles
 */
function setupEventListeners() {
    // Contrôles Dolphin
    const startDolphinBtn = document.getElementById('start-dolphin');
    if (startDolphinBtn) {
        startDolphinBtn.addEventListener('click', async () => {
            const savePath = document.getElementById('save-path')?.value;
            await dolphin.startDolphin(savePath);
            await data.loadGameContext();
        });
    }
    
    const stopDolphinBtn = document.getElementById('stop-dolphin');
    if (stopDolphinBtn) {
        stopDolphinBtn.addEventListener('click', async () => {
            await dolphin.stopDolphin();
            await data.loadGameContext();
        });
    }
    
    // Contrôle du jeu
    const restartGameBtn = document.getElementById('restart-game');
    if (restartGameBtn) {
        restartGameBtn.addEventListener('click', async () => {
            if (confirm('Are you sure you want to restart the game? All unsaved data will be lost.')) {
                const restartDolphinToo = confirm('Do you also want to restart Dolphin?');
                await dolphin.restartGame(restartDolphinToo);
                await data.loadGameContext();
            }
        });
    }
    
    // Configuration
    const configForm = document.getElementById('config-form');
    if (configForm) {
        configForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            
            const formData = {
                dolphinPath: document.getElementById('dolphin-path')?.value || '',
                isoPath: document.getElementById('iso-path')?.value || '',
                savePath: document.getElementById('save-path')?.value || '',
                refreshInterval: document.getElementById('refresh-interval')?.value * 1000 || 2000
            };
            
            await config.saveConfig(formData);
            
            // Mettre à jour l'intervalle de rafraîchissement si nécessaire
            refresh.restartAutoRefresh(parseInt(formData.refreshInterval));
        });
    }
    
    // Rafraîchissement automatique
    const autoRefreshToggle = document.getElementById('auto-refresh-toggle');
    if (autoRefreshToggle) {
        autoRefreshToggle.addEventListener('change', (event) => {
            refresh.toggleAutoRefresh(event.target.checked);
        });
    }
    
    // Rafraîchissement manuel
    const refreshBtn = document.getElementById('refresh-now');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', async () => {
            await data.loadGameContext();
            ui.showNotification('Data refreshed', 'info');
        });
    }
    
    // Intervalle de rafraîchissement
    const refreshIntervalInput = document.getElementById('refresh-interval');
    if (refreshIntervalInput) {
        refreshIntervalInput.addEventListener('change', (event) => {
            const newInterval = parseInt(event.target.value) * 1000; // Convertir en ms
            refresh.restartAutoRefresh(newInterval);
        });
    }
    
    // Gestion des onglets
    elements.tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabId = button.id;
            switchTab(tabId);
        });
    });
}

/**
 * Change l'onglet actif
 */
function switchTab(tabId) {
    // Mettre à jour l'état
    appState.activeTab = tabId;
    
    // Mettre à jour les classes des boutons d'onglet
    elements.tabButtons.forEach(button => {
        if (button.id === tabId) {
            button.classList.remove('border-transparent', 'text-gray-500');
            button.classList.add('border-monopoly-red', 'text-monopoly-red');
        } else {
            button.classList.remove('border-monopoly-red', 'text-monopoly-red');
            button.classList.add('border-transparent', 'text-gray-500');
        }
    });
    
    // Afficher le contenu de l'onglet correspondant
    const contentId = tabId.replace('-tab', '-content');
    elements.tabContents.forEach(content => {
        if (content.id === contentId) {
            content.classList.remove('hidden');
        } else {
            content.classList.add('hidden');
        }
    });
}

/**
 * Met à jour l'affichage du statut de Dolphin
 */
function updateDolphinStatus(running) {
    if (running) {
        elements.dolphinStatus.className = 'mb-4 p-3 bg-green-100 rounded-md text-green-700 flex items-center';
        elements.dolphinStatus.innerHTML = '<i class="fas fa-check-circle mr-2"></i><span>Dolphin est en cours d\'exécution</span>';
        elements.startDolphinBtn.disabled = true;
        elements.stopDolphinBtn.disabled = false;
        
        // Mettre à jour les classes des boutons
        elements.startDolphinBtn.classList.add('opacity-50', 'cursor-not-allowed');
        elements.stopDolphinBtn.classList.remove('opacity-50', 'cursor-not-allowed');
    } else {
        elements.dolphinStatus.className = 'mb-4 p-3 bg-gray-200 rounded-md text-gray-700 flex items-center';
        elements.dolphinStatus.innerHTML = '<i class="fas fa-info-circle mr-2"></i><span>Dolphin n\'est pas en cours d\'exécution</span>';
        elements.startDolphinBtn.disabled = false;
        elements.stopDolphinBtn.disabled = true;
        
        // Mettre à jour les classes des boutons
        elements.startDolphinBtn.classList.remove('opacity-50', 'cursor-not-allowed');
        elements.stopDolphinBtn.classList.add('opacity-50', 'cursor-not-allowed');
        
        // Réinitialiser l'affichage de la fenêtre Dolphin
        elements.dolphinContainer.innerHTML = `
            <div class="text-center text-gray-500">
                <i class="fas fa-desktop text-4xl mb-2"></i>
                <p>La fenêtre Dolphin s'affichera ici lorsque l'émulateur sera lancé.</p>
            </div>
        `;
        dolphinWindowCreated = false;
    }
}

/**
 * Met à jour l'affichage du statut de connexion
 */
function updateConnectionStatus(connected) {
    const statusDot = elements.connectionStatus.querySelector('span:first-child');
    const statusText = elements.connectionStatus.querySelector('span:last-child');
    
    if (connected) {
        statusDot.className = 'inline-block h-3 w-3 rounded-full bg-green-500 mr-2';
        statusText.textContent = 'Connecté';
    } else {
        statusDot.className = 'inline-block h-3 w-3 rounded-full bg-red-500 mr-2';
        statusText.textContent = 'Déconnecté';
    }
}

/**
 * Rafraîchit toutes les données
 */
async function refreshAll() {
    try {
        await Promise.all([
            refreshContext(),
            refreshTerminal()
        ]);
    } catch (error) {
        console.error('Erreur lors du rafraîchissement des données:', error);
    }
}

/**
 * Rafraîchit le contexte du jeu
 */
async function refreshContext() {
    try {
        const response = await fetch('/api/context');
        
        if (!response.ok) {
            if (response.status === 404) {
                // Le fichier de contexte n'existe pas encore
                updateConnectionStatus(false);
                return;
            }
            throw new Error(`Erreur HTTP: ${response.status}`);
        }
        
        const context = await response.json();
        
        appState.context = context;
        
        // Mettre à jour les différentes vues
        updateRawContext(context);
        updateEvents(context.events);
        updatePlayers(context.players);
        updateProperties(context.global.properties);
        updateBoard(context.board.spaces);
        
        // Mettre à jour les cartes de joueurs
        updatePlayerCards(context.players);
        
        // Mettre à jour le statut de connexion
        updateConnectionStatus(true);
    } catch (error) {
        console.error('Erreur lors du rafraîchissement du contexte:', error);
        updateConnectionStatus(false);
    }
}

/**
 * Rafraîchit la sortie du terminal
 */
async function refreshTerminal() {
    try {
        const response = await fetch('/api/terminal');
        const terminal = await response.json();
        
        appState.terminal = terminal;
        
        // Mettre à jour l'affichage du terminal
        elements.terminalOutput.textContent = terminal.join('\n');
        
        // Faire défiler vers le bas
        elements.terminalOutput.scrollTop = elements.terminalOutput.scrollHeight;
    } catch (error) {
        console.error('Erreur lors du rafraîchissement du terminal:', error);
    }
}

/**
 * Met à jour l'affichage du contexte brut
 */
function updateRawContext(context) {
    elements.rawContext.textContent = JSON.stringify(context, null, 2);
}

/**
 * Met à jour l'affichage des événements
 */
function updateEvents(events) {
    if (!events || !events.length) {
        elements.eventsContainer.innerHTML = '<p class="text-gray-500 text-center py-4">Aucun événement</p>';
        return;
    }
    
    const eventsList = document.createElement('ul');
    eventsList.className = 'divide-y divide-gray-200';
    
    events.forEach(event => {
        const eventItem = document.createElement('li');
        eventItem.className = 'py-3 hover:bg-gray-50 transition-colors';
        
        const eventHeader = document.createElement('div');
        eventHeader.className = 'flex items-center mb-1';
        
        const turnBadge = document.createElement('span');
        turnBadge.className = 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 mr-2';
        turnBadge.textContent = `Tour ${event.turn}`;
        eventHeader.appendChild(turnBadge);
        
        const playerName = document.createElement('span');
        playerName.className = 'font-medium text-gray-900';
        playerName.textContent = event.player;
        eventHeader.appendChild(playerName);
        
        const eventMessage = document.createElement('p');
        eventMessage.className = 'text-sm text-gray-600';
        eventMessage.textContent = event.message || `${event.action} ${event.detail || ''}`;
        
        eventItem.appendChild(eventHeader);
        eventItem.appendChild(eventMessage);
        
        eventsList.appendChild(eventItem);
    });
    
    elements.eventsContainer.innerHTML = '';
    elements.eventsContainer.appendChild(eventsList);
}

/**
 * Met à jour l'affichage des joueurs
 */
function updatePlayers(players) {
    if (!players || Object.keys(players).length === 0) {
        elements.playersDetailsContainer.innerHTML = '<p class="text-gray-500 text-center py-4">Aucun joueur</p>';
        return;
    }
    
    const table = document.createElement('table');
    table.className = 'min-w-full divide-y divide-gray-200';
    
    // En-tête du tableau
    const thead = document.createElement('thead');
    thead.className = 'bg-gray-50';
    const headerRow = document.createElement('tr');
    
    ['Nom', 'Argent', 'Position', 'Propriétés', 'En prison', 'Joueur actuel'].forEach(header => {
        const th = document.createElement('th');
        th.className = 'px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider';
        th.textContent = header;
        headerRow.appendChild(th);
    });
    
    thead.appendChild(headerRow);
    table.appendChild(thead);
    
    // Corps du tableau
    const tbody = document.createElement('tbody');
    tbody.className = 'bg-white divide-y divide-gray-200';
    
    let rowIndex = 0;
    Object.entries(players).forEach(([name, player]) => {
        const row = document.createElement('tr');
        row.className = rowIndex % 2 === 0 ? 'bg-white' : 'bg-gray-50';
        
        if (player.current_player) {
            row.classList.add('bg-blue-50');
        }
        
        // Nom
        const nameCell = document.createElement('td');
        nameCell.className = 'px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900';
        nameCell.textContent = name;
        row.appendChild(nameCell);
        
        // Argent
        const moneyCell = document.createElement('td');
        moneyCell.className = 'px-6 py-4 whitespace-nowrap text-sm text-gray-500';
        moneyCell.textContent = `${player.money}€`;
        row.appendChild(moneyCell);
        
        // Position
        const positionCell = document.createElement('td');
        positionCell.className = 'px-6 py-4 whitespace-nowrap text-sm text-gray-500';
        positionCell.textContent = player.current_space || `Case ${player.position}`;
        row.appendChild(positionCell);
        
        // Propriétés
        const propertiesCell = document.createElement('td');
        propertiesCell.className = 'px-6 py-4 whitespace-nowrap text-sm text-gray-500';
        
        if (player.properties && player.properties.length > 0) {
            const propCount = document.createElement('span');
            propCount.className = 'px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800';
            propCount.textContent = player.properties.length;
            propertiesCell.appendChild(propCount);
        } else {
            propertiesCell.textContent = 'Aucune';
        }
        
        row.appendChild(propertiesCell);
        
        // En prison
        const jailCell = document.createElement('td');
        jailCell.className = 'px-6 py-4 whitespace-nowrap text-sm text-gray-500';
        
        const jailBadge = document.createElement('span');
        jailBadge.className = player.jail 
            ? 'px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-red-100 text-red-800'
            : 'px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800';
        jailBadge.textContent = player.jail ? 'Oui' : 'Non';
        jailCell.appendChild(jailBadge);
        
        row.appendChild(jailCell);
        
        // Joueur actuel
        const currentPlayerCell = document.createElement('td');
        currentPlayerCell.className = 'px-6 py-4 whitespace-nowrap text-sm text-gray-500';
        
        const currentBadge = document.createElement('span');
        currentBadge.className = player.current_player 
            ? 'px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800'
            : 'px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-gray-100 text-gray-800';
        currentBadge.textContent = player.current_player ? 'Oui' : 'Non';
        currentPlayerCell.appendChild(currentBadge);
        
        row.appendChild(currentPlayerCell);
        
        tbody.appendChild(row);
        rowIndex++;
    });
    
    table.appendChild(tbody);
    
    elements.playersDetailsContainer.innerHTML = '';
    elements.playersDetailsContainer.appendChild(table);
}

/**
 * Met à jour l'affichage des propriétés
 */
function updateProperties(properties) {
    if (!properties || !properties.length) {
        elements.propertiesContainer.innerHTML = '<p class="text-gray-500 text-center py-4">Aucune propriété</p>';
        return;
    }
    
    const table = document.createElement('table');
    table.className = 'min-w-full divide-y divide-gray-200';
    
    // En-tête du tableau
    const thead = document.createElement('thead');
    thead.className = 'bg-gray-50';
    const headerRow = document.createElement('tr');
    
    ['ID', 'Nom', 'Groupe', 'Prix', 'Loyer', 'Propriétaire', 'Maisons'].forEach(header => {
        const th = document.createElement('th');
        th.className = 'px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider';
        th.textContent = header;
        headerRow.appendChild(th);
    });
    
    thead.appendChild(headerRow);
    table.appendChild(thead);
    
    // Corps du tableau
    const tbody = document.createElement('tbody');
    tbody.className = 'bg-white divide-y divide-gray-200';
    
    properties.forEach((property, index) => {
        const row = document.createElement('tr');
        row.className = index % 2 === 0 ? 'bg-white' : 'bg-gray-50';
        
        // ID
        const idCell = document.createElement('td');
        idCell.className = 'px-6 py-4 whitespace-nowrap text-sm text-gray-500';
        idCell.textContent = property.id;
        row.appendChild(idCell);
        
        // Nom
        const nameCell = document.createElement('td');
        nameCell.className = 'px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900';
        nameCell.textContent = property.name;
        row.appendChild(nameCell);
        
        // Groupe
        const groupCell = document.createElement('td');
        groupCell.className = 'px-6 py-4 whitespace-nowrap';
        
        const groupBadge = document.createElement('span');
        groupBadge.className = `px-2 inline-flex text-xs leading-5 font-semibold rounded-full color-${property.group}`;
        groupBadge.textContent = property.group;
        groupCell.appendChild(groupBadge);
        
        row.appendChild(groupCell);
        
        // Prix
        const priceCell = document.createElement('td');
        priceCell.className = 'px-6 py-4 whitespace-nowrap text-sm text-gray-500';
        priceCell.textContent = `${property.price}€`;
        row.appendChild(priceCell);
        
        // Loyer
        const rentCell = document.createElement('td');
        rentCell.className = 'px-6 py-4 whitespace-nowrap text-sm text-gray-500';
        
        if (property.rent && property.rent.length > 0) {
            rentCell.textContent = `${property.rent[0]}€`;
        } else {
            rentCell.textContent = '-';
        }
        
        row.appendChild(rentCell);
        
        // Propriétaire
        const ownerCell = document.createElement('td');
        ownerCell.className = 'px-6 py-4 whitespace-nowrap text-sm text-gray-500';
        
        if (property.owner) {
            const ownerBadge = document.createElement('span');
            ownerBadge.className = 'px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800';
            ownerBadge.textContent = property.owner;
            ownerCell.appendChild(ownerBadge);
        } else {
            ownerCell.textContent = 'Aucun';
        }
        
        row.appendChild(ownerCell);
        
        // Maisons
        const housesCell = document.createElement('td');
        housesCell.className = 'px-6 py-4 whitespace-nowrap text-sm text-gray-500';
        housesCell.textContent = property.houses || '0';
        row.appendChild(housesCell);
        
        tbody.appendChild(row);
    });
    
    table.appendChild(tbody);
    
    elements.propertiesContainer.innerHTML = '';
    elements.propertiesContainer.appendChild(table);
}

/**
 * Met à jour l'affichage du plateau
 */
function updateBoard(spaces) {
    if (!spaces || !spaces.length) {
        elements.boardContainer.innerHTML = '<p class="text-gray-500 text-center py-4">Aucune information sur le plateau</p>';
        return;
    }
    
    const boardDiv = document.createElement('div');
    boardDiv.className = 'board-container';
    
    // Créer une représentation visuelle du plateau
    spaces.forEach(space => {
        const spaceDiv = document.createElement('div');
        spaceDiv.className = 'board-space';
        
        if (space.id % 10 === 0) {
            spaceDiv.className += ' corner';
        }
        
        if (space.type === 'property' && space.property_ref !== null) {
            // Trouver la propriété correspondante
            const property = appState.context.global.properties.find(p => p.id === space.property_ref);
            if (property) {
                spaceDiv.className += ` color-${property.group}`;
            }
        }
        
        const nameDiv = document.createElement('div');
        nameDiv.className = 'font-bold text-xs';
        nameDiv.textContent = space.name;
        spaceDiv.appendChild(nameDiv);
        
        const idDiv = document.createElement('div');
        idDiv.textContent = `ID: ${space.id}`;
        idDiv.className = 'text-xs text-gray-500';
        spaceDiv.appendChild(idDiv);
        
        // Ajouter des marqueurs pour les joueurs sur cette case
        if (appState.context && appState.context.players) {
            let markerIndex = 0;
            Object.entries(appState.context.players).forEach(([name, player]) => {
                if (player.position === space.id) {
                    const playerMarker = document.createElement('div');
                    playerMarker.className = 'player-marker';
                    
                    // Positionner les marqueurs en cercle autour du centre
                    const angle = (markerIndex * (2 * Math.PI / 4)) % (2 * Math.PI);
                    const radius = 15;
                    const x = Math.cos(angle) * radius;
                    const y = Math.sin(angle) * radius;
                    
                    playerMarker.style.transform = `translate(${x}px, ${y}px)`;
                    
                    // Couleur du joueur
                    const colors = ['bg-red-500', 'bg-blue-500', 'bg-green-500', 'bg-yellow-500'];
                    playerMarker.className += ` ${colors[markerIndex % colors.length]}`;
                    
                    playerMarker.textContent = name.charAt(0);
                    playerMarker.title = name;
                    spaceDiv.appendChild(playerMarker);
                    
                    markerIndex++;
                }
            });
        }
        
        boardDiv.appendChild(spaceDiv);
    });
    
    elements.boardContainer.innerHTML = '';
    elements.boardContainer.appendChild(boardDiv);
}

/**
 * Met à jour les cartes de joueurs
 */
function updatePlayerCards(players) {
    if (!players || Object.keys(players).length === 0) {
        elements.playersContainer.innerHTML = '<p class="text-gray-500 text-center py-4">Aucun joueur</p>';
        return;
    }
    
    elements.playersContainer.innerHTML = '';
    
    Object.entries(players).forEach(([name, player]) => {
        const playerCol = document.createElement('div');
        playerCol.className = 'bg-white rounded-lg shadow overflow-hidden';
        
        // En-tête de la carte
        const cardHeader = document.createElement('div');
        cardHeader.className = player.current_player 
            ? 'bg-blue-500 text-white p-4' 
            : 'bg-gray-200 p-4';
        
        // Nom du joueur (éditable)
        const nameForm = document.createElement('div');
        nameForm.className = 'flex items-center justify-between';
        
        const nameInput = document.createElement('input');
        nameInput.type = 'text';
        nameInput.className = 'w-full bg-transparent border-b border-white focus:outline-none focus:border-blue-300 px-1 py-0.5 text-lg font-bold';
        nameInput.value = name;
        nameInput.dataset.playerId = player.id;
        nameInput.dataset.field = 'name';
        
        const saveNameBtn = document.createElement('button');
        saveNameBtn.className = 'ml-2 text-white bg-blue-600 hover:bg-blue-700 rounded-full w-6 h-6 flex items-center justify-center';
        saveNameBtn.innerHTML = '<i class="fas fa-check text-xs"></i>';
        saveNameBtn.addEventListener('click', () => updatePlayerField(player.id, 'name', nameInput.value));
        
        nameForm.appendChild(nameInput);
        nameForm.appendChild(saveNameBtn);
        
        cardHeader.appendChild(nameForm);
        playerCol.appendChild(cardHeader);
        
        // Corps de la carte
        const cardBody = document.createElement('div');
        cardBody.className = 'p-4';
        
        // Argent (éditable)
        const moneyDiv = document.createElement('div');
        moneyDiv.className = 'mb-4';
        
        const moneyLabel = document.createElement('label');
        moneyLabel.className = 'block text-sm font-medium text-gray-700 mb-1';
        moneyLabel.textContent = 'Argent:';
        
        const moneyInputGroup = document.createElement('div');
        moneyInputGroup.className = 'flex items-center';
        
        const moneyInput = document.createElement('input');
        moneyInput.type = 'number';
        moneyInput.className = 'flex-1 border-gray-300 focus:ring-blue-500 focus:border-blue-500 block w-full shadow-sm sm:text-sm border rounded-md p-2';
        moneyInput.value = player.money;
        moneyInput.min = 0;
        moneyInput.dataset.playerId = player.id;
        moneyInput.dataset.field = 'money';
        
        const saveMoneyBtn = document.createElement('button');
        saveMoneyBtn.className = 'ml-2 inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500';
        saveMoneyBtn.innerHTML = '<i class="fas fa-save mr-1"></i> Sauvegarder';
        saveMoneyBtn.addEventListener('click', () => updatePlayerField(player.id, 'money', moneyInput.value));
        
        moneyInputGroup.appendChild(moneyInput);
        moneyInputGroup.appendChild(saveMoneyBtn);
        
        moneyDiv.appendChild(moneyLabel);
        moneyDiv.appendChild(moneyInputGroup);
        
        // Position
        const positionDiv = document.createElement('div');
        positionDiv.className = 'mb-4';
        
        const positionLabel = document.createElement('div');
        positionLabel.className = 'block text-sm font-medium text-gray-700 mb-1';
        positionLabel.textContent = 'Position:';
        
        const positionValue = document.createElement('div');
        positionValue.className = 'bg-gray-100 p-2 rounded text-sm';
        positionValue.textContent = player.current_space || `Case ${player.position}`;
        
        positionDiv.appendChild(positionLabel);
        positionDiv.appendChild(positionValue);
        
        // Propriétés
        const propertiesDiv = document.createElement('div');
        propertiesDiv.className = 'mb-4';
        
        const propertiesLabel = document.createElement('div');
        propertiesLabel.className = 'block text-sm font-medium text-gray-700 mb-1';
        propertiesLabel.textContent = 'Propriétés:';
        
        const propertiesList = document.createElement('ul');
        propertiesList.className = 'bg-gray-100 rounded divide-y divide-gray-200';
        
        if (player.properties && player.properties.length > 0) {
            player.properties.forEach(propId => {
                const property = appState.context.global.properties.find(p => p.id === propId);
                if (property) {
                    const propItem = document.createElement('li');
                    propItem.className = 'px-2 py-1 text-sm flex items-center';
                    
                    const colorDot = document.createElement('span');
                    colorDot.className = `inline-block w-3 h-3 rounded-full mr-2 color-${property.group}`;
                    propItem.appendChild(colorDot);
                    
                    const propName = document.createElement('span');
                    propName.textContent = property.name;
                    propItem.appendChild(propName);
                    
                    propertiesList.appendChild(propItem);
                }
            });
        } else {
            const noPropItem = document.createElement('li');
            noPropItem.className = 'px-2 py-1 text-sm text-gray-500';
            noPropItem.textContent = 'Aucune propriété';
            propertiesList.appendChild(noPropItem);
        }
        
        propertiesDiv.appendChild(propertiesLabel);
        propertiesDiv.appendChild(propertiesList);
        
        // Statut de prison
        const jailDiv = document.createElement('div');
        jailDiv.className = 'mt-2';
        
        const jailBadge = document.createElement('span');
        if (player.jail) {
            jailBadge.className = 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800';
            jailBadge.innerHTML = '<i class="fas fa-jail mr-1"></i> En prison';
        } else {
            jailBadge.className = 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800';
            jailBadge.innerHTML = '<i class="fas fa-check-circle mr-1"></i> Libre';
        }
        
        jailDiv.appendChild(jailBadge);
        
        // Ajouter tous les éléments au corps de la carte
        cardBody.appendChild(moneyDiv);
        cardBody.appendChild(positionDiv);
        cardBody.appendChild(propertiesDiv);
        cardBody.appendChild(jailDiv);
        
        playerCol.appendChild(cardBody);
        
        elements.playersContainer.appendChild(playerCol);
    });
}

/**
 * Met à jour un champ d'un joueur
 */
async function updatePlayerField(playerId, field, value) {
    try {
        const response = await fetch('/api/players', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                id: playerId,
                [field]: value
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Rafraîchir les données
            refreshContext();
            showNotification(`Champ ${field} mis à jour avec succès!`, 'success');
        } else {
            showNotification(`Erreur: ${result.error}`, 'error');
        }
    } catch (error) {
        console.error('Erreur lors de la mise à jour du joueur:', error);
        showNotification('Erreur lors de la mise à jour du joueur', 'error');
    }
}

/**
 * Gère les paramètres de jeu
 */
async function loadGameSettings() {
    try {
        const response = await fetch('/api/game-settings');
        if (response.ok) {
            const settings = await response.json();
            
            // Mettre à jour les champs du formulaire
            if (elements.player1Name) elements.player1Name.value = settings.players.player1.name;
            if (elements.player1Model) elements.player1Model.value = settings.players.player1.model;
            if (elements.player2Name) elements.player2Name.value = settings.players.player2.name;
            if (elements.player2Model) elements.player2Model.value = settings.players.player2.model;
            if (elements.aiEnabled) elements.aiEnabled.checked = settings.game.ai_enabled;
        }
    } catch (error) {
        console.error('Error loading game settings:', error);
    }
}

async function saveGameSettings() {
    try {
        const settings = {
            players: {
                player1: {
                    name: elements.player1Name.value,
                    model: elements.player1Model.value,
                    enabled: true
                },
                player2: {
                    name: elements.player2Name.value,
                    model: elements.player2Model.value,
                    enabled: true
                }
            },
            game: {
                player_count: 2,
                ai_enabled: elements.aiEnabled.checked,
                default_model: 'gpt-4.1-mini'
            }
        };
        
        const response = await fetch('/api/game-settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        });
        
        if (response.ok) {
            ui.showNotification('Game settings saved successfully!', 'success');
            elements.gameSettingsModal.classList.add('hidden');
        } else {
            const error = await response.json();
            ui.showNotification(`Error: ${error.error}`, 'error');
        }
    } catch (error) {
        console.error('Error saving game settings:', error);
        ui.showNotification('Failed to save settings', 'error');
    }
}

// Ajouter les événements pour le modal des paramètres
document.addEventListener('DOMContentLoaded', () => {
    // Ouvrir le modal
    if (elements.gameSettingsBtn) {
        elements.gameSettingsBtn.addEventListener('click', () => {
            loadGameSettings();
            elements.gameSettingsModal.classList.remove('hidden');
        });
    }
    
    // Fermer le modal
    if (elements.closeGameSettings) {
        elements.closeGameSettings.addEventListener('click', () => {
            elements.gameSettingsModal.classList.add('hidden');
        });
    }
    
    if (elements.cancelGameSettings) {
        elements.cancelGameSettings.addEventListener('click', () => {
            elements.gameSettingsModal.classList.add('hidden');
        });
    }
    
    // Sauvegarder les paramètres
    if (elements.saveGameSettings) {
        elements.saveGameSettings.addEventListener('click', saveGameSettings);
    }
    
    // Charger les paramètres au démarrage
    loadGameSettings();
});

// Exporter les modules pour un accès global (utile pour le débogage)
window.monopolyManager = {
    config,
    ui,
    dolphin,
    data,
    refresh,
    admin,
    gameSettings: {
        load: loadGameSettings,
        save: saveGameSettings
    }
}; 