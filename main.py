import json
import random
import time
from src.core.game_loader import GameLoader
from src.core.message_finder import MessageFinder
from src.game.monopoly import MonopolyGame
from colorama import init, Fore, Back, Style

from src.game.listeners import MonopolyListeners
from src.game.contexte import Contexte

def on_player_money_changed(player, new_value, old_value):
    diff = new_value - old_value
    emoji = "💰" if diff > 0 else "💸"
    diff_text = f"+{diff}€" if diff > 0 else f"{diff}€"
    color = Fore.GREEN if diff > 0 else Fore.RED
    print(f"{Fore.CYAN}{player.name} {emoji} {color}{new_value}€ ({diff_text}){Style.RESET_ALL}")
    
def on_player_name_changed(player, new_value, old_value):
    print(f"{Fore.YELLOW}👤 {old_value} a changé son nom en {Fore.CYAN}{new_value}{Style.RESET_ALL}")
    
def on_player_dice_changed(player, new_value, old_value, ignore):
    dice_str = f"{new_value[0]}+{new_value[1]}={sum(new_value)}"
    if ignore:
        print(f"{Fore.BLUE}🎲 {player.name} a ignoré les dés: {dice_str}{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}🎲 {player.name} a lancé les dés: {Fore.WHITE}{Back.BLUE}{dice_str}{Style.RESET_ALL}")
        
def on_player_added(player):
    print(f"{Fore.GREEN}✨ {player.name} a rejoint la partie!{Style.RESET_ALL}")
    
def on_player_removed(player):
    print(f"{Fore.RED}👋 {player.name} a quitté la partie!{Style.RESET_ALL}")
    
def on_message_added(id, message, address, group):
    group_text = f" ({group})" if group is not None else ""
    print(f"{Fore.MAGENTA}📢 {id}: {Fore.WHITE}{message}{Fore.CYAN}{group_text}{Style.RESET_ALL}")

def on_message_removed(id, *args):
    print(f"{Fore.MAGENTA}🗑️ Message '{id}' a été supprimé{Style.RESET_ALL}")
    
def on_event(event, *args):
    if event in ["loop_tick", "player_handling", "message_handling", "player_position_changed", "auction_handling"]:
        return
    print(f"{Fore.CYAN}ℹ️ {event}{Style.RESET_ALL}")
    
def on_player_goto_changed(player, new_value, old_value):
    print(f"{Fore.YELLOW}🚶 {player.name} va à la case {Fore.WHITE}{Back.BLUE}{new_value}{Style.RESET_ALL}")

def main():
    """Fonction principale"""
    
    init()
    
    print(f"{Fore.GREEN}🎮 Initialisation du jeu Monopoly...{Style.RESET_ALL}")
    
    try:
        # Charger les données pour le jeu
        data = GameLoader("game_files/starting_state.jsonc", "game_files/starting_state.sav")
        
        # Créer une instance du jeu
        game = MonopolyGame(data)

        def on_auction_bid(bid):
            p = game.players[bid['player']]
            print(f'{Fore.YELLOW}🔨 Nouvelle enchère: {Fore.CYAN}{p.name}{Fore.YELLOW} pour {Fore.GREEN}{bid["bid"]}€{Style.RESET_ALL}')

        
        events = MonopolyListeners(game)
        events.tps = 30
        events.interval_player = .1
        
        # Initialiser le contexte
        contexte = Contexte(game, events)
        print(f"{Fore.GREEN}📊 Contexte initialisé et prêt à enregistrer les événements{Style.RESET_ALL}")
        
        events.on("player_added", on_player_added)
        events.on("player_removed", on_player_removed)
        events.on("player_money_changed", on_player_money_changed)
        events.on("player_name_changed", on_player_name_changed)
        events.on("player_dice_changed", on_player_dice_changed)
        events.on("player_goto_changed", on_player_goto_changed)
        events.on("message_added", on_message_added)    
        events.on("message_removed", on_message_removed)
        events.on("auction_bid", on_auction_bid)
        
        events.on("*", on_event)
        
        # Configuration des joueurs
        game.players[0].name = random.choice(["Alice", "Bob", "Charlie", "David", "Eve"])
        game.players[1].name = random.choice(["Jeff", "Karen", "Linda", "Mike", "Nancy"])
        # game.players[0].money = random.randint(100, 1000)
        # game.players[1].money = random.randint(100, 1000)
        
        print(json.dumps(game.properties, indent=2, default=str))

        print(game.players[0].properties)
        print(game.players[1].properties)
        
        
        events.start()
        
        print(f"{Fore.GREEN}✅ Initialisation terminée!{Style.RESET_ALL}")

        # Await exit command
        while True:
            time.sleep(1)
    except Exception as e:
        print(f"{Fore.RED}❌ Une erreur s'est produite: {e}{Style.RESET_ALL}")
        print(e)
        events.stop()

if __name__ == "__main__":
    main()