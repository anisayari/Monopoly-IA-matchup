#!/usr/bin/env python3
import os
from huggingface_hub import hf_hub_download, snapshot_download

print("📥 Téléchargement des modèles OmniParser...")

# Créer les dossiers
os.makedirs("weights/icon_detect", exist_ok=True)
os.makedirs("weights/icon_caption_florence", exist_ok=True)
os.makedirs("weights/icon_caption_blip2", exist_ok=True)

# Télécharger le modèle de détection
print("\n1️⃣ Téléchargement du modèle de détection d'icônes...")
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
print("\n2️⃣ Téléchargement de Florence-2 pour les captions...")
try:
    florence_dir = snapshot_download(
        repo_id="microsoft/Florence-2-base", 
        local_dir="weights/icon_caption_florence",
        ignore_patterns=["*.msgpack", "*.h5", "*.safetensors.index.json"]
    )
    print(f"✅ Florence-2 téléchargé: {florence_dir}")
except Exception as e:
    print(f"❌ Erreur téléchargement Florence-2: {e}")

print("\n✅ Téléchargement des modèles terminé!")
