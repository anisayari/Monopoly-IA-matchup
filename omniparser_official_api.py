#!/usr/bin/env python3
"""
API serveur pour OmniParser officiel de Microsoft
Adapté pour être compatible avec votre interface existante
"""
import sys
import os
import base64
import io
import json
from pathlib import Path

# Ajouter le dossier OmniParser au path
sys.path.append('omniparser_official')

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import uvicorn
from PIL import Image
import torch

# Importer les utilitaires OmniParser
try:
    from util.omniparser import Omniparser
    print("✅ Module OmniParser importé avec succès")
except ImportError as e:
    print(f"❌ Erreur d'import OmniParser: {e}")
    print("Assurez-vous d'avoir cloné le repository dans omniparser_official/")
    sys.exit(1)

# Configuration
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"🖥️ Utilisation du device: {DEVICE}")

app = FastAPI(title="OmniParser Official API", version="1.0.0")

# Initialisation du parser
print("📥 Initialisation d'OmniParser...")
try:
    # Configuration des chemins des modèles
    config = {
        'som_model_path': 'weights/icon_detect/model.pt',
        'caption_model_path': 'weights/icon_caption_florence',
        'caption_model_name': 'florence2',
        'device': DEVICE,
        'BOX_TRESHOLD': 0.01  # Notez la casse exacte utilisée dans le code original
    }
    
    parser = Omniparser(config)
    print("✅ OmniParser initialisé avec succès")
except Exception as e:
    print(f"❌ Erreur initialisation OmniParser: {e}")
    parser = None

class ImageRequest(BaseModel):
    base64_image: str

class ParsedElement(BaseModel):
    type: str
    content: str = ""
    bbox: List[float]
    confidence: float = 1.0
    interactivity: bool = False
    source: str = "omniparser_official"

class ParseResponse(BaseModel):
    parsed_content_list: List[Dict[str, Any]]
    success: bool = True
    message: str = "OK"
    detection_image_path: str = ""
    labeled_image: str = ""
    raw_parsed_content: List[Dict[str, Any]] = []

@app.get("/")
async def root():
    return {
        "message": "OmniParser Official API Server",
        "status": "running",
        "device": DEVICE,
        "gpu_available": torch.cuda.is_available(),
        "parser_loaded": parser is not None
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy" if parser else "degraded",
        "service": "omniparser-official",
        "device": DEVICE,
        "cuda_available": torch.cuda.is_available()
    }

@app.post("/parse/", response_model=ParseResponse)
async def parse_image(request: ImageRequest):
    """Parse une image avec OmniParser officiel"""
    
    if not parser:
        raise HTTPException(status_code=503, detail="OmniParser not initialized")
    
    try:
        # Vérifier que l'image est valide en la décodant
        image_data = base64.b64decode(request.base64_image)
        image = Image.open(io.BytesIO(image_data)).convert('RGB')
        
        print(f"📸 Image reçue: {image.size}")
        
        # Parser l'image avec OmniParser
        # La méthode parse attend une image en base64
        result = parser.parse(request.base64_image)
        
        # Debug: afficher le type de retour
        print(f"🔍 Type de result: {type(result)}")
        print(f"🔍 Longueur de result: {len(result) if hasattr(result, '__len__') else 'N/A'}")
        
        if len(result) >= 2:
            labeled_img, parsed_content_list = result[:2]
            print(f"🔍 Type de labeled_img: {type(labeled_img)}")
            print(f"🔍 Type de parsed_content_list: {type(parsed_content_list)}")
            label_coordinates = {}  # Pas retourné directement par la méthode parse
        else:
            raise ValueError("Format de résultat inattendu d'OmniParser")
        
        print(f"✅ Parsing terminé: {len(parsed_content_list)} éléments trouvés")
        
        # Convertir l'image annotée en base64
        labeled_base64 = ""
        if labeled_img is not None:
            # Vérifier si c'est déjà une chaîne base64
            if isinstance(labeled_img, str):
                labeled_base64 = labeled_img
            else:
                buffered = io.BytesIO()
                # Si c'est une image PIL
                if hasattr(labeled_img, 'save'):
                    labeled_img.save(buffered, format="PNG")
                else:
                    # Si c'est un array numpy ou tensor
                    try:
                        img_pil = Image.fromarray(labeled_img)
                        img_pil.save(buffered, format="PNG")
                    except:
                        # Si c'est un tensor PyTorch, convertir d'abord en numpy
                        import numpy as np
                        if hasattr(labeled_img, 'cpu'):
                            labeled_img = labeled_img.cpu().numpy()
                        if labeled_img.ndim == 3 and labeled_img.shape[0] in [3, 4]:
                            # CHW to HWC
                            labeled_img = np.transpose(labeled_img, (1, 2, 0))
                        img_pil = Image.fromarray((labeled_img * 255).astype(np.uint8) if labeled_img.max() <= 1 else labeled_img.astype(np.uint8))
                        img_pil.save(buffered, format="PNG")
                labeled_base64 = base64.b64encode(buffered.getvalue()).decode('ascii')
        
        # Adapter le format pour être compatible avec votre système
        formatted_elements = []
        
        for i, elem in enumerate(parsed_content_list):
            # Extraire les informations selon le format OmniParser
            elem_type = elem.get('type', 'unknown')
            content = elem.get('content', '')
            
            # Gérer les différents formats de bbox possibles
            if 'bbox' in elem:
                bbox = elem['bbox']
            elif i < len(label_coordinates):
                # Utiliser label_coordinates si disponible
                coord = label_coordinates.get(str(i), [0, 0, 100, 100])
                # Convertir de xywh à xyxy si nécessaire
                if len(coord) == 4:
                    x, y, w, h = coord
                    bbox = [x, y, x + w, y + h]
                else:
                    bbox = coord
            else:
                bbox = [0, 0, 100, 100]
            
            # Déterminer le type basé sur le contenu
            if elem_type == 'unknown':
                if content and not content.startswith('Icon'):
                    elem_type = 'text'
                else:
                    elem_type = 'icon'
            
            formatted_elem = {
                "type": elem_type,
                "content": content,
                "bbox": bbox,
                "interactivity": elem_type != 'text',
                "source": "omniparser_official",
                "confidence": elem.get('confidence', 1.0)
            }
            
            formatted_elements.append(formatted_elem)
        
        # Créer la réponse
        response = ParseResponse(
            parsed_content_list=formatted_elements,
            success=True,
            message=f"Successfully parsed {len(formatted_elements)} elements",
            labeled_image=labeled_base64,
            raw_parsed_content=parsed_content_list  # Données brutes pour debug
        )
        
        return response
        
    except Exception as e:
        print(f"❌ Erreur lors du parsing: {e}")
        import traceback
        traceback.print_exc()
        
        raise HTTPException(
            status_code=500, 
            detail=f"Error parsing image: {str(e)}"
        )

if __name__ == "__main__":
    print("\n🚀 Démarrage du serveur OmniParser Official sur http://localhost:8002")
    print("   API endpoints:")
    print("   - GET  / : Status")
    print("   - GET  /health : Health check")
    print("   - POST /parse/ : Parse image")
    print("\n   Appuyez sur Ctrl+C pour arrêter\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8002)