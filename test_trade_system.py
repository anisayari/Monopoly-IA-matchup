"""
Test complet du système de trade dans monitor_centralized
Utilise inverse_conversion et mouseDown/mouseUp
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time
import pygetwindow as gw
import pyautogui
from monitor_centralized import CentralizedMonitor
from src.utils import get_coordinates

def test_trade_with_mock_data():
    """Test du trade avec des données simulées en utilisant CentralizedMonitor"""
    
    print("🎮 Test du système de trade")
    print("=" * 60)
    
    # Vérifier Dolphin
    dolphin_windows = gw.getWindowsWithTitle("Dolphin")
    if not dolphin_windows:
        print("❌ Erreur: Dolphin n'est pas ouvert!")
        print("   Veuillez lancer Dolphin avant d'exécuter ce test.")
        return
    
    win = dolphin_windows[0]
    print(f"✅ Fenêtre Dolphin détectée: {win.width}x{win.height} à ({win.left}, {win.top})")
    
    # Créer une instance réelle de CentralizedMonitor
    monitor = CentralizedMonitor("http://localhost:5000")
    
    # Configurer le contexte de jeu
    monitor.game_context = {
        'global': {
            'current_player': 'player1',
            'current_turn': 10
        },
        'players': {
            'player1': {
                'name': 'Player 1',
                'money': 1500,
                'properties': ['Old Kent Road', 'Park Place']
            },
            'player2': {
                'name': 'Player 2',
                'money': 1200,
                'properties': ['Whitechapel Road', 'Boardwalk']
            }
        }
    }
    
    # Données de trade simulées
    trade_data = {
        'player1': {
            'offers': {
                'money': 200,
                'properties': ['Old Kent Road']  # Player1 offre Old Kent Road
            }
        },
        'player2': {
            'offers': {
                'money': 0,
                'properties': ['Whitechapel Road']  # Player2 offre Whitechapel Road
            }
        }
    }
    
    # Résultat simulé avec options
    result = {
        'success': True,
        'decision': 'propose',
        'reason': 'Test de trade',
        'options': [
            {
                'name': 'cancel',
                'bbox': [700, 600, 800, 650]
            },
            {
                'name': 'propose',
                'bbox': [850, 600, 950, 650]
            },
            {
                'name': 'add cash',
                'bbox': [600, 500, 700, 550]
            }
        ]
    }
    
    print("\n📋 Configuration du test:")
    print(f"   Joueur actuel: {monitor.game_context['global']['current_player']}")
    print("   Trade simulé:")
    print("   - Player 1 offre: Old Kent Road + $200")
    print("   - Player 2 offre: Whitechapel Road")
    print(f"   Décision: {result['decision']}")
    
    print("\n⏱️  Démarrage du test dans 3 secondes...")
    print("   Les clics vont être effectués sur Dolphin")
    
    for i in range(3, 0, -1):
        print(f"   {i}...")
        time.sleep(1)
    
    # Exécuter la fonction de trade
    try:
        monitor._handle_trade_event(trade_data, result, None)
        print("\n✅ Test terminé avec succès!")
    except Exception as e:
        print(f"\n❌ Erreur lors du test: {e}")
        import traceback
        traceback.print_exc()

def test_property_coordinates():
    """Test des coordonnées des propriétés depuis MonopolyProperties.json"""
    
    print("\n📍 Test des coordonnées des propriétés")
    print("=" * 60)
    
    # Charger directement depuis MonopolyProperties.json
    properties_file = os.path.join("game_files", "MonopolyProperties.json")
    
    if not os.path.exists(properties_file):
        print(f"❌ Fichier non trouvé: {properties_file}")
        return
        
    with open(properties_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Propriétés à tester
    test_props = ["Old Kent Road", "Whitechapel Road", "Park Place", "Boardwalk"]
    
    print(f"\n📋 Propriétés trouvées dans {properties_file}:")
    for prop in data.get('properties', []):
        if prop.get('name') in test_props:
            name = prop.get('name')
            coords = prop.get('coordinates', {})
            print(f"\n✅ {name}:")
            print(f"   - Relatives: ({coords.get('x_relative', 'N/A')}, {coords.get('y_relative', 'N/A')})")
            print(f"   - Absolues: ({coords.get('x_pixel', 'N/A')}, {coords.get('y_pixel', 'N/A')})")

def test_property_clicks():
    """Test des clics sur propriétés comme dans _handle_trade_event"""
    
    print("\n🏠 Test des clics sur propriétés")
    print("=" * 60)
    
    dolphin_windows = gw.getWindowsWithTitle("Dolphin")
    if not dolphin_windows:
        print("❌ Dolphin non trouvé")
        return
    
    win = dolphin_windows[0]
    
    # Créer une instance de CentralizedMonitor
    monitor = CentralizedMonitor("http://localhost:5000")
    
    # Propriétés à tester (ordre: autre joueur puis joueur actuel)
    properties_to_click = [
        ("Whitechapel Road", "player2"),
        ("Old Kent Road", "player1")
    ]
    
    print(f"\n📋 Séquence de clics prévue:")
    for prop_name, owner in properties_to_click:
        coords = get_coordinates(prop_name, 'relative')
        if coords:
            print(f"   ✅ {prop_name} ({owner}): coordonnées trouvées")
        else:
            print(f"   ❌ {prop_name} ({owner}): coordonnées non trouvées")
    
    print("\n⏱️  Début des clics dans 3 secondes...")
    for i in range(3, 0, -1):
        print(f"   {i}...")
        time.sleep(1)
    
    # Effectuer les clics comme dans _handle_trade_event
    for prop_name, owner in properties_to_click:
        coords = get_coordinates(prop_name, 'relative')
        if coords:
            rel_x, rel_y = coords
            
            # Transformer les coordonnées
            abs_x, abs_y, transformed_x, transformed_y = monitor.transform_coordinates(
                rel_x * win.width, 
                rel_y * win.height, 
                win
            )
            
            if abs_x is not None:
                print(f"\n🏠 Propriété: {prop_name} (appartient à {owner})")
                print(f"   - Coordonnées relatives: ({rel_x:.3f}, {rel_y:.3f})")
                print(f"   - Après transformation: ({transformed_x}, {transformed_y})")
                
                # Effectuer le clic
                monitor.perform_click(abs_x, abs_y, f"Clic sur {prop_name}")
            else:
                print(f"❌ Erreur de transformation pour {prop_name}")
        else:
            print(f"⚠️ Coordonnées introuvables pour {prop_name}")
    
    # Test d'un clic sur bouton avec offset
    print("\n📋 Test du clic sur bouton avec offset")
    button_x = win.left + win.width // 2
    button_y = win.top + win.height * 0.6  # 60% de la hauteur
    
    monitor.perform_click(button_x, button_y, "Clic sur bouton 'Propose'", y_offset=30)
    
    print("\n✅ Test terminé!")

def test_single_click():
    """Test d'un clic unique avec transformation en utilisant CentralizedMonitor"""
    
    print("\n🎯 Test de clic unique avec inverse_conversion")
    print("=" * 60)
    
    dolphin_windows = gw.getWindowsWithTitle("Dolphin")
    if not dolphin_windows:
        print("❌ Dolphin non trouvé")
        return
    
    win = dolphin_windows[0]
    
    # Créer une instance réelle de CentralizedMonitor
    monitor = CentralizedMonitor("http://localhost:5000")
    
    # Coordonnées de test (centre de l'écran)
    rel_x, rel_y = 0.5, 0.5
    
    print(f"\n📋 Test de clic au centre:")
    print(f"   Fenêtre: {win.width}x{win.height} à ({win.left}, {win.top})")
    print(f"   Coordonnées relatives: ({rel_x}, {rel_y})")
    
    # Calculer les coordonnées en pixels
    pixel_x = rel_x * win.width
    pixel_y = rel_y * win.height
    
    # Utiliser transform_coordinates de CentralizedMonitor
    abs_x, abs_y, transformed_x, transformed_y = monitor.transform_coordinates(pixel_x, pixel_y, win)
    
    if abs_x is not None:
        print(f"   Après transformation: ({transformed_x}, {transformed_y})")
        print(f"   Position absolue: ({abs_x}, {abs_y})")
        
        print("\n⏱️  Clic dans 2 secondes...")
        time.sleep(2)
        
        # Utiliser perform_click de CentralizedMonitor
        monitor.perform_click(abs_x, abs_y, "Test de clic au centre")
        
        print("✅ Clic effectué!")
    else:
        print("❌ Erreur de transformation")

if __name__ == "__main__":
    print("🧪 Test du système de trade Monopoly")
    print("=====================================\n")
    
    print("Options:")
    print("1. Test complet du trade avec données simulées")
    print("2. Test des coordonnées des propriétés (depuis JSON)")
    print("3. Test des clics sur propriétés (simule un trade)")
    print("4. Test d'un clic unique au centre")
    print("5. Tous les tests")
    
    choice = input("\nVotre choix (1-5): ").strip()
    
    if choice == "1":
        test_trade_with_mock_data()
    elif choice == "2":
        test_property_coordinates()
    elif choice == "3":
        test_property_clicks()
    elif choice == "4":
        test_single_click()
    elif choice == "5":
        test_property_coordinates()
        print("\n" + "=" * 60)
        test_property_clicks()
        print("\n" + "=" * 60)
        test_single_click()
        print("\n" + "=" * 60)
        test_trade_with_mock_data()
    else:
        print("❌ Choix invalide")