import React, { useState, useEffect } from 'react';
import { Play, Pause, RotateCcw, SkipForward, SkipBack } from 'lucide-react';

const AnimatedStats = ({ animatedData }) => {
  const [currentTurn, setCurrentTurn] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(1000); // milliseconds between turns

  // Get player names from the first data point
  const player1Name = animatedData[0]?.player1_name || 'Player 1';
  const player2Name = animatedData[0]?.player2_name || 'Player 2';

  // Calculate max values for scaling
  const maxMoney = Math.max(...animatedData.map(d => Math.max(d.player1_money, d.player2_money)));
  const maxProperties = Math.max(...animatedData.map(d => Math.max(d.player1_properties, d.player2_properties)));
  const maxHouses = Math.max(...animatedData.map(d => Math.max(d.player1_houses, d.player2_houses)));
  const maxMortgaged = Math.max(...animatedData.map(d => Math.max(d.player1_mortgaged || 0, d.player2_mortgaged || 0)));

  // Animation logic
  useEffect(() => {
    if (!isPlaying) return;

    const interval = setInterval(() => {
      setCurrentTurn(prev => {
        if (prev >= animatedData.length - 1) {
          setIsPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, speed);

    return () => clearInterval(interval);
  }, [isPlaying, speed, animatedData.length]);

  const currentData = animatedData[currentTurn] || animatedData[0];

  // Calculate percentages for bar widths
  const player1MoneyPercent = (currentData.player1_money / maxMoney) * 100;
  const player2MoneyPercent = (currentData.player2_money / maxMoney) * 100;
  const player1PropertiesPercent = (currentData.player1_properties / maxProperties) * 100;
  const player2PropertiesPercent = (currentData.player2_properties / maxProperties) * 100;
  const player1HousesPercent = (currentData.player1_houses / Math.max(maxHouses, 1)) * 100;
  const player2HousesPercent = (currentData.player2_houses / Math.max(maxHouses, 1)) * 100;
  const player1MortgagedPercent = ((currentData.player1_mortgaged || 0) / Math.max(maxMortgaged, 1)) * 100;
  const player2MortgagedPercent = ((currentData.player2_mortgaged || 0) / Math.max(maxMortgaged, 1)) * 100;

  const handlePlayPause = () => {
    setIsPlaying(!isPlaying);
  };

  const handleReset = () => {
    setCurrentTurn(0);
    setIsPlaying(false);
  };

  const handlePrevious = () => {
    setCurrentTurn(Math.max(0, currentTurn - 1));
  };

  const handleNext = () => {
    setCurrentTurn(Math.min(animatedData.length - 1, currentTurn + 1));
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Animation des Statistiques</h2>
      
      {/* Turn indicator */}
      <div className="mb-8 text-center">
        <h3 className="text-3xl font-bold text-gray-700">Tour {currentData.turn}</h3>
        <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
          <div 
            className="bg-blue-500 h-2 rounded-full transition-all duration-300"
            style={{ width: `${(currentTurn / (animatedData.length - 1)) * 100}%` }}
          />
        </div>
      </div>

      {/* Stats bars */}
      <div className="space-y-8">
        {/* Money */}
        <div>
          <h4 className="text-lg font-semibold text-gray-700 mb-3">💰 Argent</h4>
          <div className="space-y-3">
            <div>
              <div className="flex justify-between items-center mb-1">
                <span className="text-sm font-medium text-blue-600">{player1Name}</span>
                <span className="text-sm font-bold text-blue-600">{currentData.player1_money}€</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-8">
                <div 
                  className="bg-blue-500 h-8 rounded-full transition-all duration-500 ease-out flex items-center justify-end pr-2"
                  style={{ width: `${player1MoneyPercent}%` }}
                >
                  {player1MoneyPercent > 10 && (
                    <span className="text-xs text-white font-semibold">{currentData.player1_money}€</span>
                  )}
                </div>
              </div>
            </div>
            <div>
              <div className="flex justify-between items-center mb-1">
                <span className="text-sm font-medium text-red-600">{player2Name}</span>
                <span className="text-sm font-bold text-red-600">{currentData.player2_money}€</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-8">
                <div 
                  className="bg-red-500 h-8 rounded-full transition-all duration-500 ease-out flex items-center justify-end pr-2"
                  style={{ width: `${player2MoneyPercent}%` }}
                >
                  {player2MoneyPercent > 10 && (
                    <span className="text-xs text-white font-semibold">{currentData.player2_money}€</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Properties */}
        <div>
          <h4 className="text-lg font-semibold text-gray-700 mb-3">🏠 Propriétés</h4>
          <div className="space-y-3">
            <div>
              <div className="flex justify-between items-center mb-1">
                <span className="text-sm font-medium text-blue-600">{player1Name}</span>
                <span className="text-sm font-bold text-blue-600">{currentData.player1_properties}</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-8">
                <div 
                  className="bg-blue-500 h-8 rounded-full transition-all duration-500 ease-out flex items-center justify-end pr-2"
                  style={{ width: `${player1PropertiesPercent}%` }}
                >
                  {player1PropertiesPercent > 10 && (
                    <span className="text-xs text-white font-semibold">{currentData.player1_properties}</span>
                  )}
                </div>
              </div>
            </div>
            <div>
              <div className="flex justify-between items-center mb-1">
                <span className="text-sm font-medium text-red-600">{player2Name}</span>
                <span className="text-sm font-bold text-red-600">{currentData.player2_properties}</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-8">
                <div 
                  className="bg-red-500 h-8 rounded-full transition-all duration-500 ease-out flex items-center justify-end pr-2"
                  style={{ width: `${player2PropertiesPercent}%` }}
                >
                  {player2PropertiesPercent > 10 && (
                    <span className="text-xs text-white font-semibold">{currentData.player2_properties}</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Mortgaged Properties */}
        <div>
          <h4 className="text-lg font-semibold text-gray-700 mb-3">🔒 Propriétés Hypothéquées</h4>
          <div className="space-y-3">
            <div>
              <div className="flex justify-between items-center mb-1">
                <span className="text-sm font-medium text-blue-600">{player1Name}</span>
                <span className="text-sm font-bold text-blue-600">{currentData.player1_mortgaged || 0}</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-8">
                <div 
                  className="bg-blue-400 h-8 rounded-full transition-all duration-500 ease-out flex items-center justify-end pr-2"
                  style={{ width: `${player1MortgagedPercent}%` }}
                >
                  {player1MortgagedPercent > 10 && (
                    <span className="text-xs text-white font-semibold">{currentData.player1_mortgaged || 0}</span>
                  )}
                </div>
              </div>
            </div>
            <div>
              <div className="flex justify-between items-center mb-1">
                <span className="text-sm font-medium text-red-600">{player2Name}</span>
                <span className="text-sm font-bold text-red-600">{currentData.player2_mortgaged || 0}</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-8">
                <div 
                  className="bg-red-400 h-8 rounded-full transition-all duration-500 ease-out flex items-center justify-end pr-2"
                  style={{ width: `${player2MortgagedPercent}%` }}
                >
                  {player2MortgagedPercent > 10 && (
                    <span className="text-xs text-white font-semibold">{currentData.player2_mortgaged || 0}</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Houses */}
        <div>
          <h4 className="text-lg font-semibold text-gray-700 mb-3">🏘️ Maisons</h4>
          <div className="space-y-3">
            <div>
              <div className="flex justify-between items-center mb-1">
                <span className="text-sm font-medium text-blue-600">{player1Name}</span>
                <span className="text-sm font-bold text-blue-600">{currentData.player1_houses}</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-8">
                <div 
                  className="bg-blue-500 h-8 rounded-full transition-all duration-500 ease-out flex items-center justify-end pr-2"
                  style={{ width: `${player1HousesPercent}%` }}
                >
                  {player1HousesPercent > 10 && (
                    <span className="text-xs text-white font-semibold">{currentData.player1_houses}</span>
                  )}
                </div>
              </div>
            </div>
            <div>
              <div className="flex justify-between items-center mb-1">
                <span className="text-sm font-medium text-red-600">{player2Name}</span>
                <span className="text-sm font-bold text-red-600">{currentData.player2_houses}</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-8">
                <div 
                  className="bg-red-500 h-8 rounded-full transition-all duration-500 ease-out flex items-center justify-end pr-2"
                  style={{ width: `${player2HousesPercent}%` }}
                >
                  {player2HousesPercent > 10 && (
                    <span className="text-xs text-white font-semibold">{currentData.player2_houses}</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Total wealth comparison */}
        <div className="mt-8 p-4 bg-gray-50 rounded-lg">
          <h4 className="text-lg font-semibold text-gray-700 mb-3">📊 Comparaison de la richesse totale</h4>
          <div className="grid grid-cols-2 gap-4">
            <div className="text-center">
              <p className="text-sm text-gray-600">{player1Name}</p>
              <p className="text-2xl font-bold text-blue-600">
                {currentData.player1_money + (currentData.player1_properties * 200) + (currentData.player1_houses * 50)}€
              </p>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-600">{player2Name}</p>
              <p className="text-2xl font-bold text-red-600">
                {currentData.player2_money + (currentData.player2_properties * 200) + (currentData.player2_houses * 50)}€
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="mt-8 border-t pt-6">
        <div className="flex items-center justify-center space-x-4">
          <button
            onClick={handlePrevious}
            disabled={currentTurn === 0}
            className={`p-2 rounded-lg transition-colors ${
              currentTurn === 0 
                ? 'bg-gray-200 text-gray-400 cursor-not-allowed' 
                : 'bg-gray-300 hover:bg-gray-400 text-gray-700'
            }`}
          >
            <SkipBack size={20} />
          </button>
          
          <button
            onClick={handlePlayPause}
            className="p-3 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
          >
            {isPlaying ? <Pause size={24} /> : <Play size={24} />}
          </button>
          
          <button
            onClick={handleNext}
            disabled={currentTurn === animatedData.length - 1}
            className={`p-2 rounded-lg transition-colors ${
              currentTurn === animatedData.length - 1 
                ? 'bg-gray-200 text-gray-400 cursor-not-allowed' 
                : 'bg-gray-300 hover:bg-gray-400 text-gray-700'
            }`}
          >
            <SkipForward size={20} />
          </button>
          
          <button
            onClick={handleReset}
            className="p-2 bg-gray-300 hover:bg-gray-400 text-gray-700 rounded-lg transition-colors"
          >
            <RotateCcw size={20} />
          </button>
        </div>

        {/* Speed control */}
        <div className="mt-4 flex items-center justify-center space-x-4">
          <span className="text-sm text-gray-600">Vitesse:</span>
          <input
            type="range"
            min="100"
            max="2000"
            step="100"
            value={2100 - speed}
            onChange={(e) => setSpeed(2100 - parseInt(e.target.value))}
            className="w-32"
          />
          <span className="text-sm text-gray-600">{speed}ms</span>
        </div>
      </div>
    </div>
  );
};

export default AnimatedStats;