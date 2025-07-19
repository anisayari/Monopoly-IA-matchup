#!/usr/bin/env python3
"""
OmniParser Server Natif (sans Docker) avec support GPU
"""
import os
import sys
import torch
import base64
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import uvicorn

# Vérifier le GPU
print("=== OmniParser Native Server ===")
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA disponible: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"Mémoire GPU: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")

# Ajouter le chemin d'OmniParser
omniparser_path = Path(__file__).parent / "OmniParser"
if not omniparser_path.exists():
    # Essayer dans omniparserserver
    omniparser_path = Path(__file__).parent / "omniparserserver" / "OmniParser"
    if not omniparser_path.exists():
        print("❌ Erreur: OmniParser non trouvé.")
        print("   Lancez d'abord: setup_omniparser_native.bat")
        sys.exit(1)

sys.path.insert(0, str(omniparser_path))

# Importer OmniParser
try:
    from utils.omniparser import Omniparser
except ImportError:
    try:
        from util.omniparser import Omniparser
    except ImportError:
        print("❌ Erreur: Impossible d'importer OmniParser")
        print("   Vérifiez que OmniParser est bien installé dans:", omniparser_path)
        sys.exit(1)

app = FastAPI(title="OmniParser Native API", version="1.0.0")

# Configuration OmniParser
CONFIG = {
    'som_model_path': 'weights',
    'device': 'cuda' if torch.cuda.is_available() else 'cpu',
    'caption_model_path': 'weights/icon_caption_florence',
    'draw_bbox_config': {
        'text_scale': 0.8,
        'text_thickness': 2,
        'text_padding': 3,
        'thickness': 3,
    },
    'BOX_TRESHOLD': 0.03
}

# Initialiser OmniParser
print("Initialisation d'OmniParser...")
omniparser = Omniparser(CONFIG)
print(f"✅ OmniParser initialisé sur {CONFIG['device'].upper()}!")

class ImageRequest(BaseModel):
    base64_image: str

class ParseResponse(BaseModel):
    parsed_content_list: List[Dict[str, Any]]
    success: bool = True
    message: str = "OK"

@app.get("/")
async def root():
    return {
        "message": "OmniParser Native Server", 
        "status": "running",
        "device": CONFIG['device'],
        "gpu_available": torch.cuda.is_available()
    }

@app.get("/probe/")
async def probe():
    return {"message": "Omniparser API ready"}

@app.post("/parse/", response_model=ParseResponse)
async def parse_image(request: ImageRequest):
    """Parse une image et retourne les éléments UI"""
    try:
        # Parser l'image
        dino_labeled_img, parsed_content_list = omniparser.parse(request.base64_image)
        
        return ParseResponse(
            parsed_content_list=parsed_content_list,
            success=True,
            message="Image parsed successfully"
        )
        
    except Exception as e:
        print(f"Erreur lors du parsing: {e}")
        raise HTTPException(status_code=500, detail=f"Error parsing image: {str(e)}")

if __name__ == "__main__":
    print("\n🚀 Démarrage du serveur OmniParser natif sur http://localhost:8000")
    print("   Appuyez sur Ctrl+C pour arrêter\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)