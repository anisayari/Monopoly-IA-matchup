import time
import sys
import dolphin_memory_engine as dme
from src.game.monopoly import MonopolyGame
from src.display.game_display import GameDisplay
from colorama import init, Fore, Style
import re

# Variables globales pour suivre l'état précédent du jeu
last_properties_display = 0
previous_game_state = {
    'blue_player': {},
    'red_player': {},
    'dialog_roll_dice': ('', ''),
    'dialog_auction': ('', '', ''),
    'current_player': '',
    'end_of_turn': False,
    'end_of_turn_displayed': False,  # Pour éviter d'afficher plusieurs fois le même message
    'last_property_offer': ('', 0)   # (nom_propriété, prix) pour éviter les répétitions
}

def print_game_state(game: MonopolyGame):
    """Affiche l'état actuel du jeu"""
    try:
        # Informations sur les joueurs
        print(f"\n{Fore.BLUE}Joueur Bleu ({game.blue_player.name}): ${game.blue_player.money} - Position: {game.blue_player.position}{Style.RESET_ALL}")
        print(f"{Fore.RED}Joueur Rouge ({game.red_player.name}): ${game.red_player.money} - Position: {game.red_player.position}{Style.RESET_ALL}")
        
        # Dialogue en cours
        try:
            dialog_title = game.dialog_title
            dialog_message = game.dialog_message
            if dialog_title or dialog_message:
                print(f"\n{Fore.MAGENTA}Dialogue en cours:{Style.RESET_ALL}")
                if dialog_title:
                    print(f"{Fore.MAGENTA}Titre: {dialog_title}{Style.RESET_ALL}")
                if dialog_message:
                    print(f"{Fore.MAGENTA}Message: {dialog_message}{Style.RESET_ALL}")
        except AttributeError:
            print(f"\n{Fore.YELLOW}Dialogue non disponible{Style.RESET_ALL}")
        
        # Enchère en cours
        try:
            auction_message, auction_purchaser, auction_name = game.dialog_auction
            if auction_message or auction_purchaser or auction_name:
                print(f"\n{Fore.RED}Enchère en cours:{Style.RESET_ALL}")
                if auction_message:
                    print(f"{Fore.RED}Message: {auction_message}{Style.RESET_ALL}")
                if auction_purchaser:
                    print(f"{Fore.RED}Acheteur: {auction_purchaser}{Style.RESET_ALL}")
                if auction_name:
                    print(f"{Fore.RED}Propriété: {auction_name}{Style.RESET_ALL}")
        except AttributeError:
            print(f"\n{Fore.YELLOW}Enchère non disponible{Style.RESET_ALL}")
        
        # Propriétés disponibles
        if hasattr(game, 'properties') and game.properties:
            print(f"\n{Fore.CYAN}Liste des propriétés disponibles:{Style.RESET_ALL}")
            for prop in game.properties:
                print(f"{Fore.CYAN}Nom: {prop.name} | Prix: ${prop.price} | Hypothèque: ${prop.mortgage} | Coût maison: ${prop.house_cost}{Style.RESET_ALL}")
                print(f"{Fore.CYAN}Loyers: ${prop.rents[0]} (0 maison), ${prop.rents[1]} (1 maison), ${prop.rents[2]} (2 maisons), ${prop.rents[3]} (3 maisons), ${prop.rents[4]} (4 maisons), ${prop.rents[5]} (hôtel){Style.RESET_ALL}")
        else:
            print(f"\n{Fore.YELLOW}Propriétés non disponibles{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}Erreur lors de l'affichage de l'état du jeu: {str(e)}{Style.RESET_ALL}")

def display_game_state(game: MonopolyGame):
    """Affiche l'état actuel du jeu dans le format demandé, uniquement si des changements sont détectés"""
    global previous_game_state
    
    try:
        # Récupérer l'état actuel du jeu
        current_state = {
            'blue_player': {
                'label': game.blue_player.label,
                'money': game.blue_player.money,
                'position': game.blue_player.position,
                'goto': game.blue_player.goto,
                'dices': game.blue_player.dices
            },
            'red_player': {
                'label': game.red_player.label,
                'money': game.red_player.money,
                'position': game.red_player.position,
                'goto': game.red_player.goto,
                'dices': game.red_player.dices
            },
            'dialog_roll_dice': game.dialog_roll_dice,
            'dialog_auction': game.dialog_auction,
            'current_player': previous_game_state.get('current_player', ''),
            'end_of_turn': previous_game_state.get('end_of_turn', False),
            'end_of_turn_displayed': previous_game_state.get('end_of_turn_displayed', False),
            'last_property_offer': previous_game_state.get('last_property_offer', ('', 0))
        }
        
        # Vérifier si un nouveau tour a commencé
        _, message = game.dialog_roll_dice
        if message:
            detect_new_turn(game, message)
            
            # Mettre à jour l'état actuel avec les nouvelles valeurs
            current_state['end_of_turn'] = previous_game_state['end_of_turn']
            current_state['end_of_turn_displayed'] = previous_game_state['end_of_turn_displayed']
            current_state['current_player'] = previous_game_state['current_player']
        
        # Vérifier s'il y a un message d'achat de propriété
        buy_message = game.dialog_buy_property
        if buy_message:
            property_handled = handle_property_purchase(game, buy_message)
            if property_handled:
                # Si une opportunité d'achat a été affichée, mettre à jour l'état actuel
                current_state['last_property_offer'] = previous_game_state['last_property_offer']
        
        # Vérifier s'il y a des changements
        has_changes = False
        
        # Vérifier les changements pour les joueurs
        for player_key in ['blue_player', 'red_player']:
            if previous_game_state.get(player_key) != current_state[player_key]:
                has_changes = True
                break
        
        # Vérifier les changements pour les dialogues
        if (previous_game_state.get('dialog_roll_dice') != current_state['dialog_roll_dice'] or
            previous_game_state.get('dialog_auction') != current_state['dialog_auction']):
            has_changes = True
        
        # Si aucun changement, ne rien afficher
        if not has_changes:
            return
        
        # État des joueurs
        for player, color in [(game.blue_player, 'blue'), (game.red_player, 'red')]:
            game._display.update_player(color, {
                'label': player.label,
                'money': player.money,
                'position': player.position,
                'goto': player.goto,
                'dices': player.dices
            })
        
        # État des dialogues
        title, message = game.dialog_roll_dice
        game._display.update_dialog(title, message)
        
        # État des enchères
        auction_message, purchaser, name = game.dialog_auction
        game._display.update_auction(auction_message, purchaser, name)
        
        # Mettre à jour l'état précédent
        previous_game_state = current_state
    except Exception as e:
        print(f"\n{Fore.RED}Erreur lors de l'affichage de l'état du jeu: {str(e)}{Style.RESET_ALL}")

def display_properties(game: MonopolyGame):
    """Affiche la liste des propriétés une seule fois"""
    try:
        game._display.print_info("Liste des propriétés disponibles:")
        for prop in game.properties:
            loyers = ", ".join([f"${rent}" for rent in prop.rents])
            game._display.print_property(
                f"{prop.name} - Prix: ${prop.price} | "
                f"Hypothèque: ${prop.mortgage} | "
                f"Maison: ${prop.house_cost} | "
                f"Loyers: [{loyers}]"
            )
    except Exception as e:
        print(f"\n{Fore.RED}Erreur lors de l'affichage des propriétés: {str(e)}{Style.RESET_ALL}")

def setup_custom_memory_searches(game):
    """Configure des recherches de texte en mémoire personnalisées"""
    try:
        print(f"\n{Fore.YELLOW}Configuration de recherches de texte personnalisées...{Style.RESET_ALL}")
        
        # Patterns binaires pour les recherches personnalisées
        chance_pattern = re.compile(b'C\x00h\x00a\x00n\x00c\x00e\x00', re.DOTALL)
        community_pattern = re.compile(b'C\x00o\x00m\x00m\x00u\x00n\x00i\x00t\x00y\x00', re.DOTALL)
        win_pattern = re.compile(b'W\x00i\x00n\x00n\x00e\x00r\x00', re.DOTALL)
        
        # Pattern pour détecter "What would you like to do?" (fin de tour)
        # Utiliser un pattern plus court pour augmenter les chances de détection
        end_turn_pattern = re.compile(b'W\x00h\x00a\x00t\x00 \x00w\x00o\x00u\x00l\x00d\x00', re.DOTALL)
        
        # Pattern pour détecter les messages d'achat de propriété
        # Utiliser un pattern plus court pour augmenter les chances de détection
        buy_property_pattern = re.compile(b'b\x00u\x00y\x00', re.DOTALL)
        
        # Exemple de recherche personnalisée pour les cartes chance
        def chance_card_callback(addr, text):
            # Extraire uniquement le texte pertinent
            if text:
                # Chercher le texte réel de la carte après "Chance"
                if "Chance" in text:
                    # Extraire le texte après "Chance"
                    card_text = text.split("Chance", 1)[1].strip()
                    # Nettoyer le texte
                    card_text = re.sub(r'[^\x20-\x7E\n]', '', card_text)
                    # Afficher le texte de la carte
                    game._display.print_info(f"Carte Chance: {card_text}")
                    
        # Exemple de recherche personnalisée pour les cartes communauté
        def community_card_callback(addr, text):
            # Extraire uniquement le texte pertinent
            if text:
                # Chercher le texte réel de la carte après "Community"
                if "Community" in text:
                    # Extraire le texte après "Community"
                    card_text = text.split("Community", 1)[1].strip()
                    # Nettoyer le texte
                    card_text = re.sub(r'[^\x20-\x7E\n]', '', card_text)
                    # Afficher le texte de la carte
                    game._display.print_info(f"Carte Communauté: {card_text}")
                    
        # Exemple de recherche personnalisée pour détecter un gagnant
        def win_callback(addr, text):
            # Extraire uniquement le texte pertinent
            if text:
                # Chercher le texte réel après "Winner"
                if "Winner" in text:
                    # Extraire le texte après "Winner"
                    winner_text = text.split("Winner", 1)[1].strip()
                    # Nettoyer le texte
                    winner_text = re.sub(r'[^\x20-\x7E\n]', '', winner_text)
                    # Afficher le texte du gagnant
                    game._display.print_info(f"GAGNANT: {winner_text}")
        
        # Callback pour détecter la fin d'un tour
        def end_turn_callback(addr, text):
            global previous_game_state
            
            if text:
                # Utiliser une condition plus large pour détecter la fin d'un tour
                if "What would" in text and "like to do" in text:
                    # Stocker l'adresse mémoire pour éviter les détections répétitives
                    if hasattr(end_turn_callback, 'last_addr') and end_turn_callback.last_addr == addr:
                        return
                    end_turn_callback.last_addr = addr
                    
                    # Déterminer le joueur actuel
                    current_player = "Inconnu"
                    title, message = game.dialog_roll_dice
                    if title:
                        current_player = title
                    
                    # Ne mettre à jour l'état que si ce n'est pas déjà la fin d'un tour
                    # ou si c'est un joueur différent
                    if not previous_game_state['end_of_turn'] or previous_game_state['current_player'] != current_player:
                        # Mettre à jour l'état du jeu
                        previous_game_state['current_player'] = current_player
                        previous_game_state['end_of_turn'] = True
                        previous_game_state['end_of_turn_displayed'] = False  # Réinitialiser pour permettre l'affichage
                        
                        # Déterminer la couleur du joueur
                        player_color = 'blue' if current_player.lower() == 'ayari' else 'red'
                        color_code = Fore.BLUE if player_color == 'blue' else Fore.RED
                        
                        # Créer une bordure pour rendre le message plus visible
                        border = f"{color_code}{'=' * 60}{Style.RESET_ALL}"
                        
                        # Afficher le message de fin de tour dans la couleur du joueur
                        print(f"\n{border}")
                        print(f"{color_code}🎮 FIN DU TOUR DE {current_player.upper()} 🎮{Style.RESET_ALL}")
                        print(f"{color_code}Options disponibles: Lancer les dés, Gérer les propriétés, etc.{Style.RESET_ALL}")
                        print(f"{border}")
                        
                        # Marquer le message comme affiché
                        previous_game_state['end_of_turn_displayed'] = True
        
        # Callback pour détecter les messages d'achat de propriété
        def buy_property_callback(addr, text):
            if text:
                # Vérifier si le texte contient des mots-clés d'achat
                buy_keywords = ["buy", "purchase", "want to buy", "do you want"]
                if any(keyword in text.lower() for keyword in buy_keywords):
                    # Stocker le dernier message traité pour éviter les répétitions
                    if hasattr(buy_property_callback, 'last_message') and buy_property_callback.last_message == text:
                        return
                    buy_property_callback.last_message = text
                    
                    # Traiter le message d'achat
                    handle_property_purchase(game, text)
        
        # Démarrer les recherches personnalisées
        game.start_custom_memory_search(
            pattern=chance_pattern,
            callback=chance_card_callback,
            search_id="custom_chance_card",
            is_binary=True
        )
        
        game.start_custom_memory_search(
            pattern=community_pattern,
            callback=community_card_callback,
            search_id="custom_community_card",
            is_binary=True
        )
        
        game.start_custom_memory_search(
            pattern=win_pattern,
            callback=win_callback,
            search_id="custom_win_state",
            is_binary=True
        )
        
        # Démarrer la recherche pour détecter la fin d'un tour
        game.start_custom_memory_search(
            pattern=end_turn_pattern,
            callback=end_turn_callback,
            search_id="custom_end_turn",
            is_binary=True
        )
        
        # Démarrer la recherche pour détecter les messages d'achat de propriété
        game.start_custom_memory_search(
            pattern=buy_property_pattern,
            callback=buy_property_callback,
            search_id="custom_buy_property",
            is_binary=True
        )
        
        print(f"{Fore.YELLOW}Recherches personnalisées configurées.{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}Erreur lors de la configuration des recherches personnalisées: {str(e)}{Style.RESET_ALL}")

def detect_new_turn(game, message):
    """Détecte le début d'un nouveau tour et réinitialise l'état de fin de tour"""
    global previous_game_state
    
    # Vérifier si c'est un message de début de tour
    if "shake the Wii Remote" in message and "to roll the dice" in message:
        # Mettre à jour le joueur actuel
        title, _ = game.dialog_roll_dice
        if title:
            # Si le joueur a changé ou si c'était la fin d'un tour
            if previous_game_state.get('current_player') != title or previous_game_state.get('end_of_turn', False):
                # Réinitialiser l'état de fin de tour
                previous_game_state['end_of_turn'] = False
                previous_game_state['end_of_turn_displayed'] = False
                
                # Mettre à jour le joueur actuel seulement s'il a changé
                if previous_game_state.get('current_player') != title:
                    previous_game_state['current_player'] = title
                    
                    # Afficher un message de début de tour
                    player_color = 'blue' if title.lower() == 'ayari' else 'red'
                    color_code = Fore.BLUE if player_color == 'blue' else Fore.RED
                    
                    # Créer une bordure pour rendre le message plus visible
                    border = f"{color_code}{'=' * 60}{Style.RESET_ALL}"
                    
                    # Afficher le message de début de tour dans la couleur du joueur
                    print(f"\n{border}")
                    print(f"{color_code}🎲 DÉBUT DU TOUR DE {title.upper()} 🎲{Style.RESET_ALL}")
                    print(f"{border}")

def handle_property_purchase(game, message):
    """Gère l'affichage des messages d'achat de propriété en évitant les répétitions"""
    global previous_game_state
    
    # Nettoyer le message
    cleaned_message = ""
    for char in message:
        if (32 <= ord(char) <= 126) or ('À' <= char <= 'ÿ') or char in ['€', '£', '¥', '©', '®', '™', '°', '±', '²', '³', '¼', '½', '¾']:
            cleaned_message += char
        else:
            # Arrêter au premier caractère non imprimable
            break
    
    # Vérifier que le message contient des mots-clés d'achat
    keywords = ["buy", "purchase", "would you like"]
    if not any(keyword in cleaned_message.lower() for keyword in keywords):
        return False
    
    # Rechercher le nom de la propriété et le prix
    property_match = re.search(r"buy\s+([A-Za-z\s\.]+(?:Station|Avenue|Road|Street|Lane|Place|Gardens|Square|Park|Boardwalk|Walk))\s+for\s+\$?(\d+|\~\d+)", cleaned_message, re.IGNORECASE)
    if not property_match:
        # Essayer un autre pattern pour "Do you want to buy X for Y"
        property_match = re.search(r"want to buy\s+([A-Za-z\s\.]+(?:Station|Avenue|Road|Street|Lane|Place|Gardens|Square|Park|Boardwalk|Walk))\s+for\s+\$?(\d+|\~\d+)", cleaned_message, re.IGNORECASE)
    
    if property_match:
        property_name = property_match.group(1).strip()
        property_price = property_match.group(2).strip().replace('~', '')
        
        # Convertir le prix en nombre si possible
        try:
            price_value = int(property_price)
        except ValueError:
            price_value = 0
        
        # Vérifier si c'est la même propriété que la dernière fois
        last_property, last_price = previous_game_state['last_property_offer']
        
        # Toujours afficher l'opportunité d'achat au début du jeu
        # ou si la propriété est différente de la dernière fois
        if property_name != last_property or price_value != last_price:
            # Déterminer le joueur actuel
            current_player = previous_game_state.get('current_player', 'Inconnu')
            
            # Créer une bordure pour rendre le message plus visible
            border = f"{Fore.YELLOW}{'=' * 60}{Style.RESET_ALL}"
            
            # Afficher le message d'achat avec une bordure jaune pour plus de visibilité
            print(f"\n{border}")
            print(f"{Fore.YELLOW}💰 OPPORTUNITÉ D'ACHAT 💰{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}{current_player.upper()} peut acheter la propriété {property_name} au prix de ${property_price}{Style.RESET_ALL}")
            print(f"{border}")
            
            # Mettre à jour la dernière offre
            previous_game_state['last_property_offer'] = (property_name, price_value)
            
            # Retourner True pour indiquer qu'une opportunité d'achat a été affichée
            return True
    else:
        # Si aucun match n'est trouvé mais que le message contient des mots-clés d'achat,
        # afficher le message brut pour le débogage une seule fois
        last_property, _ = previous_game_state['last_property_offer']
        if last_property != cleaned_message:
            print(f"\n{Fore.YELLOW}💵 ACHAT DE PROPRIÉTÉ: {cleaned_message}{Style.RESET_ALL}")
            previous_game_state['last_property_offer'] = (cleaned_message, 0)
    
    # Retourner False si aucune opportunité d'achat n'a été affichée
    return False

def main():
    """Fonction principale"""
    # Initialiser colorama pour les couleurs dans le terminal
    init()
    
    print(f"{Fore.GREEN}Initialisation du jeu Monopoly...{Style.RESET_ALL}")
    
    try:
        # Créer une instance du jeu
        game = MonopolyGame()
        
        # Configurer les joueurs
        game.blue_player.name = "Ayari"
        game.red_player.name = "Claude"
        game.blue_player.money = 5000
        game.red_player.money = 5000
        
        # Initialiser le joueur actuel (par défaut, c'est le joueur bleu qui commence)
        global previous_game_state
        previous_game_state['current_player'] = "Ayari"
        previous_game_state['last_property_offer'] = ('', 0)  # Initialiser pour éviter les erreurs
        
        # Afficher un message de début de tour pour le premier joueur
        border = f"{Fore.BLUE}{'=' * 60}{Style.RESET_ALL}"
        print(f"\n{border}")
        print(f"{Fore.BLUE}🎲 DÉBUT DU TOUR DE AYARI 🎲{Style.RESET_ALL}")
        print(f"{border}")
        
        # Afficher l'état initial du jeu et la liste des propriétés une seule fois
        print_game_state(game)
        display_properties(game)
        
        # Ajouter des recherches personnalisées
        setup_custom_memory_searches(game)
        
        print(f"\n{Fore.GREEN}Surveillance des changements en cours... (Ctrl+C pour arrêter){Style.RESET_ALL}")
        print(f"{Fore.GREEN}Les adresses mémoire trouvées seront automatiquement enregistrées et utilisées.{Style.RESET_ALL}")
        
        # Compteur pour afficher l'état du jeu périodiquement
        last_state_display = time.time()
        
        # Boucle principale
        while True:
            # Vérifier l'état du jeu moins fréquemment (toutes les 1 secondes)
            # mais n'afficher que s'il y a des changements
            current_time = time.time()
            if current_time - last_state_display >= 1.0:
                display_game_state(game)
                last_state_display = current_time
            
            # Pause pour éviter de surcharger le CPU
            time.sleep(0.2)
            
            # Afficher les adresses trouvées toutes les 10 secondes
            if int(time.time()) % 10 == 0:
                try:
                    addresses = game._dynamic_addresses
                    if addresses:
                        print(f"\n{Fore.CYAN}Adresses mémoire trouvées:{Style.RESET_ALL}")
                        for key, addr in addresses.items():
                            print(f"{Fore.CYAN}{key}: 0x{addr:08X}{Style.RESET_ALL}")
                except Exception as e:
                    print(f"\n{Fore.RED}Erreur lors de l'affichage des adresses: {str(e)}{Style.RESET_ALL}")
            
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Arrêt du programme demandé par l'utilisateur.{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}Erreur: {str(e)}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            print(f"{Fore.GREEN}Nettoyage et fermeture...{Style.RESET_ALL}")
            # Le nettoyage est géré par le destructeur de MonopolyGame
        except Exception as e:
            print(f"\n{Fore.RED}Erreur lors du nettoyage: {str(e)}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
    
    
    
    
