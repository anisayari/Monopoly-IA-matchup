import json
import os
import time
from typing import Dict, List, Any
from .monopoly import MonopolyGame
from .listeners import MonopolyListeners
from src.utils import property_manager
from src.utils.property_helpers import get_property_house_count

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
        self.game_settings = self._load_game_settings()  # Charger les paramètres du jeu
        
        # Créer le dossier d'historique s'il n'existe pas
        if not os.path.exists(self.context_history_dir):
            os.makedirs(self.context_history_dir)
        
        # Initialiser le contexte
        self.context = {
            "global": {
                "properties": [],
                "current_turn": 0,
                "player_count": 0,
                "player_names": [],
                "current_player": None
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
    
    def _get_property_details(self, position, color_group):
        """Retourne les détails standard d'une propriété selon sa position et son groupe"""
        # Prix et loyers standards du Monopoly UK
        property_data = {
            "brown": {"price": 60, "house": 50, "rents": [2, 10, 30, 90, 160, 250]},
            "light_blue": {"price": 100, "house": 50, "rents": [6, 30, 90, 270, 400, 550]},
            "pink": {"price": 140, "house": 100, "rents": [10, 50, 150, 450, 625, 750]},
            "orange": {"price": 180, "house": 100, "rents": [14, 70, 200, 550, 750, 950]},
            "red": {"price": 220, "house": 150, "rents": [18, 90, 250, 700, 875, 1050]},
            "yellow": {"price": 260, "house": 150, "rents": [22, 110, 330, 800, 975, 1150]},
            "green": {"price": 300, "house": 200, "rents": [26, 130, 390, 900, 1100, 1275]},
            "dark_blue": {"price": 350, "house": 200, "rents": [35, 175, 500, 1100, 1300, 1500]},
            "station": {"price": 200, "house": 0, "rents": [25, 50, 100, 200, 0, 0]},
            "utility": {"price": 150, "house": 0, "rents": [4, 10, 0, 0, 0, 0]}
        }
        
        # Cas spéciaux pour certaines propriétés
        if position == 37:  # Park Lane
            return 350, 200, [35, 175, 500, 1100, 1300, 1500]
        elif position == 39:  # Mayfair
            return 400, 200, [50, 200, 600, 1400, 1700, 2000]
        
        # Utiliser les données par défaut selon le groupe de couleur
        data = property_data.get(color_group, {"price": 200, "house": 100, "rents": [10, 50, 150, 450, 625, 750]})
        return data["price"], data["house"], data["rents"]
    
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
        self.listeners.on("player_properties_changed", self._on_player_properties_changed)
        
        # Événements des enchères
        self.listeners.on("auction_started", self._on_auction_started)
        self.listeners.on("auction_ended", self._on_auction_ended)
        self.listeners.on("auction_bid", self._on_auction_bid)
        
        # Événements des messages
        self.listeners.on("message_added", self._on_message_added)
    
    def _load_game_settings(self):
        """Charge les paramètres du jeu depuis le fichier de configuration"""
        try:
            settings_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', 'game_settings.json')
            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Erreur chargement game_settings.json: {e}")
        
        # Paramètres par défaut
        return {
            "players": {
                "player1": {"name": "GPT1", "model": "gpt-4.1-mini", "enabled": True},
                "player2": {"name": "GPT2", "model": "gpt-4.1-mini", "enabled": True}
            },
            "game": {"default_model": "gpt-4.1-mini"}
        }
    
    def _update_context(self):
        """Met à jour le contexte avec l'état actuel du jeu"""
        # Debug: afficher le nombre de joueurs (désactivé pour éviter le spam)
        # print(f"[DEBUG] Nombre de joueurs détectés: {len(self.game.players)}")
        
        # Mise à jour des informations globales
        player_names = []
        
        # Utiliser les noms configurés si disponibles
        for i, player in enumerate(self.game.players):
            try:
                # Utiliser le nom configuré pour ce joueur
                player_key = f"player{i+1}"
                if player_key in self.game_settings.get("players", {}):
                    configured_name = self.game_settings["players"][player_key].get("name", player.name)
                    player_names.append(configured_name)
                else:
                    player_names.append(player.name)
            except:
                pass
        
        self.context["global"]["player_count"] = len(self.game.players)
        self.context["global"]["player_names"] = player_names
        self.context["global"]["current_turn"] = self.current_turn
        self.context["global"]["current_player"] = f"player{self.current_player_index + 1}"
        
        # Mise à jour des propriétés
        properties = []
        property_owners = {}  # Pour stocker quel joueur possède quelle propriété
        
        # Récupérer les propriétés de chaque joueur
        for i, player in enumerate(self.game.players):
            try:
                for prop in player.properties:
                    try:
                        prop_position = prop.position
                        property_owners[prop_position] = player.id
                    except:
                        pass
            except:
                pass
        
        # Créer la liste de toutes les propriétés du plateau
        for space in self.monopoly_board:
            if space["type"] == "property":
                prop_id = space["id"]
                owner = property_owners.get(prop_id, None)
                
                # Obtenir les informations de prix standard
                price, house_price, rents = self._get_property_details(prop_id, space["color"])
                
                # Récupérer les coordonnées depuis property_manager
                coords = None
                prop_details = property_manager.get_property_by_position(prop_id)
                if prop_details and 'coordinates' in prop_details:
                    coords = {
                        'x_relative': prop_details['coordinates']['x_relative'],
                        'y_relative': prop_details['coordinates']['y_relative'],
                        'x_pixel': prop_details['coordinates']['x_pixel'],
                        'y_pixel': prop_details['coordinates']['y_pixel']
                    }
                
                # Récupérer le nombre de maisons/hôtels sur cette propriété
                house_count = 0
                try:
                    house_count = get_property_house_count(space["name"]) or 0
                except Exception as e:
                    # En cas d'erreur, laisser à 0
                    pass
                
                # Calculer le loyer actuel en fonction du nombre de maisons
                current_rent = 0
                if owner and house_count >= 0 and house_count < len(rents):
                    current_rent = rents[house_count]
                
                properties.append({
                    "id": prop_id,
                    "name": space["name"],
                    "group": space["color"],
                    "price": price,
                    "rent": rents,
                    "current_rent": current_rent,  # Loyer actuel basé sur les constructions
                    "house_price": house_price,
                    "owner": owner,
                    "houses": house_count,  # Nombre de maisons/hôtel (5 = hôtel)
                    "has_hotel": house_count == 5,  # True si la propriété a un hôtel
                    "coordinates": coords  # Ajout des coordonnées
                })
        
        self.context["global"]["properties"] = properties
        
        # Ajouter un résumé des constructions
        total_houses = sum(1 for p in properties if 0 < p["houses"] < 5) 
        total_hotels = sum(1 for p in properties if p["houses"] == 5)
        properties_with_buildings = [p for p in properties if p["houses"] > 0]
        
        self.context["global"]["buildings_summary"] = {
            "total_houses": sum(p["houses"] for p in properties if p["houses"] < 5),
            "total_hotels": total_hotels,
            "properties_with_houses": [{
                "name": p["name"],
                "houses": p["houses"],
                "owner": p["owner"],
                "group": p["group"]
            } for p in properties_with_buildings if p["houses"] < 5],
            "properties_with_hotels": [{
                "name": p["name"],
                "owner": p["owner"],
                "group": p["group"]
            } for p in properties_with_buildings if p["houses"] == 5]
        }
        
        # Mise à jour des joueurs
        players = {}
        
        for i, player in enumerate(self.game.players):
            try:
                player_id = player.id
                
                # Utiliser le nom configuré pour ce joueur
                player_key = f"player{i+1}"
                if player_key in self.game_settings.get("players", {}):
                    player_name = self.game_settings["players"][player_key].get("name", player.name)
                else:
                    player_name = player.name
                
                # Vérifier si le nom est corrompu (caractères non-ASCII)
                if player_name and any(ord(c) > 127 for c in player_name):
                    # Logger seulement la première fois
                    if not hasattr(self, '_corruption_logged'):
                        self._corruption_logged = True
                        print(f"⚠️  Nom corrompu détecté pour {player_key}. Utilisation du nom de configuration.")
                    # Utiliser le nom de la configuration
                    config_name = self.game_settings.get('players', {}).get(player_key, {}).get('name', f'GPT{i+1}')
                    player_name = config_name
                    
                    # Essayer d'écrire le nom correct en mémoire
                    try:
                        player.name = config_name
                    except Exception as e:
                        pass  # Ignorer silencieusement les erreurs
                
                # Debug: afficher les infos du joueur (désactivé pour éviter le spam)
                # print(f"[DEBUG] Joueur {i+1}: id={player_id}, nom={player_name}, argent={player.money}, position={player.position}")
                
                # Récupérer les propriétés du joueur
                player_properties = []
                try:
                    # Utiliser la méthode owned_properties qui filtre les propriétés valides
                    for prop in player.owned_properties:
                        try:
                            prop_position = prop.position
                            if 0 <= prop_position < len(self.monopoly_board):
                                prop_info = self.monopoly_board[prop_position]
                                if prop_info["type"] == "property":
                                    player_properties.append({
                                        "id": prop_position,
                                        "name": prop_info["name"],
                                        "group": prop_info.get("color", "unknown")
                                    })
                        except:
                            pass
                except:
                    pass
                
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
                
                # Debug: afficher les propriétés du joueur (version simplifiée)
                if len(player_properties) > 0:
                    print(f"[INFO] {player_name}: {len(player_properties)} propriétés")
                
                # Utiliser player_key comme clé au lieu du nom
                players[player_key] = {
                    "name": player_name,
                    "current_player": (i == self.current_player_index),
                    "is_current": (i == self.current_player_index),  # Ajout pour la compatibilité
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
                player_key = f"player{i+1}"
                if player_key in self.context["players"]:
                    self.context["players"][player_key]["current_player"] = (i == self.current_player_index)
                    self.context["players"][player_key]["is_current"] = (i == self.current_player_index)
            except Exception as e:
                print(f"Erreur lors de la mise à jour du joueur actuel: {e}")
        
        # Mettre à jour le joueur actuel dans global
        self.context["global"]["current_player"] = f"player{self.current_player_index + 1}"
    
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
    
    def _on_player_properties_changed(self, player, new_properties, old_properties):
        """Gère les changements de propriétés d'un joueur"""
        player_name = getattr(player, 'name', 'Unknown')
        
        # Comparer les propriétés pour détecter les nouvelles acquisitions
        old_positions = set(prop.get('position', -1) for prop in old_properties)
        new_positions = set(prop.get('position', -1) for prop in new_properties)
        
        # Propriétés acquises
        acquired = new_positions - old_positions
        for prop_position in acquired:
            if 0 <= prop_position < len(self.monopoly_board):
                prop_info = self.monopoly_board[prop_position]
                if prop_info["type"] == "property":
                    # Trouver le prix de la propriété
                    price = "un prix inconnu"
                    for prop in new_properties:
                        if prop.get('position') == prop_position:
                            price = prop.get('price', price)
                            break
                    
                    self._add_event(player_name, "buy_property", f"{prop_info['name']} pour {price}€")
        
        # Propriétés perdues (hypothéquées, vendues, etc.)
        lost = old_positions - new_positions
        for prop_position in lost:
            if 0 <= prop_position < len(self.monopoly_board):
                prop_info = self.monopoly_board[prop_position]
                if prop_info["type"] == "property":
                    self._add_event(player_name, "lose_property", prop_info['name'])
        
        # Mettre à jour le contexte
        self._update_context()
        self._save_context()
        self._save_history("player_properties_changed")
    
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