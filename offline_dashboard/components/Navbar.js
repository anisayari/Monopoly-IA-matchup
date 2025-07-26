import React, { useState, useEffect, useRef } from 'react';
import { Upload, FileJson, X, Check } from 'lucide-react';

const Navbar = ({ onFileSelect, currentFile }) => {
  const [files, setFiles] = useState([]);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const fileInputRef = useRef(null);

  // Fetch available files
  const fetchFiles = async () => {
    try {
      const response = await fetch('/api/list-logs');
      const data = await response.json();
      setFiles(data.files || []);
    } catch (error) {
      console.error('Error fetching files:', error);
    }
  };

  useEffect(() => {
    fetchFiles();
  }, []);

  // Handle file upload
  const handleFileUpload = async (file) => {
    if (!file || !file.name.endsWith('.json')) {
      setUploadStatus({ type: 'error', message: 'Veuillez sélectionner un fichier JSON' });
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
      setUploadStatus({ type: 'loading', message: 'Téléchargement en cours...' });
      
      const response = await fetch('/api/upload-log', {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();

      if (response.ok) {
        setUploadStatus({ type: 'success', message: 'Fichier téléchargé avec succès' });
        fetchFiles(); // Refresh file list
        setTimeout(() => {
          setUploadStatus(null);
          setIsUploadOpen(false);
        }, 2000);
      } else {
        setUploadStatus({ type: 'error', message: result.error || 'Erreur lors du téléchargement' });
      }
    } catch (error) {
      setUploadStatus({ type: 'error', message: 'Erreur lors du téléchargement' });
    }
  };

  // Drag and drop handlers
  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    
    const file = e.dataTransfer.files[0];
    if (file) {
      handleFileUpload(file);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    else if (bytes < 1048576) return Math.round(bytes / 1024) + ' KB';
    else return Math.round(bytes / 1048576) + ' MB';
  };

  const formatDate = (date) => {
    return new Date(date).toLocaleString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <nav className="bg-gray-900 text-white border-b border-gray-800">
      <div className="px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4 flex-1 overflow-x-auto">
            <h1 className="text-lg font-semibold whitespace-nowrap">Logs disponibles:</h1>
            <div className="flex items-center space-x-2">
              {files.map((file) => (
                <button
                  key={file.name}
                  onClick={() => onFileSelect(file.name)}
                  className={`px-3 py-1.5 rounded-lg text-sm transition-colors flex items-center space-x-2 whitespace-nowrap ${
                    currentFile === file.name
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-800 hover:bg-gray-700 text-gray-300'
                  }`}
                  title={`${file.name}\nTaille: ${formatFileSize(file.size)}\nModifié: ${formatDate(file.modified)}`}
                >
                  <FileJson size={16} />
                  <span>{file.name}</span>
                </button>
              ))}
            </div>
          </div>
          
          <div className="relative ml-4">
            <button
              onClick={() => setIsUploadOpen(!isUploadOpen)}
              className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm transition-colors flex items-center space-x-2"
            >
              <Upload size={16} />
              <span>Upload</span>
            </button>

            {isUploadOpen && (
              <div className="absolute right-0 mt-2 w-80 bg-gray-800 rounded-lg shadow-xl border border-gray-700 p-4 z-50">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-sm font-semibold">Télécharger un fichier</h3>
                  <button
                    onClick={() => setIsUploadOpen(false)}
                    className="text-gray-400 hover:text-white"
                  >
                    <X size={16} />
                  </button>
                </div>

                <div
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                    isDragging
                      ? 'border-blue-500 bg-blue-500/10'
                      : 'border-gray-600 hover:border-gray-500'
                  }`}
                >
                  <Upload size={32} className="mx-auto mb-3 text-gray-400" />
                  <p className="text-sm text-gray-300 mb-2">
                    Glissez-déposez un fichier JSON ici
                  </p>
                  <p className="text-xs text-gray-500 mb-3">ou</p>
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm transition-colors"
                  >
                    Parcourir
                  </button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".json"
                    onChange={(e) => {
                      const file = e.target.files[0];
                      if (file) handleFileUpload(file);
                    }}
                    className="hidden"
                  />
                </div>

                {uploadStatus && (
                  <div className={`mt-4 p-3 rounded-lg text-sm ${
                    uploadStatus.type === 'error' ? 'bg-red-500/20 text-red-400' :
                    uploadStatus.type === 'success' ? 'bg-green-500/20 text-green-400' :
                    'bg-blue-500/20 text-blue-400'
                  }`}>
                    <div className="flex items-center space-x-2">
                      {uploadStatus.type === 'success' && <Check size={16} />}
                      <span>{uploadStatus.message}</span>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;