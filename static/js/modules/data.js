/**
 * Module de gestion des données
 * Gère le chargement et l'affichage des données du jeu
 */

// État des données
let state = {
    gameContext: null,
    lastUpdateTime: null
};

/**
 * Charge les données du contexte du jeu
 */
async function loadGameContext() {
    try {
        console.log('Fetching game context from /api/context...');
        const response = await fetch('/api/context');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Game context received:', data);
        state.gameContext = data;
        state.lastUpdateTime = new Date();
        
        // Mettre à jour l'interface avec les nouvelles données
        updateGameDisplay(data);
        
        return data;
    } catch (error) {
        console.error('Error loading game context:', error);
        return null;
    }
}

/**
 * Met à jour l'affichage du jeu avec les données du contexte
 */
function updateGameDisplay(gameContext) {
    if (!gameContext) {
        console.error('No game context data to display');
        return;
    }
    
    console.log('Updating game display with context:', gameContext);
    
    // Mettre à jour les informations globales
    updateGlobalInfo(gameContext.global);
    
    // Mettre à jour les événements
    updateEvents(gameContext.events);
    
    // Mettre à jour les informations des joueurs
    updatePlayers(gameContext.players);
    
    // Mettre à jour le plateau
    updateBoard(gameContext.board);
}

/**
 * Met à jour les informations globales du jeu
 */
function updateGlobalInfo(globalInfo) {
    if (!globalInfo) {
        console.error('No global info to update');
        return;
    }
    
    console.log('Updating global info:', globalInfo);
    
    const globalInfoContainer = document.getElementById('global-info');
    if (!globalInfoContainer) {
        console.error('Global info container not found');
        return;
    }
    
    // Formater les informations globales
    const turnInfo = document.getElementById('turn-info');
    if (turnInfo) {
        // Vérifier si turn_number existe, sinon utiliser current_turn
        const turnNumber = globalInfo.turn_number !== undefined ? globalInfo.turn_number : globalInfo.current_turn;
        turnInfo.textContent = `Turn ${turnNumber || 0}`;
    } else {
        console.error('Turn info element not found');
    }
    
    const currentPlayerInfo = document.getElementById('current-player');
    if (currentPlayerInfo) {
        // Vérifier si current_player existe, sinon utiliser le premier joueur actif
        let currentPlayer = globalInfo.current_player;
        if (!currentPlayer && globalInfo.player_names && globalInfo.player_names.length > 0) {
            currentPlayer = globalInfo.player_names[0];
        }
        
        currentPlayerInfo.textContent = currentPlayer || 'No player';
        
        // Mettre à jour la couleur en fonction du joueur actuel
        const playerColors = {
            'Player 1': 'text-blue-400',
            'Player 2': 'text-red-400',
            'Player 3': 'text-green-400',
            'Player 4': 'text-yellow-400'
        };
        
        // Réinitialiser les classes de couleur
        Object.values(playerColors).forEach(colorClass => {
            currentPlayerInfo.classList.remove(colorClass);
        });
        
        // Ajouter la classe de couleur correspondante
        if (playerColors[currentPlayer]) {
            currentPlayerInfo.classList.add(playerColors[currentPlayer]);
        }
    } else {
        console.error('Current player info element not found');
    }
}

/**
 * Met à jour la liste des événements
 */
function updateEvents(events) {
    if (!events || !Array.isArray(events)) {
        console.error('No events or events is not an array:', events);
        return;
    }
    
    console.log('Updating events:', events);
    
    const eventsContainer = document.getElementById('events-list');
    if (!eventsContainer) {
        console.error('Events container not found');
        return;
    }
    
    // Vider le conteneur
    eventsContainer.innerHTML = '';
    
    // Ajouter chaque événement
    events.forEach(event => {
        const eventItem = document.createElement('div');
        eventItem.className = 'mb-2 p-2 bg-gray-800/50 rounded-md border border-gray-700 text-sm';
        
        // Déterminer l'icône en fonction du type d'événement
        let icon = 'fa-info-circle text-blue-400';
        if (event.action && typeof event.action === 'string') {
            if (event.action.includes('dice')) {
                icon = 'fa-dice text-purple-400';
            } else if (event.action.includes('buy') || event.action.includes('purchase')) {
                icon = 'fa-shopping-cart text-green-400';
            } else if (event.action.includes('pay') || event.action.includes('rent')) {
                icon = 'fa-money-bill-wave text-yellow-400';
            } else if (event.action.includes('move') || event.action.includes('goto')) {
                icon = 'fa-walking text-blue-400';
            } else if (event.action.includes('jail')) {
                icon = 'fa-jail text-red-400';
            }
        }
        
        // Créer le contenu de l'événement
        const message = event.message || `${event.player || 'Unknown'} performed action: ${event.action || 'unknown'}`;
        const turn = event.turn || '?';
        const player = event.player || 'Unknown';
        
        eventItem.innerHTML = `
            <div class="flex items-start">
                <i class="fas ${icon} mt-1 mr-2"></i>
                <div class="flex-1">
                    <div class="text-gray-300">${message}</div>
                    <div class="text-xs text-gray-500 mt-1">
                        <span>Turn ${turn}</span>
                        <span class="mx-1">•</span>
                        <span>${player}</span>
                    </div>
                </div>
            </div>
        `;
        
        eventsContainer.appendChild(eventItem);
    });
    
    // Si aucun événement, afficher un message
    if (events.length === 0) {
        const noEvents = document.createElement('div');
        noEvents.className = 'text-center text-gray-500 py-4';
        noEvents.textContent = 'No events yet';
        eventsContainer.appendChild(noEvents);
    }
}

/**
 * Met à jour les informations des joueurs
 */
function updatePlayers(players) {
    if (!players) {
        console.error('No players data to update');
        return;
    }
    
    console.log('Updating players:', players);
    
    // Mettre à jour la liste des joueurs dans la section principale
    const playersContainer = document.getElementById('players-container');
    if (playersContainer) {
        // Vider le conteneur
        playersContainer.innerHTML = '';
        
        // Ajouter chaque joueur
        Object.entries(players).forEach(([playerName, playerData]) => {
            const playerItem = document.createElement('div');
            playerItem.className = 'mb-3 p-3 bg-gray-800/50 rounded-md border border-gray-700';
            
            // Déterminer la couleur du joueur
            const playerColors = {
                'Player 1': 'border-blue-500 bg-blue-900/20',
                'Player 2': 'border-red-500 bg-red-900/20',
                'Player 3': 'border-green-500 bg-green-900/20',
                'Player 4': 'border-yellow-500 bg-yellow-900/20'
            };
            
            if (playerColors[playerName]) {
                playerItem.className = `mb-3 p-3 rounded-md border ${playerColors[playerName]}`;
            }
            
            // Créer le contenu du joueur
            const money = playerData.money !== undefined ? playerData.money : 0;
            const position = playerData.position !== undefined ? playerData.position : 0;
            const lastDice = playerData.dice_result ? playerData.dice_result.join(', ') : '-';
            
            playerItem.innerHTML = `
                <div class="flex justify-between items-center mb-2">
                    <h3 class="font-medium text-gray-200">${playerName}</h3>
                    <span class="text-sm bg-gray-700 px-2 py-0.5 rounded-full text-gray-300">$${money}</span>
                </div>
                <div class="grid grid-cols-2 gap-2 text-xs">
                    <div class="flex items-center text-gray-400">
                        <i class="fas fa-map-marker-alt mr-1.5"></i>
                        <span>Position: ${position}</span>
                    </div>
                    <div class="flex items-center text-gray-400">
                        <i class="fas fa-dice mr-1.5"></i>
                        <span>Last roll: ${lastDice}</span>
                    </div>
                </div>
                ${playerData.properties && playerData.properties.length > 0 ? `
                    <div class="mt-2 pt-2 border-t border-gray-700">
                        <h4 class="text-xs text-gray-400 mb-1.5">Properties:</h4>
                        <div class="flex flex-wrap gap-1">
                            ${playerData.properties.map(property => {
                                // Si property est un objet, utiliser ses propriétés, sinon c'est juste un ID
                                const propertyName = typeof property === 'object' ? property.name : `Property ${property}`;
                                const propertyColor = typeof property === 'object' ? property.color : 'gray';
                                
                                // Déterminer la couleur de la propriété
                                const propertyColors = {
                                    'brown': 'bg-amber-800',
                                    'light_blue': 'bg-sky-400',
                                    'pink': 'bg-pink-500',
                                    'orange': 'bg-orange-500',
                                    'red': 'bg-red-500',
                                    'yellow': 'bg-yellow-400',
                                    'green': 'bg-green-500',
                                    'blue': 'bg-blue-600',
                                    'railroad': 'bg-gray-600',
                                    'utility': 'bg-gray-400'
                                };
                                
                                const bgColor = propertyColors[propertyColor] || 'bg-gray-600';
                                
                                return `<span class="px-1.5 py-0.5 rounded ${bgColor} text-white text-xs">${propertyName}</span>`;
                            }).join('')}
                        </div>
                    </div>
                ` : ''}
            `;
            
            playersContainer.appendChild(playerItem);
        });
        
        // Si aucun joueur, afficher un message
        if (Object.keys(players).length === 0) {
            const noPlayers = document.createElement('div');
            noPlayers.className = 'text-center text-gray-500 py-4';
            noPlayers.textContent = 'No players yet';
            playersContainer.appendChild(noPlayers);
        }
    } else {
        console.error('Players container not found');
    }
    
    // Mettre à jour les détails des joueurs dans l'onglet Players
    const playersListContainer = document.getElementById('players-list');
    if (playersListContainer) {
        // Vider le conteneur
        playersListContainer.innerHTML = '';
        
        // Ajouter chaque joueur
        Object.entries(players).forEach(([playerName, playerData]) => {
            const playerItem = document.createElement('div');
            playerItem.className = 'mb-3 p-3 bg-gray-800/50 rounded-md border border-gray-700';
            
            // Déterminer la couleur du joueur
            const playerColors = {
                'Player 1': 'border-blue-500 bg-blue-900/20',
                'Player 2': 'border-red-500 bg-red-900/20',
                'Player 3': 'border-green-500 bg-green-900/20',
                'Player 4': 'border-yellow-500 bg-yellow-900/20'
            };
            
            if (playerColors[playerName]) {
                playerItem.className = `mb-3 p-3 rounded-md border ${playerColors[playerName]}`;
            }
            
            // Créer le contenu du joueur avec plus de détails
            const money = playerData.money !== undefined ? playerData.money : 0;
            const position = playerData.position !== undefined ? playerData.position : 0;
            const currentSpace = playerData.current_space || 'Unknown';
            const lastDice = playerData.dice_result ? playerData.dice_result.join(', ') : '-';
            const inJail = playerData.jail ? 'Yes' : 'No';
            
            playerItem.innerHTML = `
                <div class="flex justify-between items-center mb-2">
                    <h3 class="font-medium text-gray-200">${playerName}</h3>
                    <span class="text-sm bg-gray-700 px-2 py-0.5 rounded-full text-gray-300">$${money}</span>
                </div>
                <div class="grid grid-cols-2 gap-2 text-xs">
                    <div class="flex items-center text-gray-400">
                        <i class="fas fa-map-marker-alt mr-1.5"></i>
                        <span>Position: ${position} (${currentSpace})</span>
                    </div>
                    <div class="flex items-center text-gray-400">
                        <i class="fas fa-dice mr-1.5"></i>
                        <span>Last roll: ${lastDice}</span>
                    </div>
                    <div class="flex items-center text-gray-400">
                        <i class="fas fa-jail mr-1.5"></i>
                        <span>In jail: ${inJail}</span>
                    </div>
                    <div class="flex items-center text-gray-400">
                        <i class="fas fa-home mr-1.5"></i>
                        <span>Properties: ${playerData.properties ? playerData.properties.length : 0}</span>
                    </div>
                </div>
                ${playerData.properties && playerData.properties.length > 0 ? `
                    <div class="mt-2 pt-2 border-t border-gray-700">
                        <h4 class="text-xs text-gray-400 mb-1.5">Properties:</h4>
                        <div class="flex flex-wrap gap-1">
                            ${playerData.properties.map(property => {
                                // Si property est un objet, utiliser ses propriétés, sinon c'est juste un ID
                                const propertyName = typeof property === 'object' ? property.name : `Property ${property}`;
                                const propertyColor = typeof property === 'object' ? property.color : 'gray';
                                
                                // Déterminer la couleur de la propriété
                                const propertyColors = {
                                    'brown': 'bg-amber-800',
                                    'light_blue': 'bg-sky-400',
                                    'pink': 'bg-pink-500',
                                    'orange': 'bg-orange-500',
                                    'red': 'bg-red-500',
                                    'yellow': 'bg-yellow-400',
                                    'green': 'bg-green-500',
                                    'blue': 'bg-blue-600',
                                    'railroad': 'bg-gray-600',
                                    'utility': 'bg-gray-400'
                                };
                                
                                const bgColor = propertyColors[propertyColor] || 'bg-gray-600';
                                
                                return `<span class="px-1.5 py-0.5 rounded ${bgColor} text-white text-xs">${propertyName}</span>`;
                            }).join('')}
                        </div>
                    </div>
                ` : ''}
            `;
            
            playersListContainer.appendChild(playerItem);
        });
        
        // Si aucun joueur, afficher un message
        if (Object.keys(players).length === 0) {
            const noPlayers = document.createElement('div');
            noPlayers.className = 'text-center text-gray-500 py-4';
            noPlayers.textContent = 'No players yet';
            playersListContainer.appendChild(noPlayers);
        }
    }
}

/**
 * Met à jour l'affichage du plateau
 */
function updateBoard(board) {
    if (!board) {
        console.error('No board data to update');
        return;
    }
    
    console.log('Updating board:', board);
    
    const boardContainer = document.getElementById('board-spaces');
    if (!boardContainer) {
        console.error('Board container not found');
        return;
    }
    
    // Vider le conteneur
    boardContainer.innerHTML = '';
    
    // Si board est un objet avec une propriété spaces, utiliser cette propriété
    const spaces = Array.isArray(board) ? board : (board.spaces || []);
    
    // Ajouter chaque case du plateau
    spaces.forEach(space => {
        const spaceItem = document.createElement('div');
        spaceItem.className = 'p-2 bg-gray-800/50 rounded-md border border-gray-700 text-xs';
        
        // Déterminer l'icône en fonction du type d'espace
        let icon = 'fa-square text-gray-400';
        if (space.type === 'property') {
            icon = 'fa-home text-blue-400';
        } else if (space.type === 'railroad') {
            icon = 'fa-train text-gray-400';
        } else if (space.type === 'utility') {
            icon = 'fa-lightbulb text-yellow-400';
        } else if (space.type === 'tax') {
            icon = 'fa-hand-holding-usd text-red-400';
        } else if (space.type === 'chance') {
            icon = 'fa-question-circle text-orange-400';
        } else if (space.type === 'community_chest') {
            icon = 'fa-treasure-chest text-purple-400';
        } else if (space.type === 'go') {
            icon = 'fa-arrow-right text-green-400';
        } else if (space.type === 'jail') {
            icon = 'fa-jail text-red-400';
        } else if (space.type === 'free_parking') {
            icon = 'fa-parking text-blue-400';
        } else if (space.type === 'go_to_jail') {
            icon = 'fa-gavel text-red-400';
        }
        
        // Créer le contenu de l'espace
        spaceItem.innerHTML = `
            <div class="flex items-start">
                <i class="fas ${icon} mt-0.5 mr-1.5"></i>
                <div class="flex-1">
                    <div class="text-gray-300 font-medium">${space.name}</div>
                    ${space.type === 'property' ? `
                        <div class="flex items-center mt-1">
                            <span class="w-3 h-3 rounded-full ${getColorClass(space.color)} mr-1.5"></span>
                            <span class="text-gray-400">${space.price ? '$' + space.price : ''}</span>
                        </div>
                    ` : ''}
                    ${space.owner ? `
                        <div class="text-gray-400 mt-1">Owner: ${space.owner}</div>
                    ` : ''}
                </div>
            </div>
        `;
        
        boardContainer.appendChild(spaceItem);
    });
    
    // Si aucun espace, afficher un message
    if (spaces.length === 0) {
        const noSpaces = document.createElement('div');
        noSpaces.className = 'text-center text-gray-500 py-4';
        noSpaces.textContent = 'Board data not available';
        boardContainer.appendChild(noSpaces);
    }
    
    // Mettre à jour l'affichage du JSON brut
    const rawContext = document.getElementById('raw-context');
    if (rawContext && state.gameContext) {
        rawContext.textContent = JSON.stringify(state.gameContext, null, 2);
    }
}

/**
 * Obtient la classe de couleur CSS pour une couleur de propriété
 */
function getColorClass(color) {
    const colorClasses = {
        'brown': 'bg-amber-800',
        'light_blue': 'bg-sky-400',
        'pink': 'bg-pink-500',
        'orange': 'bg-orange-500',
        'red': 'bg-red-500',
        'yellow': 'bg-yellow-400',
        'green': 'bg-green-500',
        'blue': 'bg-blue-600',
        'railroad': 'bg-gray-600',
        'utility': 'bg-gray-400'
    };
    
    return colorClasses[color] || 'bg-gray-600';
}

const data = {
    async getGameContext() {
        try {
            const response = await fetch('/api/context');
            return await response.json();
        } catch (error) {
            console.error('Error fetching game context:', error);
            return null;
        }
    }
};

export default data; 