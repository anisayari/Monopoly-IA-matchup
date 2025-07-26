import fs from 'fs';
import path from 'path';
import formidable from 'formidable';

export const config = {
  api: {
    bodyParser: false,
  },
};

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const form = formidable({
    uploadDir: path.join(process.cwd(), '..', 'services', 'logs'),
    keepExtensions: true,
    maxFileSize: 50 * 1024 * 1024, // 50MB max
  });

  try {
    const [fields, files] = await form.parse(req);
    const file = Array.isArray(files.file) ? files.file[0] : files.file;

    if (!file) {
      return res.status(400).json({ error: 'No file uploaded' });
    }

    // Validate file is JSON
    if (!file.originalFilename.endsWith('.json')) {
      // Delete uploaded file
      fs.unlinkSync(file.filepath);
      return res.status(400).json({ error: 'Only JSON files are allowed' });
    }

    // Validate JSON content
    try {
      const content = fs.readFileSync(file.filepath, 'utf8');
      JSON.parse(content);
    } catch (error) {
      // Delete invalid file
      fs.unlinkSync(file.filepath);
      return res.status(400).json({ error: 'Invalid JSON file' });
    }

    // Rename file to original name
    const targetPath = path.join(process.cwd(), '..', 'services', 'logs', file.originalFilename);
    
    // Check if file already exists
    if (fs.existsSync(targetPath)) {
      // Add timestamp to filename
      const timestamp = Date.now();
      const nameParts = file.originalFilename.split('.');
      nameParts[nameParts.length - 2] += `_${timestamp}`;
      const newName = nameParts.join('.');
      const newTargetPath = path.join(process.cwd(), '..', 'services', 'logs', newName);
      fs.renameSync(file.filepath, newTargetPath);
      
      return res.status(200).json({ 
        message: 'File uploaded successfully',
        filename: newName,
        originalName: file.originalFilename
      });
    } else {
      fs.renameSync(file.filepath, targetPath);
      
      return res.status(200).json({ 
        message: 'File uploaded successfully',
        filename: file.originalFilename
      });
    }
  } catch (error) {
    console.error('Error uploading file:', error);
    res.status(500).json({ error: 'Failed to upload file' });
  }
}