#!/usr/bin/env python3
"""
Script d'installation de l'OmniParser officiel de Microsoft
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, cwd=None):
    """Exécute une commande et affiche la sortie en temps réel"""
    print(f"📌 Exécution: {cmd}")
    process = subprocess.Popen(
        cmd, 
        shell=True, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT, 
        text=True,
        cwd=cwd
    )
    
    for line in process.stdout:
        print(line, end='')
    
    process.wait()
    
    if process.returncode != 0:
        print(f"❌ Erreur lors de l'exécution de: {cmd}")
        return False
    return True

def main():
    print("🚀 Installation d'OmniParser officiel de Microsoft")
    print("=" * 60)
    
    # Vérifier si git est installé
    if not shutil.which('git'):
        print("❌ Git n'est pas installé. Veuillez installer Git d'abord.")
        return
    
    # Créer un dossier pour OmniParser
    omniparser_dir = Path("omniparser_official")
    
    # Supprimer le dossier s'il existe déjà
    if omniparser_dir.exists():
        print(f"⚠️  Le dossier {omniparser_dir} existe déjà.")
        response = input("Voulez-vous le supprimer et réinstaller ? (y/n): ").lower()
        if response == 'y':
            shutil.rmtree(omniparser_dir)
        else:
            print("Installation annulée.")
            return
    
    # Cloner le repository
    print("\n📥 Clonage du repository OmniParser...")
    if not run_command("git clone https://github.com/microsoft/OmniParser.git omniparser_official"):
        return
    
    print("\n✅ Repository cloné avec succès")
    
    # Installer les dépendances
    print("\n📦 Installation des dépendances OmniParser...")
    
    # Créer requirements_omniparser.txt avec les dépendances spécifiques
    requirements_content = """# OmniParser dependencies
torch>=2.0.0
torchvision>=0.15.0
transformers>=4.36.0
ultralytics>=8.0.0
opencv-python>=4.8.0
Pillow>=10.0.0
numpy>=1.24.0
easyocr>=1.7.0
paddlepaddle>=2.5.0
paddleocr>=2.7.0
supervision>=0.16.0
matplotlib>=3.7.0
fastapi>=0.104.0
uvicorn>=0.24.0
python-multipart>=0.0.6
gradio>=4.0.0
huggingface-hub>=0.19.0
"""
    
    with open("requirements_omniparser.txt", "w") as f:
        f.write(requirements_content)
    
    print("📝 Fichier requirements_omniparser.txt créé")
    
    # Installer avec pip
    print("\n🔧 Installation des packages Python...")
    if not run_command(f"{sys.executable} -m pip install -r requirements_omniparser.txt"):
        print("⚠️  Certaines dépendances n'ont pas pu être installées")
    
    # Télécharger les modèles
    print("\n📥 Téléchargement des modèles OmniParser...")
    
    # Créer le script de téléchargement des modèles
    download_script = """#!/usr/bin/env python3
import os
from huggingface_hub import hf_hub_download, snapshot_download

print("📥 Téléchargement des modèles OmniParser...")

# Créer les dossiers
os.makedirs("weights/icon_detect", exist_ok=True)
os.makedirs("weights/icon_caption_florence", exist_ok=True)
os.makedirs("weights/icon_caption_blip2", exist_ok=True)

# Télécharger le modèle de détection
print("\\n1️⃣ Téléchargement du modèle de détection d'icônes...")
try:
    model_path = hf_hub_download(
        repo_id="microsoft/OmniParser", 
        filename="icon_detect/model.pt",
        local_dir="weights"
    )
    print(f"✅ Modèle de détection téléchargé: {model_path}")
except Exception as e:
    print(f"❌ Erreur téléchargement détection: {e}")

# Télécharger Florence-2 pour les captions
print("\\n2️⃣ Téléchargement de Florence-2 pour les captions...")
try:
    florence_dir = snapshot_download(
        repo_id="microsoft/Florence-2-base", 
        local_dir="weights/icon_caption_florence",
        ignore_patterns=["*.msgpack", "*.h5", "*.safetensors.index.json"]
    )
    print(f"✅ Florence-2 téléchargé: {florence_dir}")
except Exception as e:
    print(f"❌ Erreur téléchargement Florence-2: {e}")

print("\\n✅ Téléchargement des modèles terminé!")
"""
    
    with open("download_omniparser_models.py", "w") as f:
        f.write(download_script)
    
    print("📝 Script de téléchargement créé")
    print("\n🔄 Exécution du téléchargement des modèles...")
    
    if not run_command(f"{sys.executable} download_omniparser_models.py"):
        print("⚠️  Erreur lors du téléchargement des modèles")
    
    # Créer un script de lancement pour OmniParser officiel
    launch_script = """#!/usr/bin/env python3
\"\"\"
Serveur OmniParser officiel adapté pour une utilisation en API
\"\"\"
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
"""
    
    with open("omniparser_official_server.py", "w") as f:
        f.write(launch_script)
    
    # Créer un fichier batch pour Windows
    batch_content = """@echo off
title OmniParser Official Server
echo ========================================
echo     OmniParser Official Server
echo     Port: 8001
echo ========================================
echo.

python omniparser_official_server.py

pause
"""
    
    with open("start_omniparser_official.bat", "w") as f:
        f.write(batch_content)
    
    print("\n✅ Installation terminée!")
    print("\n📋 Résumé de l'installation:")
    print("   - Repository cloné dans: ./omniparser_official/")
    print("   - Modèles téléchargés dans: ./weights/")
    print("   - Script de lancement: omniparser_official_server.py")
    print("   - Fichier batch Windows: start_omniparser_official.bat")
    print("\n🚀 Pour lancer le serveur OmniParser officiel:")
    print("   - Windows: double-cliquez sur start_omniparser_official.bat")
    print("   - Linux/Mac: python omniparser_official_server.py")
    print("\n⚠️  Notes importantes:")
    print("   - Le serveur officiel utilise le port 8001 (votre version lite utilise 8000)")
    print("   - Assurez-vous d'avoir suffisamment de mémoire GPU disponible")
    print("   - Les deux serveurs peuvent coexister sur des ports différents")

if __name__ == "__main__":
    main()