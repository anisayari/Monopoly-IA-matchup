#!/usr/bin/env python3
"""
Script de test pour lire l'état de toutes les propriétés du Monopoly
Affiche: nom, prix, nombre de maisons, hypothèque, etc.
"""

import dolphin_memory_engine as dme
import json
import os
import sys
from tabulate import tabulate
from colorama import init, Fore, Style

# Initialiser colorama pour Windows
init()

# Ajouter le dossier racine au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.property import Property
from src.core.game_loader import GameLoader
from src.game.monopoly import MonopolyGame

def connect_to_dolphin():
    """Se connecte à Dolphin Memory Engine"""
    try:
        dme.hook()
        print(f"{Fore.GREEN}✅ Connecté à Dolphin{Style.RESET_ALL}")
        return True
    except Exception as e:
        print(f"{Fore.RED}❌ Erreur de connexion à Dolphin: {e}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Assurez-vous que Dolphin est lancé avec un jeu en cours{Style.RESET_ALL}")
        return False

def load_property_data():
    """Charge les données des propriétés depuis MonopolyProperties.json"""
    try:
        json_path = os.path.join('game_files', 'MonopolyProperties.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {prop['name']: prop for prop in data['properties']}
    except Exception as e:
        print(f"{Fore.RED}❌ Erreur lors du chargement de MonopolyProperties.json: {e}{Style.RESET_ALL}")
        return {}

def get_property_color(prop_name, property_data):
    """Retourne la couleur d'une propriété basée sur son groupe"""
    groups = {
        'Brown': ['Old Kent Road', 'Whitechapel Road'],
        'Light Blue': ['The Angel Islington', 'Euston Road', 'Pentonville Road'],
        'Pink': ['Pall Mall', 'Whitehall', 'Northumberland Avenue'],
        'Orange': ['Bow Street', 'Marlborough Street', 'Vine Street'],
        'Red': ['The Strand', 'Fleet Street', 'Trafalgar Square'],
        'Yellow': ['Leicester Square', 'Coventry Street', 'Piccadilly'],
        'Green': ['Regent Street', 'Oxford Street', 'Bond Street'],
        'Dark Blue': ['Park Lane', 'Mayfair'],
        'Station': ['Kings Cross Station', 'Marylebone Station', 'Fenchurch St Station', 'Liverpool St Station'],
        'Utility': ['Electric Company', 'Water Works']
    }
    
    for group, props in groups.items():
        if prop_name in props:
            return group
    return 'Unknown'

def get_all_properties_from_game():
    """Récupère toutes les propriétés de tous les joueurs"""
    try:
        # Charger le jeu
        loader = GameLoader("game_files/starting_state.jsonc", "game_files/starting_state.sav")
        game = MonopolyGame(loader)
        
        all_properties = []
        
        # Parcourir tous les joueurs
        for player in game.players:
            print(f"\n{Fore.YELLOW}🎮 Joueur {player.id} - {player.name}{Style.RESET_ALL}")
            
            # Récupérer les propriétés du joueur
            for prop in player.owned_properties:
                prop_dict = {
                    'name': prop.name,
                    'price': prop.price,
                    'position': prop.position,
                    'owner': player.name,
                    'owner_id': player.id,
                    'base': prop._base
                }
                all_properties.append(prop_dict)
                
        return all_properties
        
    except Exception as e:
        print(f"{Fore.RED}❌ Erreur lors de la récupération des propriétés: {e}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()
        return []

def main():
    """Fonction principale"""
    print(f"\n{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}📊 Test de lecture de l'état des propriétés Monopoly{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
    
    # Se connecter à Dolphin
    if not connect_to_dolphin():
        return
    
    # Charger les données des propriétés
    property_data = load_property_data()
    
    # Récupérer toutes les propriétés depuis la RAM
    print(f"\n{Fore.YELLOW}🔍 Lecture des propriétés depuis la RAM...{Style.RESET_ALL}")
    properties = get_all_properties_from_game()
    
    if not properties:
        print(f"{Fore.RED}❌ Aucune propriété trouvée dans la RAM{Style.RESET_ALL}")
        return
    
    # Préparer les données pour l'affichage
    table_data = []
    
    for prop_dict in properties:
        prop_name = prop_dict.get('name', 'Unknown')
        
        # Récupérer le nombre de maisons
        house_count = Property.get_house_count_for_property(prop_name)
        if house_count is None:
            house_count = 0
        
        # Récupérer le statut d'hypothèque
        is_mortgaged = Property.is_property_mortgaged(prop_name)
        
        # Récupérer les infos supplémentaires depuis le JSON
        prop_info = property_data.get(prop_name, {})
        
        # Déterminer le statut de construction
        if house_count == 5:
            build_status = "🏨 Hôtel"
            build_color = Fore.MAGENTA
        elif house_count > 0:
            build_status = f"🏠 {house_count} maison{'s' if house_count > 1 else ''}"
            build_color = Fore.GREEN
        else:
            build_status = "🏞️ Terrain nu"
            build_color = Fore.WHITE
        
        # Statut d'hypothèque
        if is_mortgaged:
            mortgage_status = "❌ Hypothéquée"
            mortgage_color = Fore.RED
        else:
            mortgage_status = "✅ Libre"
            mortgage_color = Fore.GREEN
        
        # Groupe/couleur
        group = get_property_color(prop_name, property_data)
        
        # Ajouter à la table
        table_data.append([
            prop_name,
            group,
            prop_dict.get('owner', 'Unknown'),
            f"${prop_dict.get('price', 0)}",
            f"{build_color}{build_status}{Style.RESET_ALL}",
            f"{mortgage_color}{mortgage_status}{Style.RESET_ALL}",
            f"${prop_info.get('mortgage', 0)}",
            f"${prop_info.get('houseCost', 0)}" if group not in ['Station', 'Utility'] else "N/A"
        ])
    
    # Afficher le tableau
    headers = ["Propriété", "Groupe", "Propriétaire", "Prix", "Construction", "Statut", "Valeur Hyp.", "Coût Maison"]
    print(f"\n{Fore.CYAN}📋 État des propriétés:{Style.RESET_ALL}\n")
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Statistiques
    total_properties = len(properties)
    mortgaged_count = sum(1 for row in table_data if "Hypothéquée" in row[5])
    with_houses = sum(1 for row in table_data if "maison" in row[4] or "Hôtel" in row[4])
    
    print(f"\n{Fore.CYAN}📊 Statistiques:{Style.RESET_ALL}")
    print(f"  • Total des propriétés: {total_properties}")
    print(f"  • Propriétés hypothéquées: {mortgaged_count}")
    print(f"  • Propriétés avec constructions: {with_houses}")
    
    # Test des fonctions individuelles sur une propriété
    if properties:
        test_prop = properties[0]
        print(f"\n{Fore.CYAN}🔬 Test détaillé sur '{test_prop['name']}':{Style.RESET_ALL}")
        
        # Créer une instance Property
        prop = Property(test_prop['base'])
        info = prop.get_property_info()
        
        print(f"  • Nom: {info['name']}")
        print(f"  • Prix: ${info['price']}")
        print(f"  • Coût maison: ${info['house_cost']}")
        print(f"  • Valeur hypothèque: ${info['mortgage']}")
        print(f"  • Est hypothéquée: {'Oui' if info['is_mortgaged'] else 'Non'}")
        print(f"  • Prix pour 3 maisons: ${info['set_price_3_houses']}")
        print(f"  • Prix de revente maison: ${info['house_sell_price']}")
        print(f"  • Prix pour lever hypothèque: ${info['unmortgage_price']}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Arrêt du script...{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}❌ Erreur inattendue: {e}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()