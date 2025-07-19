#!/usr/bin/env python3
"""
OmniParser Lite - Version simplifiée sans dépendance au repo complet
"""
import os
import sys
import torch
import base64
import json
import io
from pathlib import Path
from PIL import Image
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import uvicorn
import numpy as np

# Vérifier le GPU
print("=== OmniParser Lite Server ===")
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA disponible: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"Mémoire GPU: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")

app = FastAPI(title="OmniParser Lite API", version="1.0.0")

# Configuration
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"\n✅ Utilisation du {DEVICE.upper()}")

# Import des modèles
try:
    from ultralytics import YOLO
    from transformers import AutoProcessor, AutoModelForCausalLM
    import easyocr
    print("✅ Modules importés avec succès")
except ImportError as e:
    print(f"❌ Erreur d'import: {e}")
    print("Installez les dépendances: pip install ultralytics transformers==4.49.0 easyocr")
    sys.exit(1)

# Initialisation des modèles
print("\n📥 Chargement des modèles...")

# OCR
reader = easyocr.Reader(['en'], gpu=torch.cuda.is_available())
print("✅ EasyOCR initialisé")

# YOLO pour la détection d'icônes
try:
    # Télécharger YOLO si nécessaire
    yolo_model = YOLO('yolov8s.pt')
    yolo_model.to(DEVICE)
    print("✅ YOLO chargé")
except:
    print("⚠️ YOLO non disponible, détection simplifiée")
    yolo_model = None

# Florence-2 pour les captions (optionnel)
try:
    if os.path.exists("weights/icon_caption_florence"):
        processor = AutoProcessor.from_pretrained("weights/icon_caption_florence", trust_remote_code=True)
        caption_model = AutoModelForCausalLM.from_pretrained("weights/icon_caption_florence", trust_remote_code=True).to(DEVICE)
        print("✅ Florence-2 chargé")
    else:
        processor = None
        caption_model = None
        print("⚠️ Florence-2 non disponible")
except:
    processor = None
    caption_model = None
    print("⚠️ Florence-2 non chargé")

class ImageRequest(BaseModel):
    base64_image: str

class ParsedElement(BaseModel):
    type: str
    content: str
    bbox: List[float]
    confidence: float = 1.0

class ParseResponse(BaseModel):
    parsed_content_list: List[ParsedElement]
    success: bool = True
    message: str = "OK"

def parse_image_lite(base64_img: str) -> List[ParsedElement]:
    """Parse une image avec détection simplifiée"""
    # Décoder l'image
    image_data = base64.b64decode(base64_img)
    image = Image.open(io.BytesIO(image_data)).convert('RGB')
    image_np = np.array(image)
    
    elements = []
    
    # 1. OCR pour le texte
    try:
        ocr_results = reader.readtext(image_np)
        for (bbox, text, conf) in ocr_results:
            if conf > 0.2:  # Seuil de confiance
                x1, y1 = bbox[0]
                x2, y2 = bbox[2]
                elements.append(ParsedElement(
                    type="text",
                    content=text,
                    bbox=[float(x1), float(y1), float(x2), float(y2)],
                    confidence=float(conf)
                ))
    except Exception as e:
        print(f"Erreur OCR: {e}")
    
    # 2. Détection d'objets avec YOLO (si disponible)
    if yolo_model:
        try:
            results = yolo_model(image_np)
            for r in results:
                boxes = r.boxes
                if boxes is not None:
                    for box in boxes:
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        conf = box.conf[0].item()
                        cls = int(box.cls[0].item())
                        
                        # Filtrer certains types d'objets comme boutons
                        if conf > 0.5:
                            elements.append(ParsedElement(
                                type="icon",
                                content=f"object_{cls}",
                                bbox=[float(x1), float(y1), float(x2), float(y2)],
                                confidence=float(conf)
                            ))
        except Exception as e:
            print(f"Erreur YOLO: {e}")
    
    # 3. Détection simple de boutons par couleur/forme
    # (Ajouter ici une logique de détection basique si nécessaire)
    
    return elements

@app.get("/")
async def root():
    return {
        "message": "OmniParser Lite Server", 
        "status": "running",
        "device": DEVICE,
        "gpu_available": torch.cuda.is_available(),
        "models": {
            "ocr": True,
            "yolo": yolo_model is not None,
            "florence": caption_model is not None
        }
    }

@app.get("/probe/")
async def probe():
    return {"message": "Omniparser API ready"}

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "omniparser-lite",
        "device": DEVICE,
        "cuda_available": torch.cuda.is_available()
    }

@app.post("/parse/", response_model=ParseResponse)
async def parse_image(request: ImageRequest):
    """Parse une image et retourne les éléments UI"""
    try:
        # Parser l'image
        parsed_elements = parse_image_lite(request.base64_image)

        # Convertir en format attendu
        parsed_content_list = []
        for elem in parsed_elements:
            parsed_content_list.append({
                "type": elem.type,
                "content": elem.content,
                "bbox": elem.bbox,
                "confidence": elem.confidence
            })
        
        return ParseResponse(
            parsed_content_list=parsed_content_list,
            success=True,
            message=f"Found {len(parsed_elements)} elements"
        )
        
    except Exception as e:
        print(f"Erreur lors du parsing: {e}")
        raise HTTPException(status_code=500, detail=f"Error parsing image: {str(e)}")

if __name__ == "__main__":
    print("\n🚀 Démarrage du serveur OmniParser Lite sur http://localhost:8000")
    print("   Appuyez sur Ctrl+C pour arrêter\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)