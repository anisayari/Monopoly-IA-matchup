import time
import sys
import dolphin_memory_engine as dme
from src.game.monopoly import MonopolyGame
from colorama import init, Fore, Style
import re

# Ajouter une variable globale pour suivre le dernier affichage des propriétés
last_properties_display = 0

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
    """Affiche l'état actuel du jeu dans le format demandé"""
    global last_properties_display
    current_time = time.time()
    
    try:
        game._display.print_info("=== État actuel du jeu ===")
        
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
        
        # N'afficher la liste des propriétés que lors de la première exécution ou toutes les 30 secondes
        if last_properties_display == 0 or (current_time - last_properties_display >= 30):
            game._display.print_info("Liste des propriétés disponibles:")
            for prop in game.properties:
                loyers = ", ".join([f"${rent}" for rent in prop.rents])
                game._display.print_property(
                    f"{prop.name} - Prix: ${prop.price} | "
                    f"Hypothèque: ${prop.mortgage} | "
                    f"Maison: ${prop.house_cost} | "
                    f"Loyers: [{loyers}]"
                )
            last_properties_display = current_time
    except Exception as e:
        print(f"\n{Fore.RED}Erreur lors de l'affichage de l'état du jeu: {str(e)}{Style.RESET_ALL}")

def setup_custom_memory_searches(game):
    """Configure des recherches de texte en mémoire personnalisées"""
    try:
        print(f"\n{Fore.YELLOW}Configuration de recherches de texte personnalisées...{Style.RESET_ALL}")
        
        # Patterns binaires pour les recherches personnalisées
        chance_pattern = re.compile(b'C\x00h\x00a\x00n\x00c\x00e\x00', re.DOTALL)
        community_pattern = re.compile(b'C\x00o\x00m\x00m\x00u\x00n\x00i\x00t\x00y\x00', re.DOTALL)
        win_pattern = re.compile(b'W\x00i\x00n\x00n\x00e\x00r\x00', re.DOTALL)
        
        # Exemple de recherche personnalisée pour les cartes chance
        def chance_card_callback(addr, text):
            # Extraire uniquement le texte pertinent
            if text:
                # Chercher le texte réel de la carte après "Chance"
                if "Chance" in text:
                    # Chercher le texte réel après "Chance"
                    parts = text.split("Chance")
                    if len(parts) > 1:
                        # Chercher le texte réel dans les données binaires
                        real_text = ""
                        for i in range(addr + 20, addr + 500, 2):  # Chercher dans les 500 octets suivants
                            try:
                                char_bytes = dme.read_bytes(i, 2)
                                if char_bytes == b"\x00\x00":
                                    continue
                                char = char_bytes.decode("utf-16-le", errors="ignore")
                                if char and (32 <= ord(char) <= 126):  # ASCII imprimable
                                    real_text += char
                                else:
                                    # Si on a déjà du texte et qu'on rencontre un caractère non imprimable,
                                    # on considère que c'est la fin du texte
                                    if real_text and len(real_text) > 10:
                                        break
                            except:
                                pass
                        
                        if real_text:
                            # Nettoyer le texte (enlever les caractères non imprimables)
                            clean_text = ''.join(c for c in real_text if 32 <= ord(c) <= 126)
                            print(f"{Fore.YELLOW}✨ Carte Chance trouvée à 0x{addr:08X}: {clean_text}{Style.RESET_ALL}")
                            return
                
                # Si on n'a pas trouvé de texte réel, afficher juste "Chance"
                print(f"{Fore.YELLOW}✨ Carte Chance trouvée à 0x{addr:08X}: Chance{Style.RESET_ALL}")
        
        game.start_custom_memory_search(
            pattern=chance_pattern,
            callback=chance_card_callback,
            search_id="custom_chance_cards",
            is_binary=True
        )
        
        # Exemple de recherche personnalisée pour les cartes communauté
        def community_card_callback(addr, text):
            # Extraire uniquement le texte pertinent
            if text:
                # Chercher le texte réel de la carte après "Community Chest"
                if "Community" in text:
                    # Chercher le texte réel après "Community Chest"
                    parts = text.split("Community")
                    if len(parts) > 1:
                        # Chercher le texte réel dans les données binaires
                        real_text = ""
                        for i in range(addr + 30, addr + 500, 2):  # Chercher dans les 500 octets suivants
                            try:
                                char_bytes = dme.read_bytes(i, 2)
                                if char_bytes == b"\x00\x00":
                                    continue
                                char = char_bytes.decode("utf-16-le", errors="ignore")
                                if char and (32 <= ord(char) <= 126):  # ASCII imprimable
                                    real_text += char
                                else:
                                    # Si on a déjà du texte et qu'on rencontre un caractère non imprimable,
                                    # on considère que c'est la fin du texte
                                    if real_text and len(real_text) > 10:
                                        break
                            except:
                                pass
                        
                        if real_text:
                            # Nettoyer le texte (enlever les caractères non imprimables)
                            clean_text = ''.join(c for c in real_text if 32 <= ord(c) <= 126)
                            print(f"{Fore.YELLOW}✨ Carte Communauté trouvée à 0x{addr:08X}: {clean_text}{Style.RESET_ALL}")
                            return
                
                # Si on n'a pas trouvé de texte réel, afficher juste "Community Chest"
                print(f"{Fore.YELLOW}✨ Carte Communauté trouvée à 0x{addr:08X}: Community Chest{Style.RESET_ALL}")
        
        game.start_custom_memory_search(
            pattern=community_pattern,
            callback=community_card_callback,
            search_id="custom_community_cards",
            is_binary=True
        )        
        # Exemple de recherche personnalisée pour les messages de victoire
        def win_callback(addr, text):
            # Extraire uniquement le texte pertinent
            if text:
                # Chercher le texte réel après "Winner"
                if "Winner" in text:
                    # Chercher le texte réel dans les données binaires
                    real_text = ""
                    for i in range(addr + 20, addr + 500, 2):  # Chercher dans les 500 octets suivants
                        try:
                            char_bytes = dme.read_bytes(i, 2)
                            if char_bytes == b"\x00\x00":
                                continue
                            char = char_bytes.decode("utf-16-le", errors="ignore")
                            if char and (32 <= ord(char) <= 126):  # ASCII imprimable
                                real_text += char
                            else:
                                # Si on a déjà du texte et qu'on rencontre un caractère non imprimable,
                                # on considère que c'est la fin du texte
                                if real_text and len(real_text) > 10:
                                    break
                        except:
                            pass
                    
                    if real_text:
                        # Nettoyer le texte (enlever les caractères non imprimables)
                        clean_text = ''.join(c for c in real_text if 32 <= ord(c) <= 126)
                        print(f"{Fore.GREEN}🏆 Victoire trouvée à 0x{addr:08X}: {clean_text}{Style.RESET_ALL}")
                        return
            
            # Si on n'a pas trouvé de texte réel, afficher juste le texte original
            print(f"{Fore.GREEN}🏆 Victoire trouvée à 0x{addr:08X}: {text}{Style.RESET_ALL}")
        
        game.start_custom_memory_search(
            pattern=win_pattern,
            callback=win_callback,
            search_id="custom_win_state",
            is_binary=True
        )
        
        print(f"{Fore.YELLOW}Recherches personnalisées configurées.{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}Erreur lors de la configuration des recherches personnalisées: {str(e)}{Style.RESET_ALL}")

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
        
        # Afficher l'état initial du jeu
        print_game_state(game)
        
        # Ajouter des recherches personnalisées
        setup_custom_memory_searches(game)
        
        print(f"\n{Fore.GREEN}Surveillance des changements en cours... (Ctrl+C pour arrêter){Style.RESET_ALL}")
        print(f"{Fore.GREEN}Les adresses mémoire trouvées seront automatiquement enregistrées et utilisées.{Style.RESET_ALL}")
        
        # Afficher l'état du jeu dans le format demandé
        display_game_state(game)
        
        # Compteur pour afficher l'état du jeu périodiquement
        last_state_display = time.time()
        
        # Boucle principale
        while True:
            # Afficher l'état du jeu toutes les 5 secondes
            current_time = time.time()
            if current_time - last_state_display >= 5:
                display_game_state(game)
                last_state_display = current_time
            
            # Afficher les adresses trouvées toutes les 10 secondes
            if int(time.time()) % 10 == 0:
                try:
                    addresses = game._dynamic_addresses
                    if addresses:
                        print(f"\n{Fore.CYAN}Adresses mémoire trouvées:{Style.RESET_ALL}")
                        for key, addr in addresses.items():
                            print(f"{Fore.CYAN}{key}: 0x{addr:08X}{Style.RESET_ALL}")
                    time.sleep(1)  # Éviter d'afficher plusieurs fois par seconde
                except Exception as e:
                    print(f"\n{Fore.RED}Erreur lors de l'affichage des adresses: {str(e)}{Style.RESET_ALL}")
            
            time.sleep(0.1)  # Pause courte pour réduire l'utilisation CPU
            
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
    
    
    
    
