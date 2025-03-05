import time
import sys
import dolphin_memory_engine as dme
from src.game.monopoly import MonopolyGame
from colorama import init, Fore, Style

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
        game._game_state['current_player'] = "Ayari"
        game._game_state['last_property_offer'] = ('', 0)  # Initialiser pour éviter les erreurs
        
        # Afficher un message de début de tour pour le premier joueur
        game._display.display_new_turn("Ayari")
        
        # Afficher l'état initial du jeu et la liste des propriétés une seule fois
        game.display_properties()
        
        # Ajouter des recherches personnalisées
        game.setup_custom_memory_searches()
        
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
                game.display_game_state()
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
    
    
    
    
