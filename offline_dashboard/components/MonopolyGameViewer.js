import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { MessageSquare, DollarSign, Home, Building2, TrendingUp, AlertCircle, BarChart3, Download } from 'lucide-react';
import Navbar from './Navbar';
import AnimatedStats from './AnimatedStats';

const MonopolyGameViewer = () => {
  const [gameData, setGameData] = useState(null);
  const [selectedTurn, setSelectedTurn] = useState(0);
  const [activeTab, setActiveTab] = useState('evolution');
  const [animatedData, setAnimatedData] = useState([]);
  const [isAnimating, setIsAnimating] = useState(false);
  const [currentFile, setCurrentFile] = useState(null);

  // Charger la liste des fichiers au démarrage
  useEffect(() => {
    const loadFirstFile = async () => {
      try {
        const response = await fetch('/api/list-logs');
        const data = await response.json();
        if (data.files && data.files.length > 0) {
          setCurrentFile(data.files[0].name);
        }
      } catch (error) {
        console.error('Erreur lors du chargement de la liste des fichiers:', error);
      }
    };
    loadFirstFile();
  }, []);

  // Charger les données du fichier
  useEffect(() => {
    if (!currentFile) return; // Ne pas charger si aucun fichier n'est sélectionné
    
    const loadGameData = async () => {
      try {
        const response = await fetch(`/api/game-logs?file=${currentFile}`);
        if (!response.ok) {
          console.error('Error response:', response.status, response.statusText);
          return;
        }
        const data = await response.json();
        console.log('Loaded data type:', typeof data, 'Is array:', Array.isArray(data));
        setGameData(data);
        processGameData(data);
      } catch (error) {
        console.error('Erreur lors du chargement des données:', error);
      }
    };
    loadGameData();
    
    // Recharger les données toutes les 5 secondes
    const interval = setInterval(loadGameData, 5000);
    return () => clearInterval(interval);
  }, [currentFile]);

  // Traiter les données pour créer l'évolution tour par tour
  const processGameData = (data) => {
    if (!data || !Array.isArray(data)) {
      console.error('Invalid game data:', data);
      return;
    }
    
    const evolution = [];
    const turnData = {};

    data.forEach((log, index) => {
      const turn = log.game_context.global.current_turn;
      const players = log.game_context.players;
      
      if (!turnData[turn]) {
        turnData[turn] = {
          turn,
          player1_name: players.player1.name,
          player2_name: players.player2.name,
          player1_money: players.player1.money,
          player2_money: players.player2.money,
          player1_properties: players.player1.properties.length,
          player2_properties: players.player2.properties.length,
          player1_mortgaged: countMortgaged(players.player1.properties),
          player2_mortgaged: countMortgaged(players.player2.properties),
          player1_houses: countHouses(players.player1.properties),
          player2_houses: countHouses(players.player2.properties),
          // Keep legacy fields for backward compatibility
          GPT_money: players.player1.money,
          Gemini_money: players.player2.money,
          GPT_properties: players.player1.properties.length,
          Gemini_properties: players.player2.properties.length,
          GPT_mortgaged: countMortgaged(players.player1.properties),
          Gemini_mortgaged: countMortgaged(players.player2.properties),
          GPT_houses: countHouses(players.player1.properties),
          Gemini_houses: countHouses(players.player2.properties),
          events: log.game_context.events.filter(e => e.turn === turn),
          chat: log.chat_messages || [],
          decisions: log.result ? [{
            player: log.player_name,
            decision: log.result.decision,
            reason: log.result.reason,
            confidence: log.result.confidence
          }] : []
        };
      } else {
        // Ajouter les messages de chat et décisions supplémentaires
        if (log.chat_messages) {
          turnData[turn].chat = [...turnData[turn].chat, ...log.chat_messages];
        }
        if (log.result) {
          turnData[turn].decisions.push({
            player: log.player_name,
            decision: log.result.decision,
            reason: log.result.reason,
            confidence: log.result.confidence
          });
        }
      }
    });

    const sortedData = Object.values(turnData).sort((a, b) => a.turn - b.turn);
    setAnimatedData(sortedData);
  };

  const countHouses = (properties) => {
    return properties.reduce((sum, prop) => sum + (prop.houses || 0), 0);
  };

  const countMortgaged = (properties) => {
    return properties.filter(prop => prop.is_mortgaged === true).length;
  };

  // Animation des données
  const startAnimation = () => {
    setIsAnimating(true);
    let index = 0;
    const interval = setInterval(() => {
      if (index >= animatedData.length - 1) {
        clearInterval(interval);
        setIsAnimating(false);
      } else {
        index++;
        setSelectedTurn(index);
      }
    }, 1000);
  };

  if (!gameData || animatedData.length === 0) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-100">
        <div className="text-center">
          <AlertCircle className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <p className="text-lg text-gray-600">Chargement des données de jeu...</p>
        </div>
      </div>
    );
  }

  const currentTurnData = animatedData[selectedTurn] || animatedData[0];

  const handleFileSelect = (filename) => {
    setCurrentFile(filename);
    setSelectedTurn(0); // Reset to first turn when changing files
  };

  const exportDecisions = async () => {
    try {
      const response = await fetch('/api/export-decisions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sourceFile: currentFile
        }),
      });

      if (response.ok) {
        const result = await response.json();
        alert(`Décisions exportées avec succès dans: ${result.path}`);
      } else {
        const error = await response.json();
        alert(`Erreur lors de l'export: ${error.error || 'Erreur inconnue'}`);
      }
    } catch (error) {
      console.error('Erreur lors de l\'export:', error);
      alert('Erreur lors de l\'export des décisions');
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar onFileSelect={handleFileSelect} currentFile={currentFile} />
      <div className="p-4">
        <div className="max-w-7xl mx-auto">
          <header className="bg-white rounded-lg shadow-md p-6 mb-6">
            <h1 className="text-3xl font-bold text-gray-800 mb-2">
              Visualiseur de Partie Monopoly IA
            </h1>
            <p className="text-gray-600">GPT vs Gemini - Analyse de la partie</p>
            <p className="text-sm text-gray-500 mt-2">Fichier actuel: {currentFile}</p>
          </header>

          {/* Contrôles */}
          <div className="bg-white rounded-lg shadow-md p-4 mb-6">
            <div className="flex items-center justify-between">
              <div className="flex gap-4">
                <button
                  onClick={() => setActiveTab('evolution')}
                  className={`px-4 py-2 rounded-lg transition-colors ${
                    activeTab === 'evolution' 
                      ? 'bg-blue-500 text-white' 
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                >
                  <TrendingUp className="inline-block w-4 h-4 mr-2" />
                  Évolution
                </button>
                <button
                  onClick={() => setActiveTab('chat')}
                  className={`px-4 py-2 rounded-lg transition-colors ${
                    activeTab === 'chat' 
                      ? 'bg-blue-500 text-white' 
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                >
                  <MessageSquare className="inline-block w-4 h-4 mr-2" />
                  Chat & Décisions
                </button>
                <button
                  onClick={() => setActiveTab('animation')}
                  className={`px-4 py-2 rounded-lg transition-colors ${
                    activeTab === 'animation' 
                      ? 'bg-blue-500 text-white' 
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                >
                  <BarChart3 className="inline-block w-4 h-4 mr-2" />
                  Animation
                </button>
              </div>
              <button
                onClick={startAnimation}
                disabled={isAnimating}
                className={`px-6 py-2 rounded-lg transition-colors ${
                  isAnimating 
                    ? 'bg-gray-400 text-gray-200 cursor-not-allowed' 
                    : 'bg-green-500 text-white hover:bg-green-600'
                }`}
              >
                {isAnimating ? 'Animation en cours...' : 'Démarrer l\'animation'}
              </button>
            </div>
          </div>

          {/* Statistiques actuelles */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div className="bg-white rounded-lg shadow-md p-6">
              <h3 className="text-xl font-semibold text-gray-800 mb-4">{currentTurnData.player1_name} (Bleu)</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="flex items-center text-gray-600">
                    <DollarSign className="w-4 h-4 mr-2" />
                    Argent
                  </span>
                  <span className="text-2xl font-bold text-blue-600">
                    {currentTurnData.player1_money}€
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="flex items-center text-gray-600">
                    <Building2 className="w-4 h-4 mr-2" />
                    Propriétés
                  </span>
                  <span className="text-2xl font-bold text-blue-600">
                    {currentTurnData.player1_properties}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="flex items-center text-gray-600">
                    <Home className="w-4 h-4 mr-2" />
                    Maisons
                  </span>
                  <span className="text-2xl font-bold text-blue-600">
                    {currentTurnData.player1_houses}
                  </span>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-md p-6">
              <h3 className="text-xl font-semibold text-gray-800 mb-4">{currentTurnData.player2_name} (Rouge)</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="flex items-center text-gray-600">
                    <DollarSign className="w-4 h-4 mr-2" />
                    Argent
                  </span>
                  <span className="text-2xl font-bold text-red-600">
                    {currentTurnData.player2_money}€
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="flex items-center text-gray-600">
                    <Building2 className="w-4 h-4 mr-2" />
                    Propriétés
                  </span>
                  <span className="text-2xl font-bold text-red-600">
                    {currentTurnData.player2_properties}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="flex items-center text-gray-600">
                    <Home className="w-4 h-4 mr-2" />
                    Maisons
                  </span>
                  <span className="text-2xl font-bold text-red-600">
                    {currentTurnData.player2_houses}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Contenu principal */}
          {activeTab === 'evolution' && (
            <div className="space-y-6">
              {/* Graphique de l'argent */}
              <div className="bg-white rounded-lg shadow-md p-6">
                <h3 className="text-xl font-semibold text-gray-800 mb-4">
                  Évolution de l'argent
                </h3>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={animatedData.slice(0, selectedTurn + 1)}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="turn" label={{ value: 'Tour', position: 'insideBottom', offset: -5 }} />
                    <YAxis label={{ value: 'Argent (€)', angle: -90, position: 'insideLeft' }} />
                    <Tooltip />
                    <Legend />
                    <Line 
                      type="monotone" 
                      dataKey="player1_money" 
                      stroke="#3b82f6" 
                      strokeWidth={2}
                      name={animatedData[0]?.player1_name || 'Player 1'}
                      animationDuration={500}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="player2_money" 
                      stroke="#ef4444" 
                      strokeWidth={2}
                      name={animatedData[0]?.player2_name || 'Player 2'}
                      animationDuration={500}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* Graphique des propriétés */}
              <div className="bg-white rounded-lg shadow-md p-6">
                <h3 className="text-xl font-semibold text-gray-800 mb-4">
                  Nombre de propriétés et maisons
                </h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={animatedData.slice(0, selectedTurn + 1)}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="turn" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="player1_properties" fill="#3b82f6" name={`Propriétés ${animatedData[0]?.player1_name || 'Player 1'}`} />
                    <Bar dataKey="player2_properties" fill="#ef4444" name={`Propriétés ${animatedData[0]?.player2_name || 'Player 2'}`} />
                    <Bar dataKey="player1_houses" fill="#1e40af" name={`Maisons ${animatedData[0]?.player1_name || 'Player 1'}`} />
                    <Bar dataKey="player2_houses" fill="#991b1b" name={`Maisons ${animatedData[0]?.player2_name || 'Player 2'}`} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Contrôle du tour */}
              <div className="bg-white rounded-lg shadow-md p-6">
                <h3 className="text-xl font-semibold text-gray-800 mb-4">
                  Navigation dans les tours
                </h3>
                <input
                  type="range"
                  min="0"
                  max={animatedData.length - 1}
                  value={selectedTurn}
                  onChange={(e) => setSelectedTurn(parseInt(e.target.value))}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
                <div className="mt-2 text-center text-gray-600">
                  Tour {currentTurnData.turn} sur {animatedData[animatedData.length - 1].turn}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'animation' && (
            <AnimatedStats animatedData={animatedData} />
          )}

          {activeTab === 'chat' && (
            <div className="bg-white rounded-lg shadow-md p-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-xl font-semibold text-gray-800">
                  Chat & Décisions - Tour {currentTurnData.turn}
                </h3>
                <button
                  onClick={() => exportDecisions()}
                  className="px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg transition-colors flex items-center space-x-2"
                >
                  <Download size={20} />
                  <span>Exporter les décisions</span>
                </button>
              </div>
              
              {/* Messages de chat */}
              <div className="mb-6">
                <h4 className="font-semibold text-gray-700 mb-3">Messages du chat</h4>
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {currentTurnData.chat.length > 0 ? (
                    currentTurnData.chat.map((msg, idx) => (
                      <div key={idx} className="p-3 bg-gray-50 rounded-lg">
                        <p className="text-sm text-gray-800">{msg}</p>
                      </div>
                    ))
                  ) : (
                    <p className="text-gray-500 italic">Aucun message pour ce tour</p>
                  )}
                </div>
              </div>

              {/* Décisions des IA */}
              <div className="mb-6">
                <h4 className="font-semibold text-gray-700 mb-3">Décisions des IA</h4>
                <div className="space-y-3">
                  {currentTurnData.decisions.length > 0 ? (
                    currentTurnData.decisions.map((decision, idx) => (
                      <div key={idx} className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                        <div className="flex justify-between items-start mb-2">
                          <span className="font-semibold text-blue-800">{decision.player}</span>
                          <span className="text-sm bg-blue-200 text-blue-800 px-2 py-1 rounded">
                            Confiance: {decision.confidence}
                          </span>
                        </div>
                        <p className="text-gray-700 mb-2">
                          <strong>Décision:</strong> {decision.decision}
                        </p>
                        <p className="text-sm text-gray-600 italic">
                          <strong>Raison:</strong> {decision.reason}
                        </p>
                      </div>
                    ))
                  ) : (
                    <p className="text-gray-500 italic">Aucune décision pour ce tour</p>
                  )}
                </div>
              </div>

              {/* Événements du tour */}
              <div>
                <h4 className="font-semibold text-gray-700 mb-3">Événements du tour</h4>
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {currentTurnData.events.length > 0 ? (
                    currentTurnData.events.map((event, idx) => (
                      <div key={idx} className="p-2 bg-gray-50 rounded text-sm">
                        <span className="font-medium">{event.player}:</span> {event.message}
                      </div>
                    ))
                  ) : (
                    <p className="text-gray-500 italic">Aucun événement pour ce tour</p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MonopolyGameViewer;