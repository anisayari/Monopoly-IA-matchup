import json
import random
import time
from src.core.game_loader import GameLoader
from src.core.message_finder import MessageFinder
from src.game.game import MonopolyGame
from colorama import init, Fore, Style

from src.game.listeners import MonopolyListeners

def on_player_money_changed(player, new_value, old_value):
    print(f"{Fore.YELLOW}{player.name} a maintenant {new_value}€ ({str(new_value - old_value)}€){Style.RESET_ALL}")
    
def on_player_name_changed(player, new_value, old_value):
    print(f"{Fore.YELLOW}{old_value} a changé son nom en {new_value}{Style.RESET_ALL}")
    
def on_player_dice_changed(player, new_value, old_value, ignore):
    if ignore:
        print(f"{Fore.GREEN}{player.name} a ignoré les dés: {new_value}{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}{player.name} a lancé les dés: {new_value}{Style.RESET_ALL}")
        
def on_player_added(player):
    print(f"{Fore.YELLOW}{player.name} a rejoint la partie!{Style.RESET_ALL}")
    
def on_player_removed(player):
    print(f"{Fore.YELLOW}{player.name} a quitté la partie!{Style.RESET_ALL}")
    
def on_message_added(id, message, address):
    print(f"{Fore.MAGENTA}{id}: {message}{Style.RESET_ALL}")

def on_message_removed(id, *args):
    print(f"{Fore.MAGENTA}{id} a été supprimé{Style.RESET_ALL}")
    
def on_event(event, *args):
    if event in ["loop_tick", "player_handling", "message_handling", "player_position_changed"]:
        return
    print(f"{Fore.CYAN}> {event}{Style.RESET_ALL}")
    
def on_player_goto_changed(player, new_value, old_value):
    print(f"{Fore.YELLOW}{player.name} va à la case {new_value}{Style.RESET_ALL}")
        
def main():
    """Fonction principale"""
    
    init()
    
    print(f"{Fore.GREEN}Initialisation du jeu Monopoly...{Style.RESET_ALL}")
    
    try:
        # Charger les données pour le jeu
        data = GameLoader("game_files/starting_state.jsonc", "game_files/starting_state.sav")
        
        # Créer une instance du jeu
        game = MonopolyGame(data)
        
        events = MonopolyListeners(game)
        events.tps = 30
        events.interval_player = .1
        
        events.on("player_added", on_player_added)
        events.on("player_removed", on_player_removed)
        events.on("player_money_changed", on_player_money_changed)
        events.on("player_name_changed", on_player_name_changed)
        events.on("player_dice_changed", on_player_dice_changed)
        events.on("player_goto_changed", on_player_goto_changed)
        events.on("message_added", on_message_added)    
        events.on("message_removed", on_message_removed)
        
        events.on("*", on_event)
        
        # Configuration des joueurs
        game.players[0].name = random.choice(["Alice", "Bob", "Charlie", "David", "Eve"])
        game.players[1].name = random.choice(["Jeff", "Karen", "Linda", "Mike", "Nancy"])
        # game.players[0].money = random.randint(100, 1000)
        # game.players[1].money = random.randint(100, 1000)
        
        print(game.get_property_by_player_id(game.players[0].id))
        print(game.get_property_by_player_id(game.players[1].id))
        
        print(game.players[0].dices)
        #print(game.players[1].dices)
        
        print(game.players[0].roll)
        print(game.players[1].roll)

        if game.auction.is_active():
            print(f"{Fore.YELLOW}Une enchère est en cours!{Style.RESET_ALL}")
            print(f"Current winner {game.players[game.auction.current_bidder].name} for {game.auction.current_price}")
            print(f"Next price {game.auction.next_price}")
        
        events.start()
        
        print(f"{Fore.GREEN}Initialisation terminée!{Style.RESET_ALL}")

        # Await exit command
        while True:
            time.sleep(1)
    except Exception as e:
        print(f"{Fore.RED}Une erreur s'est produite: {e}{Style.RESET_ALL}")
        events.stop()

if __name__ == "__main__":
    main()