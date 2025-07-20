#!/usr/bin/env python3
"""
Serveur OmniParser officiel adapté pour une utilisation en API
"""
import sys
import os
sys.path.append('omniparser_official')

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import base64
import io
from PIL import Image
import uvicorn

# Importer les modules OmniParser
try:
    from omniparser_official.demo import process_image
    print("✅ Modules OmniParser importés")
except ImportError:
    print("❌ Erreur d'import des modules OmniParser")
    print("Assurez-vous que le dossier omniparser_official existe")
    sys.exit(1)

app = FastAPI(title="OmniParser Official API")

class ImageRequest(BaseModel):
    base64_image: str

@app.get("/")
async def root():
    return {"message": "OmniParser Official Server", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "omniparser-official"}

@app.post("/parse/")
async def parse_image(request: ImageRequest):
    try:
        # Décoder l'image base64
        image_data = base64.b64decode(request.base64_image)
        image = Image.open(io.BytesIO(image_data))
        
        # Traiter avec OmniParser
        results = process_image(image)
        
        return {
            "success": True,
            "parsed_content_list": results,
            "message": f"Found {len(results)} elements"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("🚀 Démarrage du serveur OmniParser officiel sur http://localhost:8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)
