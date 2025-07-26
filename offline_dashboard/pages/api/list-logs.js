import fs from 'fs';
import path from 'path';

export default function handler(req, res) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const logsDir = path.join(process.cwd(), '..', 'services', 'logs');
    
    // Check if directory exists
    if (!fs.existsSync(logsDir)) {
      return res.status(200).json({ files: [] });
    }

    // Read directory and filter JSON files
    const files = fs.readdirSync(logsDir)
      .filter(file => file.endsWith('.json'))
      .map(file => {
        const filePath = path.join(logsDir, file);
        const stats = fs.statSync(filePath);
        return {
          name: file,
          size: stats.size,
          modified: stats.mtime,
          path: file
        };
      })
      .sort((a, b) => b.modified - a.modified); // Sort by most recent first

    res.status(200).json({ files });
  } catch (error) {
    console.error('Error listing log files:', error);
    res.status(500).json({ error: 'Failed to list log files' });
  }
}