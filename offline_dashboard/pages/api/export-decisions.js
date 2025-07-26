import fs from 'fs';
import path from 'path';

export default function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { sourceFile } = req.body;

    if (!sourceFile) {
      return res.status(400).json({ error: 'Missing source file' });
    }

    // Read the source file
    const sourcePath = path.join(process.cwd(), '..', 'services', 'logs', sourceFile);
    
    if (!fs.existsSync(sourcePath)) {
      return res.status(404).json({ error: 'Source file not found' });
    }

    const fileContents = fs.readFileSync(sourcePath, 'utf8');
    const gameData = JSON.parse(fileContents);

    // Process the data to extract decisions and chat messages for each turn
    const turnData = {};
    let previousChatLength = 0;

    // Sort gameData by timestamp to ensure correct order
    gameData.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

    gameData.forEach((log) => {
      const turn = log.game_context.global.current_turn;
      const players = log.game_context.players;
      
      if (!turnData[turn]) {
        turnData[turn] = {
          tour: turn,
          player1_name: players.player1.name,
          player2_name: players.player2.name,
          player1_money: players.player1.money,
          player2_money: players.player2.money,
          player1_properties: players.player1.properties.length,
          player2_properties: players.player2.properties.length,
          decisions: [],
          chat: []
        };
      } else {
        // Update money and properties count with latest values
        turnData[turn].player1_money = players.player1.money;
        turnData[turn].player2_money = players.player2.money;
        turnData[turn].player1_properties = players.player1.properties.length;
        turnData[turn].player2_properties = players.player2.properties.length;
      }

      // Extract only NEW chat messages for this turn
      if (log.chat_messages && log.chat_messages.length > 0) {
        // Get only the messages that were added since the last log entry
        const newMessages = log.chat_messages.slice(previousChatLength);
        if (newMessages.length > 0) {
          turnData[turn].chat.push(...newMessages);
        }
        previousChatLength = log.chat_messages.length;
      }

      // Add decision if present
      if (log.result) {
        turnData[turn].decisions.push({
          IA: log.player_name,
          decision: log.result.decision,
          raison: log.result.reason,
          confiance: log.result.confidence
        });
      }
    });

    // Convert to array and sort by turn
    const exportData = Object.values(turnData)
      .sort((a, b) => a.tour - b.tour)
      .map(turn => ({
        tour: turn.tour,
        player1_name: turn.player1_name,
        player2_name: turn.player2_name,
        player1_money: turn.player1_money,
        player2_money: turn.player2_money,
        player1_properties: turn.player1_properties,
        player2_properties: turn.player2_properties,
        decisions: turn.decisions,
        chat: turn.chat
      }));

    // Create export directory if it doesn't exist
    const exportDir = path.join(process.cwd(), '..', 'services', 'logs', 'export_decision');
    if (!fs.existsSync(exportDir)) {
      fs.mkdirSync(exportDir, { recursive: true });
    }

    // Create filename with timestamp
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `decisions_${sourceFile.replace('.json', '')}_${timestamp}.json`;
    const filepath = path.join(exportDir, filename);

    // Write to file
    fs.writeFileSync(filepath, JSON.stringify(exportData, null, 2), 'utf8');

    res.status(200).json({ 
      message: 'Export successful',
      filename: filename,
      path: `/services/logs/export_decision/${filename}`,
      totalTurns: exportData.length
    });
  } catch (error) {
    console.error('Error exporting decisions:', error);
    res.status(500).json({ error: 'Failed to export decisions' });
  }
}