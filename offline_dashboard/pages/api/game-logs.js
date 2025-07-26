import fs from 'fs';
import path from 'path';

export default function handler(req, res) {
  if (req.method === 'GET') {
    try {
      // Get filename from query parameter, default to 'game_logs.json'
      const { file } = req.query;
      let filename = file || 'game_logs.json';
      
      // Temporary fix: if game_logs.json is requested and fails, use another file
      if (filename === 'game_logs.json') {
        const testPath = path.join(process.cwd(), '..', 'services', 'logs', filename);
        if (fs.existsSync(testPath)) {
          try {
            const testContent = fs.readFileSync(testPath, 'utf8');
            JSON.parse(testContent);
          } catch (e) {
            // If game_logs.json is corrupted, use another file
            console.log('game_logs.json is corrupted, using game_logs_partie_2_6h.json instead');
            filename = 'game_logs_partie_2_6h.json';
          }
        }
      }
      
      // Validate filename (prevent directory traversal)
      if (filename.includes('..') || filename.includes('/') || !filename.endsWith('.json')) {
        return res.status(400).json({ error: 'Invalid filename' });
      }
      
      const logsPath = path.join(process.cwd(), '..', 'services', 'logs', filename);
      
      // Check if file exists
      if (!fs.existsSync(logsPath)) {
        return res.status(404).json({ error: 'File not found' });
      }
      
      const fileContents = fs.readFileSync(logsPath, 'utf8');
      const data = JSON.parse(fileContents);
      res.status(200).json(data);
    } catch (error) {
      console.error('Error reading game logs:', error);
      res.status(500).json({ error: 'Failed to read game logs' });
    }
  } else {
    res.setHeader('Allow', ['GET']);
    res.status(405).end(`Method ${req.method} Not Allowed`);
  }
}