import fs from 'fs';
import path from 'path';

export default function handler(req, res) {
  if (req.method === 'GET') {
    try {
      const logsPath = path.join(process.cwd(), '..', 'services', 'logs', 'game_logs.json');
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