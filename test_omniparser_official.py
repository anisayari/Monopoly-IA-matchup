#!/usr/bin/env python3
"""
Script de test pour l'API OmniParser Official
"""
import requests
import base64
import json
import sys
from pathlib import Path
from PIL import Image
import io

def test_omniparser_api(image_path=None):
    """Teste l'API OmniParser avec une image"""
    
    # URL de l'API
    API_URL = "http://localhost:8002"
    
    # Vérifier que le serveur est en ligne
    try:
        # Essayer d'abord l'endpoint racine
        response = requests.get(f"{API_URL}/", timeout=5)
        if response.status_code == 200:
            try:
                status = response.json()
                if "message" in status and "OmniParser" in status.get("message", ""):
                    print(f"✅ Serveur OmniParser en ligne: {status}")
                else:
                    print(f"⚠️  Un serveur répond sur {API_URL} mais ce n'est pas OmniParser")
                    print(f"   Réponse: {response.text[:200]}...")
                    return False
            except:
                # Si ce n'est pas du JSON, essayer l'endpoint /health
                response = requests.get(f"{API_URL}/health", timeout=5)
                if response.status_code == 200:
                    content = response.text
                    # Vérifier si c'est des métriques Prometheus (pas notre API)
                    if "python_gc_objects" in content or "omni_service" in content:
                        print(f"❌ Erreur: Le port 8001 est utilisé par un autre service (probablement Omniverse)")
                        print(f"   Arrêtez ce service ou changez le port d'OmniParser")
                        return False
                    else:
                        print(f"✅ Serveur en ligne (status code: {response.status_code})")
                else:
                    raise Exception("Erreur status code")
        else:
            raise Exception("Erreur connexion")
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur: Le serveur OmniParser n'est pas accessible sur {API_URL}")
        print(f"   Assurez-vous que le serveur est démarré avec 'start_omniparser.bat'")
        print(f"   Détail: {str(e)}")
        return False
    
    # Si pas d'image fournie, créer une image de test
    if not image_path:
        print("\n📸 Création d'une image de test...")
        # Créer une simple image avec du texte
        from PIL import Image, ImageDraw, ImageFont
        
        img = Image.new('RGB', (800, 600), color='white')
        draw = ImageDraw.Draw(img)
        
        # Essayer d'utiliser une police par défaut
        try:
            font = ImageFont.truetype("arial.ttf", 40)
        except:
            font = ImageFont.load_default()
        
        # Dessiner du texte et des formes
        draw.text((50, 50), "Test OmniParser", fill='black', font=font)
        draw.text((50, 150), "Click Here", fill='blue', font=font)
        draw.rectangle([50, 250, 200, 300], fill='green')
        draw.text((60, 260), "Button", fill='white', font=font)
        draw.rectangle([300, 250, 500, 350], outline='red', width=3)
        draw.text((320, 280), "Input Field", fill='black', font=font)
        
        # Sauvegarder temporairement
        test_image_path = Path("test_image_omniparser.png")
        img.save(test_image_path)
        image_path = test_image_path
        print(f"✅ Image de test créée: {test_image_path}")
    else:
        image_path = Path(image_path)
        if not image_path.exists():
            print(f"❌ Erreur: L'image {image_path} n'existe pas")
            return False
    
    # Encoder l'image en base64
    print(f"\n📤 Envoi de l'image: {image_path}")
    with open(image_path, 'rb') as f:
        image_base64 = base64.b64encode(f.read()).decode('utf-8')
    
    # Préparer la requête
    payload = {
        "base64_image": image_base64
    }
    
    # Envoyer la requête
    try:
        print("⏳ Analyse en cours...")
        response = requests.post(f"{API_URL}/parse/", json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ Analyse réussie!")
            print(f"   Nombre d'éléments détectés: {len(result['parsed_content_list'])}")
            print(f"   Message: {result['message']}")
            
            # Afficher les éléments détectés
            print("\n📊 Éléments détectés:")
            for i, elem in enumerate(result['parsed_content_list']):
                print(f"\n   [{i+1}] Type: {elem['type']}")
                print(f"       Contenu: {elem.get('content', 'N/A')}")
                print(f"       Position: {elem['bbox']}")
                print(f"       Interactif: {elem.get('interactivity', False)}")
                print(f"       Confiance: {elem.get('confidence', 'N/A')}")
            
            # Sauvegarder l'image annotée si disponible
            if result.get('labeled_image'):
                labeled_data = base64.b64decode(result['labeled_image'])
                labeled_path = Path("test_result_labeled.png")
                with open(labeled_path, 'wb') as f:
                    f.write(labeled_data)
                print(f"\n✅ Image annotée sauvegardée: {labeled_path}")
            
            # Sauvegarder le résultat complet
            result_path = Path("test_result_omniparser.json")
            with open(result_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"📄 Résultat complet sauvegardé: {result_path}")
            
            return True
            
        else:
            print(f"\n❌ Erreur {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Timeout: L'analyse a pris trop de temps")
        return False
    except Exception as e:
        print(f"❌ Erreur lors de l'analyse: {e}")
        return False

if __name__ == "__main__":
    print("🧪 TEST OMNIPARSER OFFICIAL API")
    print("================================\n")
    
    # Utiliser l'image fournie en argument ou créer une image de test
    image_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    success = test_omniparser_api(image_path)
    
    if success:
        print("\n✅ Test terminé avec succès!")
    else:
        print("\n❌ Test échoué!")
    
    print("\nAppuyez sur Entrée pour quitter...")
    input()