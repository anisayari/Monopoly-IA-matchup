#!/usr/bin/env python3
"""
Script de diagnostic pour la connexion Dolphin
"""

import dolphin_memory_engine as dme
import time
import sys

def test_connection():
    print("🔍 Test de connexion à Dolphin Memory Engine")
    print("="*50)
    
    # Test 1: Vérifier l'état initial
    print("\n1. État initial:")
    print(f"   is_hooked(): {dme.is_hooked()}")
    
    # Test 2: Essayer de se connecter
    print("\n2. Tentative de connexion...")
    try:
        dme.hook()
        print("   ✅ hook() appelé avec succès")
    except Exception as e:
        print(f"   ❌ Erreur lors de hook(): {e}")
    
    # Test 3: Vérifier à nouveau
    print("\n3. État après hook():")
    print(f"   is_hooked(): {dme.is_hooked()}")
    
    # Test 4: Essayer une lecture simple
    print("\n4. Test de lecture mémoire...")
    if dme.is_hooked():
        try:
            # Essayer de lire une adresse connue
            test_addr = 0x80000000  # Adresse de base GameCube/Wii
            data = dme.read_bytes(test_addr, 4)
            print(f"   ✅ Lecture réussie à 0x{test_addr:08X}: {data.hex()}")
        except Exception as e:
            print(f"   ❌ Erreur de lecture: {e}")
    else:
        print("   ⚠️  Pas connecté, impossible de lire")
    
    # Test 5: Informations additionnelles
    print("\n5. Informations système:")
    try:
        # Essayer d'obtenir des infos sur le processus
        import psutil
        dolphin_found = False
        for proc in psutil.process_iter(['pid', 'name']):
            if 'dolphin' in proc.info['name'].lower():
                print(f"   ✅ Processus Dolphin trouvé: {proc.info['name']} (PID: {proc.info['pid']})")
                dolphin_found = True
        if not dolphin_found:
            print("   ❌ Aucun processus Dolphin trouvé")
    except:
        print("   ⚠️  Impossible de vérifier les processus")

def test_alternative_connection():
    """Test avec différentes méthodes de connexion"""
    print("\n\n🔧 Test de connexions alternatives")
    print("="*50)
    
    # Méthode 1: Attendre un peu avant de vérifier
    print("\n1. Test avec délai:")
    dme.un_hook()  # S'assurer qu'on est déconnecté
    time.sleep(0.5)
    
    for i in range(5):
        try:
            dme.hook()
            time.sleep(0.5)  # Attendre que la connexion s'établisse
            if dme.is_hooked():
                print(f"   ✅ Connecté après {i+1} tentative(s)")
                return True
        except:
            pass
        print(f"   Tentative {i+1}/5...")
    
    print("   ❌ Impossible de se connecter après 5 tentatives")
    return False

def test_memory_addresses():
    """Test de lecture des adresses Monopoly"""
    print("\n\n📍 Test des adresses Monopoly")
    print("="*50)
    
    if not dme.is_hooked():
        print("❌ Non connecté à Dolphin")
        return
    
    # Tester quelques adresses du jeu
    test_addresses = [
        ("Player 1 Money", 0x9303DD5C),
        ("Player 2 Money", 0x9303DB6C),
        ("Old Kent Road Houses", 0x9303E327),
        ("Mayfair Houses", 0x9303F4DF)
    ]
    
    for name, addr in test_addresses:
        try:
            value = dme.read_bytes(addr, 4)
            print(f"\n{name} (0x{addr:08X}):")
            print(f"   Bytes: {value.hex()}")
            print(f"   Int32: {int.from_bytes(value, 'big')}")
            print(f"   Byte[0]: {value[0]}")
        except Exception as e:
            print(f"\n{name} (0x{addr:08X}):")
            print(f"   ❌ Erreur: {e}")

def main():
    print("\n🐬 DIAGNOSTIC DE CONNEXION DOLPHIN 🐬\n")
    
    # Test de base
    test_connection()
    
    # Si pas connecté, essayer méthode alternative
    if not dme.is_hooked():
        if test_alternative_connection():
            print("\n✅ Connexion établie avec méthode alternative!")
        else:
            print("\n❌ Impossible d'établir la connexion")
            print("\nVérifiez que:")
            print("  1. Dolphin est bien lancé")
            print("  2. Un jeu est en cours d'exécution (pas en pause)")
            print("  3. Dolphin n'est pas en mode 'Debug' exclusif")
            sys.exit(1)
    
    # Tester les adresses
    test_memory_addresses()
    
    print("\n\n✅ Diagnostic terminé!")

if __name__ == "__main__":
    main()