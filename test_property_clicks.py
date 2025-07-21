"""
Script de test pour cliquer sur toutes les propriétés du Monopoly
Utilise la fonction perform_click de monitor_centralized.py
"""
import json
import time
import sys
from pathlib import Path
import pygetwindow as gw

# Ajouter le répertoire courant au path pour l'import
sys.path.append(str(Path(__file__).parent))

from monitor_centralized import CentralizedMonitor
from src.utils.calibration import CalibrationUtils

def test_property_clicks():
    """Test de clic sur toutes les propriétés"""
    print("🎮 Démarrage du test de clic sur les propriétés")
    print("=" * 60)
    
    # Charger le fichier des propriétés
    try:
        with open('game_files/MonopolyProperties.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            properties = data['properties']
        print(f"✅ Chargé {len(properties)} propriétés depuis MonopolyProperties.json")
    except Exception as e:
        print(f"❌ Erreur lors du chargement du fichier: {e}")
        return
    
    # Initialiser le monitor et la calibration
    monitor = CentralizedMonitor()
    calibration = CalibrationUtils()
    
    # Vérifier que Dolphin est ouvert
    dolphin_window = monitor.get_dolphin_window()
    if not dolphin_window:
        print("❌ Fenêtre Dolphin non trouvée! Assurez-vous que Dolphin est ouvert.")
        return
    
    print(f"🖼️ Fenêtre Dolphin trouvée: {dolphin_window.title}")
    print(f"📐 Dimensions: {dolphin_window.width}x{dolphin_window.height}")
    print(f"📍 Position: ({dolphin_window.left}, {dolphin_window.top})")
    print("=" * 60)
    
    # Focus la fenêtre
    monitor.focus_dolphin_window()
    time.sleep(1)
    
    # Statistiques
    success_count = 0
    error_count = 0
    
    # Parcourir toutes les propriétés
    for i, prop in enumerate(properties):
        prop_id = prop.get('id', 'Unknown')
        prop_name = prop.get('name', 'Unknown')
        prop_type = prop.get('type', 'Unknown')
        
        print(f"\n[{i+1}/{len(properties)}] Propriété: {prop_name}")
        print(f"   ID: {prop_id}")
        print(f"   Type: {prop_type}")
        
        # Récupérer les coordonnées
        coords = prop.get('coordinates', {})
        if not coords:
            print("   ⚠️ Pas de coordonnées disponibles")
            error_count += 1
            continue
        
        # Utiliser les coordonnées relatives si disponibles
        if 'x_relative' in coords and 'y_relative' in coords:
            x_rel = coords['x_relative']
            y_rel = coords['y_relative']
            
            # Convertir en pixels absolus
            x_pixel = int(x_rel * dolphin_window.width)
            y_pixel = int(y_rel * dolphin_window.height)
            
            print(f"   📍 Coordonnées relatives: ({x_rel:.4f}, {y_rel:.4f})")
            print(f"   📍 Coordonnées pixels: ({x_pixel}, {y_pixel})")
            
            # Transformer les coordonnées avec la calibration
            try:
                abs_x, abs_y, transformed_x, transformed_y = monitor.transform_coordinates(
                    x_pixel, 
                    y_pixel, 
                    dolphin_window
                )
                
                if abs_x is not None:
                    print(f"   📍 Coordonnées transformées: ({transformed_x}, {transformed_y})")
                    print(f"   📍 Coordonnées absolues: ({abs_x}, {abs_y})")
                    
                    # Effectuer le clic
                    print(f"   🖱️ Clic sur {prop_name}...")
                    monitor.perform_click(abs_x, abs_y, f"Test clic sur {prop_name}", y_offset=8)
                    
                    success_count += 1
                    
                    # Attendre un peu entre chaque clic
                    time.sleep(1.5)
                else:
                    print("   ❌ Erreur de transformation des coordonnées")
                    error_count += 1
                    
            except Exception as e:
                print(f"   ❌ Erreur lors du clic: {e}")
                error_count += 1
                
        else:
            print("   ⚠️ Coordonnées relatives manquantes")
            error_count += 1
    
    # Résumé
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ DU TEST")
    print(f"   Total de propriétés: {len(properties)}")
    print(f"   ✅ Clics réussis: {success_count}")
    print(f"   ❌ Erreurs: {error_count}")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_property_clicks()
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrompu par l'utilisateur")
    except Exception as e:
        print(f"\n\n❌ Erreur fatale: {e}")