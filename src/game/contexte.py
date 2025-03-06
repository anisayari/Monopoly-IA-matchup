import json
import os
import time
from typing import Dict, List, Any
from .monopoly import MonopolyGame
from .listeners import MonopolyListeners

class Contexte:
    """Classe gérant le contexte global du jeu Monopoly"""
    
    def __init__(self, game: MonopolyGame, listeners: MonopolyListeners):
        """Initialise le contexte avec le jeu et les listeners"""
        self.game = game
        self.listeners = listeners
        self.context_file = os.path.join("contexte", "game_context.json")
        self.context_history_dir = os.path.join("contexte", "history")
        self.current_turn = 0
        self.current_player_index = 0  # Indice du joueur actuel
        self.events = []
        self.turn_events = []  # Événements du tour actuel
        self.monopoly_board = self._initialize_monopoly_board()  # Initialiser le plateau de Monopoly
        self.duplicate_events = set()  # Pour éviter les événements en double
        
        # Créer le dossier d'historique s'il n'existe pas
        if not os.path.exists(self.context_history_dir):
            os.makedirs(self.context_history_dir)
        
        # Initialiser le contexte
        self.context = {
            "global": {
                "properties": [],
                "current_turn": 0,
                "player_count": 0,
                "player_names": []
            },
            "events": [],
            "players": {},
            "board": {
                "spaces": []
            }
        }
        
        # Enregistrer les événements intéressants
        self._register_events()
        
        # Initialiser le contexte avec l'état actuel
        self._update_context()
        self._save_context()
    
    def _initialize_monopoly_board(self):
        """Initialise le plateau de Monopoly avec les noms réels des cases (version UK)"""
        board = [
            {"id": 0, "name": "GO", "type": "special"},
            {"id": 1, "name": "Old Kent Road", "type": "property", "color": "brown"},
            {"id": 2, "name": "Community Chest", "type": "special"},
            {"id": 3, "name": "Whitechapel Road", "type": "property", "color": "brown"},
            {"id": 4, "name": "Income Tax", "type": "special"},
            {"id": 5, "name": "Kings Cross Station", "type": "property", "color": "station"},
            {"id": 6, "name": "The Angel Islington", "type": "property", "color": "light_blue"},
            {"id": 7, "name": "Chance", "type": "special"},
            {"id": 8, "name": "Euston Road", "type": "property", "color": "light_blue"},
            {"id": 9, "name": "Pentonville Road", "type": "property", "color": "light_blue"},
            {"id": 10, "name": "Jail / Just Visiting", "type": "special"},
            {"id": 11, "name": "Pall Mall", "type": "property", "color": "pink"},
            {"id": 12, "name": "Electric Company", "type": "property", "color": "utility"},
            {"id": 13, "name": "Whitehall", "type": "property", "color": "pink"},
            {"id": 14, "name": "Northumberland Avenue", "type": "property", "color": "pink"},
            {"id": 15, "name": "Marylebone Station", "type": "property", "color": "station"},
            {"id": 16, "name": "Bow Street", "type": "property", "color": "orange"},
            {"id": 17, "name": "Community Chest", "type": "special"},
            {"id": 18, "name": "Marlborough Street", "type": "property", "color": "orange"},
            {"id": 19, "name": "Vine Street", "type": "property", "color": "orange"},
            {"id": 20, "name": "Free Parking", "type": "special"},
            {"id": 21, "name": "Strand", "type": "property", "color": "red"},
            {"id": 22, "name": "Chance", "type": "special"},
            {"id": 23, "name": "Fleet Street", "type": "property", "color": "red"},
            {"id": 24, "name": "Trafalgar Square", "type": "property", "color": "red"},
            {"id": 25, "name": "Fenchurch Street Station", "type": "property", "color": "station"},
            {"id": 26, "name": "Leicester Square", "type": "property", "color": "yellow"},
            {"id": 27, "name": "Coventry Street", "type": "property", "color": "yellow"},
            {"id": 28, "name": "Water Works", "type": "property", "color": "utility"},
            {"id": 29, "name": "Piccadilly", "type": "property", "color": "yellow"},
            {"id": 30, "name": "Go To Jail", "type": "special"},
            {"id": 31, "name": "Regent Street", "type": "property", "color": "green"},
            {"id": 32, "name": "Oxford Street", "type": "property", "color": "green"},
            {"id": 33, "name": "Community Chest", "type": "special"},
            {"id": 34, "name": "Bond Street", "type": "property", "color": "green"},
            {"id": 35, "name": "Liverpool Street Station", "type": "property", "color": "station"},
            {"id": 36, "name": "Chance", "type": "special"},
            {"id": 37, "name": "Park Lane", "type": "property", "color": "dark_blue"},
            {"id": 38, "name": "Super Tax", "type": "special"},
            {"id": 39, "name": "Mayfair", "type": "property", "color": "dark_blue"}
        ]
        return board
    
    def _register_events(self):
        """Enregistre les callbacks pour les événements intéressants"""
        # Événements des joueurs
        self.listeners.on("player_added", self._on_player_added)
        self.listeners.on("player_removed", self._on_player_removed)
        self.listeners.on("player_money_changed", self._on_player_money_changed)
        self.listeners.on("player_name_changed", self._on_player_name_changed)
        self.listeners.on("player_dice_changed", self._on_player_dice_changed)
        self.listeners.on("player_goto_changed", self._on_player_goto_changed)
        self.listeners.on("player_position_changed", self._on_player_position_changed)
        
        # Événements des enchères
        self.listeners.on("auction_started", self._on_auction_started)
        self.listeners.on("auction_ended", self._on_auction_ended)
        self.listeners.on("auction_bid", self._on_auction_bid)
        
        # Événements des messages
        self.listeners.on("message_added", self._on_message_added)
    
    def _update_context(self):
        """Met à jour le contexte avec l'état actuel du jeu"""
        # Mise à jour des informations globales
        player_names = []
        for player in self.game.players:
            try:
                player_names.append(player.name)
            except:
                pass
        
        self.context["global"]["player_count"] = len(self.game.players)
        self.context["global"]["player_names"] = player_names
        self.context["global"]["current_turn"] = self.current_turn
        
        # Mise à jour des propriétés
        properties = []
        try:
            for prop in self.game.properties:
                try:
                    prop_id = prop.get('id', 0)
                    
                    # Obtenir le nom réel de la propriété à partir du plateau
                    prop_name = prop.get('name', 'Unknown')
                    if 0 <= prop_id < len(self.monopoly_board):
                        board_space = self.monopoly_board[prop_id]
                        if board_space["type"] == "property":
                            prop_name = board_space["name"]
                    
                    prop_price = prop.get('price', 0)
                    prop_rents = prop.get('rents', [0, 0, 0, 0, 0, 0])
                    prop_cost = prop.get('cost', 0)
                    
                    # Déterminer le groupe de couleur à partir du plateau
                    color = "unknown"
                    if 0 <= prop_id < len(self.monopoly_board):
                        board_space = self.monopoly_board[prop_id]
                        if "color" in board_space:
                            color = board_space["color"]
                    else:
                        color = self.get_property_color(prop)
                    
                    # Déterminer le propriétaire
                    owner = self.get_property_owner(prop_id)
                    
                    # Déterminer le nombre de maisons (à implémenter selon votre logique de jeu)
                    houses = 0
                    
                    properties.append({
                        "id": prop_id,
                        "name": prop_name,
                        "group": color,
                        "price": prop_price,
                        "rent": prop_rents,
                        "house_price": prop_cost,
                        "owner": owner,
                        "houses": houses
                    })
                except Exception as e:
                    print(f"Erreur lors de la mise à jour d'une propriété: {e}")
        except Exception as e:
            print(f"Erreur lors de l'accès aux propriétés: {e}")
        
        self.context["global"]["properties"] = properties
        
        # Mise à jour des joueurs
        players = {}
        
        for i, player in enumerate(self.game.players):
            try:
                player_id = player.id
                player_name = player.name
                
                # Récupérer les propriétés du joueur
                player_properties = []
                for prop in properties:
                    if prop["owner"] == player_id:
                        player_properties.append(prop["id"])
                
                # Déterminer l'espace actuel
                position = getattr(player, 'position', 0)
                current_space = "Unknown"
                
                # Utiliser le nom réel de la case à partir du plateau
                if 0 <= position < len(self.monopoly_board):
                    current_space = self.monopoly_board[position]["name"]
                else:
                    for space in self.context["board"]["spaces"]:
                        if space["id"] == position:
                            current_space = space["name"]
                            break
                
                # Déterminer si le joueur est en prison
                in_jail = position == 10 and getattr(player, 'jail_turns', 0) > 0
                
                players[player_name] = {
                    "current_player": (i == self.current_player_index),
                    "dice_result": getattr(player, 'dices', None),
                    "money": getattr(player, 'money', 0),
                    "properties": player_properties,
                    "position": position,
                    "current_space": current_space,
                    "jail": in_jail
                }
            except Exception as e:
                print(f"Erreur lors de la mise à jour d'un joueur: {e}")
        
        self.context["players"] = players
        
        # Mise à jour du plateau
        if not self.context["board"]["spaces"]:
            # Utiliser le plateau de Monopoly initialisé
            self.context["board"]["spaces"] = self.monopoly_board
        
        # Limiter le nombre d'événements
        if len(self.context["events"]) > 20:
            self.context["events"] = self.context["events"][-20:]
    
    def _save_context(self):
        """Sauvegarde le contexte dans le fichier JSON"""
        with open(self.context_file, 'w', encoding='utf-8') as f:
            json.dump(self.context, f, ensure_ascii=False, indent=2)
    
    def _save_history(self, event_type: str):
        """Sauvegarde une copie du contexte dans l'historique"""
        timestamp = int(time.time())
        history_file = os.path.join(self.context_history_dir, f"{timestamp}_{event_type}.json")
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(self.context, f, ensure_ascii=False, indent=2)
    
    def _add_event(self, player_name, action, detail=None):
        """Ajoute un événement à la liste des événements avec un message descriptif"""
        # Vérifier si l'événement est pertinent ou s'il doit être ignoré
        if self._should_ignore_event(action, player_name, detail):
            return
            
        # Fusionner avec l'événement précédent si possible
        if self._should_merge_with_previous(action, player_name, detail):
            return
            
        # Créer un message descriptif basé sur l'action et les détails
        message = self._generate_event_message(player_name, action, detail)
        
        event = {
            "turn": self.current_turn,
            "player": player_name,
            "action": action,
            "detail": detail,
            "message": message
        }
        self.context["events"].append(event)
        self.turn_events.append(event)
        
        # Vérifier si c'est la fin du tour
        if self._is_turn_ending_action(action):
            self._end_turn()
    
    def _should_ignore_event(self, action, player_name, detail):
        """Détermine si un événement doit être ignoré"""
        # Créer une clé unique pour cet événement
        event_key = f"{self.current_turn}:{player_name}:{action}:{detail}"
        
        # Si l'événement est déjà dans l'ensemble des événements en double, l'ignorer
        if event_key in self.duplicate_events:
            return True
        
        # Ajouter l'événement à l'ensemble des événements en double
        self.duplicate_events.add(event_key)
        
        # Ignorer les événements de dés ignorés
        if action == "ignore_dice":
            return True
            
        # Ignorer les messages système non pertinents
        if action == "message" and player_name == "System":
            # Liste de messages à ignorer
            ignore_messages = [
                "Roll Again",
                "Next Turn",
                "What would you like to do?",
                "shake the Wii Remote",
                "press \\[BUTTON_A\\]",
                "to roll the dice"
            ]
            
            if detail:
                for msg in ignore_messages:
                    if msg in detail:
                        return True
        
        # Ignorer les événements redondants
        if action == "buy_property" and self.context["events"] and self.context["events"][-1]["action"] == "move_and_buy":
            # Si le dernier événement est déjà un move_and_buy, ignorer cet achat
            return True
        
        # Ignorer les déplacements redondants
        if action == "move" and self.context["events"]:
            last_event = self.context["events"][-1]
            if last_event["action"] in ["move", "move_and_buy", "move_and_pay"] and last_event["player"] == player_name:
                # Si le dernier événement est déjà un déplacement du même joueur, ignorer ce déplacement
                return True
        
        return False
    
    def _should_merge_with_previous(self, action, player_name, detail):
        """Détermine si l'événement doit être fusionné avec le précédent"""
        # Si pas d'événements précédents, ne pas fusionner
        if not self.context["events"]:
            return False
            
        last_event = self.context["events"][-1]
        
        # Si le dernier événement est d'un autre joueur, ne pas fusionner
        if last_event["player"] != player_name:
            return False
            
        # Si le dernier événement est d'un autre tour, ne pas fusionner
        if last_event["turn"] != self.current_turn:
            return False
            
        # Fusionner les événements de déplacement et d'achat de propriété
        if action == "buy_property" and last_event["action"] == "move":
            # Mettre à jour le message du dernier événement
            property_name = detail.split(" pour ")[0] if detail and " pour " in detail else detail
            price = detail.split(" pour ")[1] if detail and " pour " in detail else ""
            
            last_event["message"] = f"{player_name} s'est déplacé sur {property_name} et l'a acheté pour {price}."
            last_event["action"] = "move_and_buy"
            last_event["detail"] = f"{last_event['detail']} -> {detail}"
            return True
            
        # Fusionner les événements de déplacement et de paiement de loyer
        if action == "pay_rent" and last_event["action"] == "move":
            # Mettre à jour le message du dernier événement
            rent_amount = detail.split(" to ")[0] if detail and " to " in detail else detail
            owner = detail.split(" to ")[1].split(" pour ")[0] if detail and " to " in detail and " pour " in detail.split(" to ")[1] else "un autre joueur"
            property_name = detail.split(" pour ")[1] if detail and " pour " in detail else last_event["detail"]
            
            last_event["message"] = f"{player_name} s'est déplacé sur {property_name} et a payé {rent_amount} de loyer à {owner}."
            last_event["action"] = "move_and_pay"
            last_event["detail"] = f"{last_event['detail']} -> {detail}"
            return True
            
        return False
    
    def _generate_event_message(self, player_name, action, detail):
        """Génère un message descriptif pour un événement"""
        # Obtenir le nom réel de la case si possible
        def get_real_space_name(space_id_or_name):
            if isinstance(space_id_or_name, int) or (isinstance(space_id_or_name, str) and space_id_or_name.isdigit()):
                space_id = int(space_id_or_name)
                if 0 <= space_id < len(self.monopoly_board):
                    return self.monopoly_board[space_id]["name"]
            elif isinstance(space_id_or_name, str) and space_id_or_name.startswith("Case "):
                try:
                    space_id = int(space_id_or_name.replace("Case ", ""))
                    if 0 <= space_id < len(self.monopoly_board):
                        return self.monopoly_board[space_id]["name"]
                except ValueError:
                    pass
            return space_id_or_name
        
        if action == "join_game":
            return f"{player_name} a rejoint la partie de Monopoly."
        
        elif action == "leave_game":
            return f"{player_name} a quitté la partie de Monopoly."
        
        elif action == "roll_dice":
            dice_parts = detail.split("=") if detail and "=" in detail else [detail, ""]
            dice_sum = dice_parts[1] if len(dice_parts) > 1 else ""
            return f"{player_name} a lancé les dés et avance de {dice_sum} cases."
        
        elif action == "move":
            space_name = get_real_space_name(detail)
            return f"{player_name} arrive sur {space_name}."
        
        elif action == "goto":
            if "prison" in str(detail).lower():
                return f"{player_name} est envoyé directement en prison."
            elif "départ" in str(detail).lower():
                return f"{player_name} retourne à la case Départ et reçoit 200€."
            else:
                space_name = get_real_space_name(detail)
                return f"{player_name} se déplace directement vers {space_name}."
        
        elif action == "receive_money":
            reason = ""
            if detail and "(" in detail and ")" in detail:
                amount = detail.split(" (")[0] if " (" in detail else detail
                reason = detail.split("(")[1].split(")")[0] if "(" in detail and ")" in detail else ""
                if reason:
                    reason = f" pour {reason}"
            else:
                amount = detail
            
            return f"{player_name} reçoit {amount}{reason}."
        
        elif action == "pay_money":
            reason = ""
            if detail and "(" in detail and ")" in detail:
                amount = detail.split(" (")[0] if " (" in detail else detail
                reason = detail.split("(")[1].split(")")[0] if "(" in detail and ")" in detail else ""
                if reason:
                    reason = f" pour {reason}"
            else:
                amount = detail
            
            return f"{player_name} paie {amount}{reason}."
        
        elif action == "change_name":
            return f"{player_name} change son nom en {detail}."
        
        elif action == "buy_property":
            parts = detail.split(" pour ") if detail and " pour " in detail else [detail, "un montant inconnu"]
            property_name = get_real_space_name(parts[0])
            price = parts[1]
            return f"{player_name} achète {property_name} pour {price}."
        
        elif action == "sell_property":
            parts = detail.split(" pour ") if detail and " pour " in detail else [detail, "un montant inconnu"]
            property_name = get_real_space_name(parts[0])
            price = parts[1]
            return f"{player_name} vend {property_name} pour {price}."
        
        elif action == "mortgage_property":
            property_name = get_real_space_name(detail)
            return f"{player_name} hypothèque {property_name}."
        
        elif action == "unmortgage_property":
            property_name = get_real_space_name(detail)
            return f"{player_name} lève l'hypothèque sur {property_name}."
        
        elif action == "build_house":
            property_name = get_real_space_name(detail)
            return f"{player_name} construit une maison sur {property_name}."
        
        elif action == "build_hotel":
            property_name = get_real_space_name(detail)
            return f"{player_name} construit un hôtel sur {property_name}."
        
        elif action == "pay_rent":
            parts = detail.split(" to ") if detail and " to " in detail else [detail, "un autre joueur"]
            rent = parts[0]
            owner_info = parts[1]
            
            owner = owner_info
            property_name = ""
            
            if " pour " in owner_info:
                owner_parts = owner_info.split(" pour ")
                owner = owner_parts[0]
                property_name = get_real_space_name(owner_parts[1])
                property_name = f" pour {property_name}"
            
            return f"{player_name} paie {rent} de loyer à {owner}{property_name}."
        
        elif action == "jail_enter":
            return f"{player_name} est envoyé en prison."
        
        elif action == "jail_exit":
            method = f" ({detail})" if detail else ""
            return f"{player_name} sort de prison{method}."
        
        elif action == "auction_started":
            property_name = get_real_space_name(detail)
            return f"Une enchère commence pour {property_name}."
        
        elif action == "auction_ended":
            return f"L'enchère est terminée. {detail}"
        
        elif action == "bid":
            return f"{player_name} enchérit {detail}."
        
        elif action == "property_offer":
            # Extraire le nom de la propriété du message
            property_name = ""
            if "buy" in detail and "for" in detail:
                parts = detail.split("buy ")
                if len(parts) > 1:
                    property_parts = parts[1].split(" for")
                    if property_parts:
                        property_name = property_parts[0].strip()
                        property_name = get_real_space_name(property_name)
            
            if property_name:
                return f"{player_name} a la possibilité d'acheter {property_name}."
            return f"{player_name} a la possibilité d'acheter une propriété."
        
        elif action == "jail_options":
            return f"{player_name} doit choisir comment sortir de prison."
        
        elif action == "chance_card":
            return f"{player_name} tire une carte Chance: {detail}"
        
        elif action == "community_chest":
            return f"{player_name} tire une carte Caisse de Communauté: {detail}"
        
        elif action == "message":
            if "Passed Go" in detail:
                return f"{player_name} passe par la case Départ et reçoit 200€."
            return f"Message: {detail}"
        
        elif action == "move_and_buy":
            parts = detail.split(" -> ")
            if len(parts) == 2:
                space = parts[0]
                buy_detail = parts[1]
                
                buy_parts = buy_detail.split(" pour ")
                property_name = get_real_space_name(buy_parts[0]) if len(buy_parts) > 0 else space
                price = buy_parts[1] if len(buy_parts) > 1 else "un montant inconnu"
                
                return f"{player_name} arrive sur {property_name} et l'achète pour {price}."
            
            return f"{player_name} se déplace et achète une propriété."
        
        elif action == "move_and_pay":
            parts = detail.split(" -> ")
            if len(parts) == 2:
                space = parts[0]
                pay_detail = parts[1]
                
                pay_parts = pay_detail.split(" to ")
                rent = pay_parts[0] if len(pay_parts) > 0 else "un loyer"
                
                owner_info = pay_parts[1] if len(pay_parts) > 1 else "un autre joueur"
                owner = owner_info
                property_name = get_real_space_name(space)
                
                if " pour " in owner_info:
                    owner_parts = owner_info.split(" pour ")
                    owner = owner_parts[0]
                    property_name = get_real_space_name(owner_parts[1])
                
                return f"{player_name} arrive sur {property_name} et paie {rent} de loyer à {owner}."
            
            return f"{player_name} se déplace et paie un loyer."
        
        # Cas par défaut
        return f"{player_name} a effectué l'action '{action}' {detail if detail else ''}."
    
    def _is_turn_ending_action(self, action):
        """Détermine si une action marque la fin d'un tour"""
        # Actions qui marquent généralement la fin d'un tour
        turn_ending_actions = [
            "move_and_buy",   # Déplacement + achat = fin de tour
            "move_and_pay",   # Déplacement + paiement = fin de tour
            "pay_rent",       # Après avoir payé un loyer, le tour passe généralement au joueur suivant
            "buy_property",   # Après avoir acheté une propriété, le tour passe généralement au joueur suivant
            "auction_ended",  # La fin d'une enchère marque généralement la fin d'un tour
            "jail_enter"      # Aller en prison termine le tour
        ]
        
        # Si le message contient "Next Turn", c'est aussi la fin du tour
        if action == "message" and "Next Turn" in str(self.context["events"][-1].get("detail", "")):
            return True
            
        return action in turn_ending_actions
    
    def _end_turn(self):
        """Termine le tour actuel et passe au joueur suivant"""
        # Passer au joueur suivant
        self.current_player_index = (self.current_player_index + 1) % max(1, len(self.game.players))
        
        # Si on revient au premier joueur, incrémenter le numéro de tour
        if self.current_player_index == 0:
            self.current_turn += 1
        
        # Mettre à jour le contexte global
        self.context["global"]["current_turn"] = self.current_turn
        
        # Réinitialiser les événements du tour
        self.turn_events = []
        
        # Mettre à jour le joueur actuel dans le contexte
        self._update_current_player()
    
    def _update_current_player(self):
        """Met à jour le joueur actuel dans le contexte"""
        for i, player in enumerate(self.game.players):
            try:
                player_name = player.name
                if player_name in self.context["players"]:
                    self.context["players"][player_name]["current_player"] = (i == self.current_player_index)
            except Exception as e:
                print(f"Erreur lors de la mise à jour du joueur actuel: {e}")
    
    # Callbacks pour les événements
    def _on_player_added(self, player):
        player_name = getattr(player, 'name', 'Unknown')
        self._add_event(player_name, "join_game")
        self._update_context()
        self._save_context()
        self._save_history("player_added")
    
    def _on_player_removed(self, player):
        player_name = getattr(player, 'name', 'Unknown')
        self._add_event(player_name, "leave_game")
        self._update_context()
        self._save_context()
        self._save_history("player_removed")
    
    def _on_player_money_changed(self, player, new_value, old_value):
        player_name = getattr(player, 'name', 'Unknown')
        diff = new_value - old_value
        
        # Déterminer la raison du changement d'argent (à améliorer selon votre logique de jeu)
        reason = self._determine_money_change_reason(player, diff)
        
        if diff > 0:
            self._add_event(player_name, "receive_money", f"{abs(diff)}€ ({reason})")
        else:
            self._add_event(player_name, "pay_money", f"{abs(diff)}€ ({reason})")
            
        self._update_context()
        self._save_context()
        self._save_history("player_money_changed")
    
    def _determine_money_change_reason(self, player, diff):
        """Détermine la raison probable d'un changement d'argent"""
        # Cette méthode peut être améliorée avec plus de contexte du jeu
        position = getattr(player, 'position', -1)
        
        if position == 0:  # Case départ
            return "passage par la case départ"
        elif position == 10:  # Prison
            return "amende ou caution"
        elif position == 20:  # Parc gratuit
            return "parc gratuit"
        elif position == 30:  # Allez en prison
            return "amende"
        elif diff > 0 and diff == 200:
            return "passage par la case départ"
        elif diff < 0:
            # Vérifier si c'est un loyer
            for other_player in self.game.players:
                if other_player.id != player.id:
                    other_props = self.game.get_property_by_player_id(other_player.id)
                    if other_props and position == other_props.get('id', -1):
                        return f"loyer payé à {other_player.name}"
            
            # Autres raisons possibles
            if abs(diff) in [50, 100, 150]:
                return "taxe ou carte chance/caisse de communauté"
            
        return "transaction"
    
    def _on_player_name_changed(self, player, new_value, old_value):
        self._add_event(old_value, "change_name", new_value)
        self._update_context()
        self._save_context()
        self._save_history("player_name_changed")
    
    def _on_player_dice_changed(self, player, new_value, old_value, ignore):
        player_name = getattr(player, 'name', 'Unknown')
        
        # Ignorer les événements de dés ignorés
        if ignore:
            # On peut quand même enregistrer l'événement pour le débogage, mais il sera filtré
            self._add_event(player_name, "ignore_dice", f"{new_value[0]}+{new_value[1]}={sum(new_value)}" if new_value and len(new_value) >= 2 else str(new_value))
            return
        
        # Calculer la somme des dés
        dice_sum = sum(new_value) if new_value else 0
        detail = f"{new_value[0]}+{new_value[1]}={dice_sum}" if new_value and len(new_value) >= 2 else str(new_value)
        
        # Ajouter l'événement de lancer de dés
        self._add_event(player_name, "roll_dice", detail)
        
        # Si ce n'est pas ignoré, ajouter un événement de déplacement
        if new_value and len(new_value) >= 2:
            # Vérifier si le joueur est en prison
            position = getattr(player, 'position', -1)
            if position == 10:  # Prison
                # Vérifier si c'est un double
                if new_value[0] == new_value[1]:
                    self._add_event(player_name, "jail_exit", "double obtenu")
            
            # Ajouter un événement pour indiquer la nouvelle position après le lancer de dés
            new_position = (position + dice_sum) % 40  # 40 cases sur un plateau standard
            space_name = "Unknown"
            for space in self.context["board"]["spaces"]:
                if space["id"] == new_position:
                    space_name = space["name"]
                    break
            
            # Vérifier si le joueur passe par la case départ
            if position + dice_sum >= 40:
                self._add_event(player_name, "receive_money", "200€ (passage par la case départ)")
            
            self._add_event(player_name, "move", space_name)
            
            # Vérifier si la case est une propriété et si elle est disponible
            for prop in self.context["global"]["properties"]:
                if prop["id"] == new_position and prop["owner"] is None:
                    self._add_event(player_name, "buy_property", f"{space_name} pour {prop['price']}€")
                    break
                elif prop["id"] == new_position and prop["owner"] != player.id:
                    # Trouver le nom du propriétaire
                    owner_name = "un autre joueur"
                    for p in self.game.players:
                        if p.id == prop["owner"]:
                            owner_name = p.name
                            break
                    
                    # Calculer le loyer (simplifié)
                    rent = prop["rent"][0]  # Loyer de base
                    self._add_event(player_name, "pay_rent", f"{rent}€ to {owner_name} pour {space_name}")
                    break
        
        self._update_context()
        self._save_context()
        self._save_history("player_dice_changed")
    
    def _on_player_goto_changed(self, player, new_value, old_value):
        player_name = getattr(player, 'name', 'Unknown')
        space_name = "Unknown"
        
        for space in self.context["board"]["spaces"]:
            if space["id"] == new_value:
                space_name = space["name"]
                break
        
        # Déterminer la raison du déplacement
        reason = ""
        if new_value == 10:
            reason = " (envoyé en prison)"
            self._add_event(player_name, "jail_enter")
        elif new_value == 0:
            reason = " (case départ)"
        
        self._add_event(player_name, "goto", f"{space_name}{reason}")
        
        # Vérifier si la case est une propriété et si elle est disponible
        for prop in self.context["global"]["properties"]:
            if prop["id"] == new_value and prop["owner"] is None:
                self._add_event(player_name, "buy_property", f"{space_name} pour {prop['price']}€")
                break
            elif prop["id"] == new_value and prop["owner"] != player.id:
                # Trouver le nom du propriétaire
                owner_name = "un autre joueur"
                for p in self.game.players:
                    if p.id == prop["owner"]:
                        owner_name = p.name
                        break
                
                # Calculer le loyer (simplifié)
                rent = prop["rent"][0]  # Loyer de base
                self._add_event(player_name, "pay_rent", f"{rent}€ to {owner_name} pour {space_name}")
                break
        
        self._update_context()
        self._save_context()
        self._save_history("player_goto_changed")
    
    def _on_player_position_changed(self, player, new_value, old_value):
        player_name = getattr(player, 'name', 'Unknown')
        space_name = "Unknown"
        
        for space in self.context["board"]["spaces"]:
            if space["id"] == new_value:
                space_name = space["name"]
                break
        
        # Ne pas ajouter d'événement de déplacement si c'est juste après un lancer de dés
        # car cela a déjà été géré dans _on_player_dice_changed
        last_event = self.context["events"][-1] if self.context["events"] else None
        if not last_event or last_event["action"] != "move":
            self._add_event(player_name, "move", space_name)
            
            # Vérifier si la case est une propriété et si elle est disponible
            for prop in self.context["global"]["properties"]:
                if prop["id"] == new_value and prop["owner"] is None:
                    self._add_event(player_name, "buy_property", f"{space_name} pour {prop['price']}€")
                    break
                elif prop["id"] == new_value and prop["owner"] != player.id:
                    # Trouver le nom du propriétaire
                    owner_name = "un autre joueur"
                    for p in self.game.players:
                        if p.id == prop["owner"]:
                            owner_name = p.name
                            break
                    
                    # Calculer le loyer (simplifié)
                    rent = prop["rent"][0]  # Loyer de base
                    self._add_event(player_name, "pay_rent", f"{rent}€ to {owner_name} pour {space_name}")
                    break
        
        self._update_context()
        self._save_context()
        self._save_history("player_position_changed")
    
    def _on_auction_started(self):
        # Déterminer la propriété mise aux enchères (si possible)
        property_name = "une propriété"
        
        self._add_event("System", "auction_started", property_name)
        self._update_context()
        self._save_context()
        self._save_history("auction_started")
    
    def _on_auction_ended(self, last_bid):
        detail = "Aucune offre n'a été faite."
        
        if last_bid is not None:
            player_index = last_bid.get("player", -1)
            bid_amount = last_bid.get("bid", 0)
            
            if player_index >= 0 and player_index < len(self.game.players):
                player = self.game.players[player_index]
                player_name = getattr(player, 'name', "Unknown")
                
                # Déterminer la propriété achetée (si possible)
                property_name = "une propriété"
                
                detail = f"{player_name} a remporté {property_name} pour {bid_amount}€"
                
                # Ajouter un événement d'achat pour le joueur
                self._add_event(player_name, "buy_property", f"{property_name} pour {bid_amount}€ (enchère)")
        
        self._add_event("System", "auction_ended", detail)
        self._update_context()
        self._save_context()
        self._save_history("auction_ended")
    
    def _on_auction_bid(self, bid):
        try:
            player_index = bid.get('player', -1)
            bid_amount = bid.get("bid", 0)
            
            if player_index >= 0 and player_index < len(self.game.players):
                player = self.game.players[player_index]
                player_name = getattr(player, 'name', "Unknown")
                
                # Déterminer la propriété mise aux enchères (si possible)
                property_name = "une propriété"
                
                self._add_event(player_name, "bid", f"{bid_amount}€ pour {property_name}")
            else:
                self._add_event("Unknown", "bid", f"{bid_amount}€")
        except Exception as e:
            print(f"Erreur lors de la gestion d'une enchère: {e}")
            self._add_event("System", "bid_error", str(e))
        
        self._update_context()
        self._save_context()
        self._save_history("auction_bid")
    
    def _on_message_added(self, id, message, address, group):
        # Analyser le message pour déterminer son type
        message_type = self._analyze_message(id, message)
        
        detail = f"{message}"
        if group:
            detail += f" ({group})"
        
        # Si c'est un message spécifique, créer un événement plus descriptif
        if message_type:
            self._add_event("System", message_type, detail)
        else:
            self._add_event("System", "message", detail)
        
        self._update_context()
        self._save_context()
    
    def _analyze_message(self, id, message):
        """Analyse un message pour déterminer son type"""
        message_lower = message.lower()
        
        if "buy" in message_lower and "for" in message_lower:
            return "property_offer"
        elif "pay" in message_lower and "bail" in message_lower:
            return "jail_options"
        elif "roll" in message_lower and "doubles" in message_lower:
            return "jail_options"
        elif "auction" in message_lower:
            return "auction_notification"
        elif "rent" in message_lower:
            return "rent_notification"
        elif "tax" in message_lower:
            return "tax_notification"
        elif "chance" in message_lower:
            return "chance_card"
        elif "community" in message_lower:
            return "community_chest"
        
        return None
    
    def get_property_color(self, prop):
        """Détermine la couleur d'une propriété en fonction de son ID ou d'autres attributs"""
        # Vous pouvez implémenter une logique plus complexe ici
        # Par exemple, en fonction des groupes de propriétés dans le jeu Monopoly
        prop_id = prop.get('id', 0)
        
        # Exemple de logique simple basée sur l'ID
        colors = ["brown", "light_blue", "pink", "orange", "red", "yellow", "green", "blue"]
        color_index = (prop_id % len(colors))
        return colors[color_index]
    
    def get_property_owner(self, prop_id):
        """Détermine le propriétaire d'une propriété en fonction de son ID"""
        # Parcourir tous les joueurs pour voir qui possède cette propriété
        for player in self.game.players:
            try:
                player_props = self.game.get_property_by_player_id(player.id)
                if player_props and player_props.get('id') == prop_id:
                    return player.id
            except Exception:
                pass
        return None 