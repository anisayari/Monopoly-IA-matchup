import json
from src.core.message_finder import MessageFinder
from src.core.listeners import EventListeners
from src.game.monopoly import MonopolyGame

import threading
import time

class MonopolyListeners(EventListeners):
    
    _game: MonopolyGame
    _running: bool
    _thread: threading.Thread
    tps: int = 1

    def __init__(self, game):
        super().__init__()
        self._game = game
        self._running = False
        self._thread = None

    def start(self):
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._run)
            self._thread.daemon = True  # Ensure the thread does not block main thread exit
            self._thread.start()

    def stop(self):
        if self._running:
            self._running = False
            self._thread.join()
            
    # { id, text, address }
    _message_founds = []
    
    def message_handler(self):
        messages = MessageFinder.messages(self._game)
        self.emit("message_handling", messages)
         
        # remove old messages
        for message in self._message_founds:
            index = MonopolyListeners.find_index(
                messages,
                lambda x: x["id"] == message["id"]
            )
            if index == -1:
                self._message_founds.remove(message)
                self.emit("message_removed", message["id"], message["text"], message["address"])
            else:
                index = MonopolyListeners.find_index(
                    messages[index]["data"],
                    lambda x: x["address"] == message["address"] and x["text"] == message["text"]
                )
                if index == -1:
                    self._message_founds.remove(message)
                    self.emit("message_removed", message["id"], message["text"], message["address"])
    
        # add new messages 
        for message in messages:
            for data in message["data"]:
                index = MonopolyListeners.find_index(
                    self._message_founds, 
                    lambda x: x["id"] == message["id"] and x["address"] == data["address"] and x["text"] == data["text"]
                )
                if index == -1:
                    event = {
                        "id": message["id"],
                        "text": data["text"],
                        "address": data["address"],
                        "group": message.get("group", None)
                    }
                    self._message_founds.append(event)
                    self.emit("message_added", event["id"], event["text"], event["address"], event["group"])
                   
    @staticmethod
    def find_index(lst, func): 
        return next((i for i, x in enumerate(lst) if func(x)), -1)
    
    _players = []
    
    def player_money_handler(self):
        for player in self._players:
            game_player = self._game.get_player_by_id(player["id"])
            if game_player is None:
                self.emit("warning", "Player not found in player_money_handler")
                continue
            old,new = player["money"], game_player.money
            if old != new:
                player["money"] = new
                self.emit("player_money_changed", game_player, new, old)
    
    def player_name_handler(self):
        for player in self._players:
            game_player = self._game.get_player_by_id(player["id"])
            if game_player is None:
                self.emit("warning", "Player not found in player_name_handler")
                continue
            old,new = player["name"], game_player.name
            if old != new:
                player["name"] = new
                self.emit("player_name_changed", game_player, new, old)
                
    def player_dice_handler(self):
        for player in self._players:
            game_player = self._game.get_player_by_id(player["id"])
            if game_player is None:
                self.emit("warning", "Player not found in player_dice_handler")
                continue
            
            old,new = player["dices"], game_player.dices
            
            if old != new:
                player["dices"] = new
                if new == [0, 0]:
                    player["ignore_next_dice"] = True
                    continue
                if player["ignore_next_dice"]:
                    player["ignore_next_dice"] = False
                    self.emit("player_dice_changed", game_player, new, old, True)
                    continue
                player["ignore_next_dice"] = True
                self.emit("player_dice_changed", game_player, new, old, False)
                
    def player_goto_handler(self):
        for player in self._players:
            game_player = self._game.get_player_by_id(player["id"])
            if game_player is None:
                self.emit("warning", "Player not found in player_goto_handler")
                continue
            old,new = player["goto"], game_player.goto
            if old != new:
                player["goto"] = new
                self.emit("player_goto_changed", game_player, new, old)
    
    def player_position_handler(self):
        for player in self._players:
            game_player = self._game.get_player_by_id(player["id"])
            if game_player is None:
                self.emit("warning", "Player not found in player_position_handler")
                continue
            old,new = player["position"], game_player.position
            if old != new:
                player["position"] = new
                self.emit("player_position_changed", game_player, new, old)
                
    def player_handler(self):
        self.emit("player_handling", self._players)
        
        # remove old players
        for player in self._players:
            game_player = self._game.get_player_by_id(player["id"])
            if game_player is None:
                # Créer un objet temporaire avec les informations du joueur pour l'événement
                removed_player = type('Player', (), {'id': player["id"], 'name': player["name"]})
                self._players.remove(player)
                self.emit("player_removed", removed_player)
                
        # add new players
        for player in self._game.players:
            index = MonopolyListeners.find_index(self._players, lambda x: x["id"] == player.id)
            if index == -1:
                self._players.append({
                    "id": player.id,
                    "name": player.name,
                    "money": player.money,
                    "dices": player.dices,
                    "ignore_next_dice": False,
                    "goto": player.goto,
                    "position": player.position
                })
                self.emit("player_added", player)
                
        self.player_name_handler()
        self.player_money_handler()
        self.player_dice_handler()
        self.player_goto_handler()
        self.player_position_handler()

    _auction = {
        'active': False,
        'current': {
            'player': None,
            'bid': 0,
            'next_bid': 0
        }
    }

    def auction_active_handler(self):
        if self._game.auction.is_active() and not self._auction['active']:
            self._auction['active'] = True
            self.emit("auction_started")
        elif not self._game.auction.is_active() and self._auction['active']:
            self._auction['active'] = False
            self.emit("auction_ended", self._auction['current'])

    def auction_bid_handler(self):
        if not self._game.auction.is_active():
            return
        
        bid = {
            'player': self._game.auction.current_bidder, 
            'bid': self._game.auction.current_price, 
            'next_bid': self._game.auction.next_price
        }
        if bid != self._auction['current'] and bid['player'] < 4:
            self._auction['current'] = bid
            self.emit("auction_bid", bid)

    def auction_handler(self):
        self.emit("auction_handling", self._game.auction)
        
        self.auction_active_handler()
        self.auction_bid_handler()
        
    _last_time_message = 0
    _last_time_player = 0
    _last_time_auction = 0
    
    interval_message = 1 # 1 second
    interval_player = 1 # 1 second
    interval_auction = 0.1 # 0.1 second

    def _run(self):
        while self._running:
            self.emit("loop_tick")
            
            if time.time() - self._last_time_player >= self.interval_player:
                self._last_time_player = time.time()
                self.player_handler()
                
            if time.time() - self._last_time_message >= self.interval_message:
                self._last_time_message = time.time()
                self.message_handler()

            if time.time() - self._last_time_auction >= self.interval_auction:
                self._last_time_auction = time.time()
                self.auction_handler()
            
            time.sleep(1 / self.tps)



