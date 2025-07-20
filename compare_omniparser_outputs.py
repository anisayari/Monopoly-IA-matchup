#!/usr/bin/env python3
"""
Script pour comparer les sorties JSON des deux versions d'OmniParser
"""
import requests
import base64
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import io
from datetime import datetime

def create_test_image():
    """Créer une image de test simple"""
    img = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("arial.ttf", 30)
    except:
        font = ImageFont.load_default()
    
    # Dessiner quelques éléments
    draw.text((50, 50), "Test Comparison", fill='black', font=font)
    draw.rectangle([100, 150, 250, 200], fill='blue')
    draw.text((120, 160), "Button", fill='white', font=font)
    draw.rectangle([300, 150, 500, 250], outline='red', width=3)
    draw.text((320, 180), "Input Box", fill='black', font=font)
    
    # Sauvegarder
    test_path = Path("test_comparison_image.png")
    img.save(test_path)
    return test_path

def test_api(api_url, image_path):
    """Tester une API OmniParser"""
    # Encoder l'image
    with open(image_path, 'rb') as f:
        image_base64 = base64.b64encode(f.read()).decode('utf-8')
    
    # Préparer la requête
    payload = {"base64_image": image_base64}
    
    try:
        # Tester d'abord la disponibilité
        health_response = requests.get(f"{api_url}/", timeout=5)
        print(f"✅ API accessible sur {api_url}")
        
        # Envoyer la requête de parsing
        response = requests.post(f"{api_url}/parse/", json=payload, timeout=30)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Erreur {response.status_code}: {response.text[:200]}")
            return None
            
    except Exception as e:
        print(f"❌ Erreur connexion {api_url}: {e}")
        return None

def compare_results(lite_result, official_result):
    """Comparer les résultats des deux APIs"""
    print("\n" + "="*60)
    print("COMPARAISON DES FORMATS JSON")
    print("="*60)
    
    # Structure générale
    print("\n📋 STRUCTURE GÉNÉRALE:")
    print(f"   Lite keys: {list(lite_result.keys())}")
    print(f"   Official keys: {list(official_result.keys())}")
    
    # Nombre d'éléments détectés
    lite_count = len(lite_result.get('parsed_content_list', []))
    official_count = len(official_result.get('parsed_content_list', []))
    print(f"\n📊 NOMBRE D'ÉLÉMENTS:")
    print(f"   Lite: {lite_count}")
    print(f"   Official: {official_count}")
    
    # Comparer les éléments
    print("\n🔍 DÉTAIL DES ÉLÉMENTS:")
    
    # Lite
    print("\n  VERSION LITE:")
    for i, elem in enumerate(lite_result.get('parsed_content_list', [])[:3]):
        print(f"\n  [{i}] Keys: {list(elem.keys())}")
        print(f"      Type: {elem.get('type', 'N/A')}")
        print(f"      Content: {elem.get('content', 'N/A')[:50]}")
        print(f"      BBox: {elem.get('bbox', 'N/A')}")
        print(f"      Confidence: {elem.get('confidence', 'N/A')}")
    
    # Official
    print("\n  VERSION OFFICIAL:")
    for i, elem in enumerate(official_result.get('parsed_content_list', [])[:3]):
        print(f"\n  [{i}] Keys: {list(elem.keys())}")
        print(f"      Type: {elem.get('type', 'N/A')}")
        print(f"      Content: {elem.get('content', 'N/A')[:50]}")
        print(f"      BBox: {elem.get('bbox', 'N/A')}")
        print(f"      Interactivity: {elem.get('interactivity', 'N/A')}")
        print(f"      Source: {elem.get('source', 'N/A')}")
    
    # Différences clés
    print("\n⚠️  DIFFÉRENCES PRINCIPALES:")
    
    # Champs spécifiques
    lite_only = set()
    official_only = set()
    
    if lite_result.get('parsed_content_list'):
        lite_elem = lite_result['parsed_content_list'][0]
        lite_only = set(lite_elem.keys())
    
    if official_result.get('parsed_content_list'):
        official_elem = official_result['parsed_content_list'][0]
        official_only = set(official_elem.keys())
    
    print(f"   Champs uniquement dans Lite: {lite_only - official_only}")
    print(f"   Champs uniquement dans Official: {official_only - lite_only}")
    
    # Sauvegarder les résultats complets
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    with open(f"comparison_lite_{timestamp}.json", 'w', encoding='utf-8') as f:
        json.dump(lite_result, f, indent=2, ensure_ascii=False)
    
    with open(f"comparison_official_{timestamp}.json", 'w', encoding='utf-8') as f:
        json.dump(official_result, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Résultats complets sauvegardés:")
    print(f"   - comparison_lite_{timestamp}.json")
    print(f"   - comparison_official_{timestamp}.json")

def main():
    print("🔄 COMPARAISON OMNIPARSER LITE VS OFFICIAL")
    print("==========================================\n")
    
    # URLs des APIs
    LITE_URL = "http://localhost:8000"
    OFFICIAL_URL = "http://localhost:8002"
    
    # Créer ou utiliser une image de test
    image_path = create_test_image()
    print(f"📸 Image de test: {image_path}\n")
    
    # Tester Lite
    print("🧪 Test OmniParser Lite...")
    lite_result = test_api(LITE_URL, image_path)
    
    if not lite_result:
        print("⚠️  OmniParser Lite non disponible")
        print("   Assurez-vous qu'il est démarré sur le port 8000")
        return
    
    # Tester Official
    print("\n🧪 Test OmniParser Official...")
    official_result = test_api(OFFICIAL_URL, image_path)
    
    if not official_result:
        print("⚠️  OmniParser Official non disponible")
        print("   Assurez-vous qu'il est démarré sur le port 8002")
        return
    
    # Comparer les résultats
    compare_results(lite_result, official_result)
    
    # Sauvegarder les images annotées si disponibles
    for name, result in [("lite", lite_result), ("official", official_result)]:
        if result.get('labeled_image'):
            try:
                img_data = base64.b64decode(result['labeled_image'])
                with open(f"comparison_{name}_labeled.png", 'wb') as f:
                    f.write(img_data)
                print(f"\n✅ Image annotée {name} sauvegardée: comparison_{name}_labeled.png")
            except:
                pass

if __name__ == "__main__":
    main()
    print("\nAppuyez sur Entrée pour quitter...")
    input()