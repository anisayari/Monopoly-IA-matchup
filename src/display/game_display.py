from datetime import datetime
from typing import Dict, Any, Tuple
from colorama import init, Fore, Back, Style
import time
import re

class GameDisplay:
    """Classe gérant l'affichage des modifications du jeu"""
    
    # Émojis pour les différents types d'événements
    EMOJIS = {
        'money': '💰',
        'position': '🎯',
        'dice': '🎲',
        'dialog': '💭',
        'auction': '🏷️',
        'info': 'ℹ️',
        'property': '🏠',
        'time': '🕒',
        'turn': '👉',
        'buy': '💵',
        'new_turn': '🎲',
        'end_turn': '🎮',
        'opportunity': '💰'
    }
    
    def __init__(self):
        init()  # Initialise colorama
        self._previous_states = {
            'blue_player': {},
            'red_player': {},
            'dialog': {},
            'auction': {},
            'buy_property': ''
        }
        # Suivi des lancers de dés
        self._dice_rolls = {
            'blue': {'last_roll': None, 'last_time': 0, 'was_reset': False},
            'red': {'last_roll': None, 'last_time': 0, 'was_reset': False}
        }
        self._last_buy_property_message = ''

    def _format_time(self) -> str:
        """Retourne l'heure actuelle formatée"""
        return datetime.now().strftime("%H:%M:%S")

    def _print_change(self, category: str, message: str, player_color: str = None, is_secondary: bool = False):
        """Affiche un changement avec l'émoji approprié et la couleur du joueur si applicable"""
        time = self._format_time()
        emoji = self.EMOJIS.get(category, '')
        
        # Définition de la couleur en fonction du joueur
        color = Fore.WHITE
        if player_color == 'blue':
            color = Fore.BLUE
        elif player_color == 'red':
            color = Fore.RED
            
        # Format secondaire pour les informations moins importantes
        if is_secondary:
            message = f"{Fore.WHITE}({Style.DIM}{message}{Style.RESET_ALL}{Fore.WHITE})"
            
        # Format: [🕒 12:34:56] 💰 Message
        print(f"{Fore.WHITE}[{self.EMOJIS['time']} {time}] {emoji} {color}{message}{Style.RESET_ALL}")

    def update_player(self, color: str, current_state: Dict[str, Any]):
        """Met à jour et affiche les changements d'état d'un joueur"""
        previous = self._previous_states[f'{color}_player']
        current_time = time.time()
        
        # Gestion des dés
        if 'dices' in current_state and current_state['dices'] != previous.get('dices'):
            dice1, dice2 = current_state['dices']
            dice_sum = dice1 + dice2
            
            # Détecter une réinitialisation
            if dice_sum == 0:
                self._dice_rolls[color]['was_reset'] = True
                self._dice_rolls[color]['last_roll'] = None
            # Traitement des lancers non-nuls
            elif dice_sum > 0:
                current_roll = (dice1, dice2)
                
                # Si c'est le premier lancer après une réinitialisation (factice)
                if self._dice_rolls[color]['was_reset']:
                    self._dice_rolls[color]['was_reset'] = False
                    self._dice_rolls[color]['last_roll'] = current_roll
                    # Afficher un message pour le lancer factice
                    self._print_change('dice',
                        f"Les dés sont lancés !",
                        color)
                # Sinon, c'est le vrai lancer
                elif (current_time - self._dice_rolls[color]['last_time'] > 2 and 
                      current_roll != self._dice_rolls[color]['last_roll']):
                    self._dice_rolls[color]['last_roll'] = current_roll
                    self._dice_rolls[color]['last_time'] = current_time
                    # Afficher un message plus détaillé pour le vrai lancer
                    self._print_change('dice',
                        f"{current_state['label']} a fait un lancé de {dice1} et {dice2} soit {dice_sum}",
                        color)

        # Gestion de la position et du goto
        if ('goto' in current_state and current_state['goto'] != previous.get('goto')) or \
           ('position' in current_state and current_state['position'] != previous.get('position')):
            
            # Afficher le goto comme déplacement principal
            if 'goto' in current_state and current_state['goto'] != previous.get('goto'):
                self._print_change('position',
                    f"{current_state['label']} se déplace vers la case {current_state['goto']}",
                    color)
            
            # Afficher la position comme info secondaire
            if 'position' in current_state and current_state['position'] != previous.get('position'):
                self._print_change('position',
                    f"{current_state['label']} - Position actuelle: {current_state['position']}",
                    color, True)

        # Gestion de l'argent - Simplifiée pour afficher directement les changements
        if 'money' in current_state and current_state['money'] != previous.get('money', 0):
            current_money = current_state['money']
            previous_money = previous.get('money', current_money)
            change = current_money - previous_money
            
            if change != 0:
                sign = '+' if change > 0 else ''
                self._print_change('money', 
                    f"{current_state['label']}: {sign}{change}$ (Total: ${current_money})",
                    color)

        # Mise à jour de l'état précédent
        self._previous_states[f'{color}_player'].update(current_state)

    def update_dialog(self, title: str, message: str):
        """Met à jour et affiche les changements de dialogue"""
        previous = self._previous_states['dialog']
        current = {'title': title, 'message': message}
        
        # Ne rien faire si le message est identique au précédent
        if current == previous:
            return
            
        # Vérifier si c'est un message de tour de jeu
        if "shake the Wii Remote" in message and "to roll the dice" in message:
            # Extraire le nom du joueur
            player_name = title
            # Déterminer la couleur du joueur
            player_color = 'blue' if title.lower() == 'ayari' else 'red'
            
            # Afficher un message de tour de jeu (une seule fois)
            self._print_change('turn', f"C'est au tour de {player_name} !", player_color)
        # Sinon, afficher le dialogue normal
        else:
            self._print_change('dialog', f"{title} - {message}")
            
        # Mettre à jour l'état précédent
        self._previous_states['dialog'] = current

    def update_auction(self, message: str, purchaser: str, name: str):
        """Met à jour et affiche les changements d'enchères"""
        previous = self._previous_states['auction']
        current = {'message': message, 'purchaser': purchaser, 'name': name}
        
        # Ne rien faire si le message est identique au précédent
        if current == previous:
            return
            
        # Afficher le message d'enchère uniquement s'il y a un contenu
        if message or purchaser or name:
            self._print_change('auction', f"Enchère: {message} (Acheteur: {purchaser}, Nom: {name})")
            
        # Mettre à jour l'état précédent
        self._previous_states['auction'] = current

    def update_buy_property(self, message: str):
        """Met à jour l'affichage avec un message d'achat de propriété"""
        # Vérifier si c'est le même message que le précédent
        if message == self._last_buy_property_message:
            return
        
        # Stocker le message pour éviter les répétitions
        self._last_buy_property_message = message
        
        # Nettoyer le message pour enlever les caractères non imprimables
        cleaned_message = re.sub(r'[^\x20-\x7E]', '', message)
        
        # Vérifier si le message contient des mots-clés liés à l'achat
        buy_keywords = ['buy', 'purchase', 'acheter', 'acquérir']
        if not any(keyword in cleaned_message.lower() for keyword in buy_keywords):
            return
        
        # Initialiser les variables
        property_name = None
        property_price = None
        player_name = "Joueur"  # Valeur par défaut
        
        # Extraire le nom de la propriété et le prix avec regex
        # Essayer différents patterns pour capturer les formats possibles
        patterns = [
            # "Would you like to buy X for Y"
            r"like to buy\s+([A-Za-z\s]+(?:Station|Avenue|Road|Street|Lane|Place|Gardens|Square|Park|Boardwalk|Walk))\s+for\s+\$?(\d+|\~\d+)",
            # "Do you want to buy X for Y"
            r"want to buy\s+([A-Za-z\s]+(?:Station|Avenue|Road|Street|Lane|Place|Gardens|Square|Park|Boardwalk|Walk))\s+for\s+\$?(\d+|\~\d+)",
            # "buy X for ~Y?"
            r"buy\s+([A-Za-z\s]+(?:Station|Avenue|Road|Street|Lane|Place|Gardens|Square|Park|Boardwalk|Walk))\s+for\s+\$?(\d+|\~\d+)\??",
            # Generic pattern for any property name followed by a price
            r"buy\s+([A-Za-z\s]+)\s+for\s+\$?(\d+|\~\d+)\??"
        ]
        
        for pattern in patterns:
            property_match = re.search(pattern, cleaned_message, re.IGNORECASE)
            if property_match:
                property_name = property_match.group(1).strip()
                property_price = property_match.group(2).strip()
                break
        
        # Rechercher le nom du joueur (plus difficile, dépend du format du message)
        player_match = re.search(r"(Player\s+\d+|[A-Za-z]+)'s turn", cleaned_message, re.IGNORECASE)
        if player_match:
            player_name = player_match.group(1).strip()
        
        # Si nous avons extrait les informations de propriété, utiliser la méthode spécialisée
        if property_name and property_price:
            self.display_property_purchase_opportunity(player_name, property_name, property_price)
        else:
            # Sinon, construire un message générique à afficher
            display_message = cleaned_message
            # Afficher le message générique
            self._print_change('buy', f"ACHAT DE PROPRIÉTÉ: {display_message}")

    def print_info(self, message: str):
        """Affiche une information générale"""
        self._print_change('info', message)
        
    def print_property(self, message: str):
        """Affiche une information sur une propriété"""
        self._print_change('property', message)

    def print_error(self, message: str):
        """Affiche un message d'erreur"""
        print(f"{Fore.RED}Erreur: {message}{Style.RESET_ALL}")

    def display_new_turn(self, player_name: str):
        """Affiche un message de début de tour"""
        # Déterminer la couleur du joueur
        player_color = 'blue' if player_name.lower() == 'ayari' else 'red'
        color_code = Fore.BLUE if player_color == 'blue' else Fore.RED
        
        # Créer une bordure pour rendre le message plus visible
        border = f"{color_code}{'=' * 60}{Style.RESET_ALL}"
        
        # Afficher le message de début de tour dans la couleur du joueur
        print(f"\n{border}")
        print(f"{color_code}{self.EMOJIS['new_turn']} DÉBUT DU TOUR DE {player_name.upper()} {self.EMOJIS['new_turn']}{Style.RESET_ALL}")
        print(f"{border}")

    def display_end_turn(self, player_name: str):
        """Affiche un message de fin de tour"""
        # Déterminer la couleur du joueur
        player_color = 'blue' if player_name.lower() == 'ayari' else 'red'
        color_code = Fore.BLUE if player_color == 'blue' else Fore.RED
        
        # Créer une bordure pour rendre le message plus visible
        border = f"{color_code}{'=' * 60}{Style.RESET_ALL}"
        
        # Afficher le message de fin de tour dans la couleur du joueur
        print(f"\n{border}")
        print(f"{color_code}{self.EMOJIS['end_turn']} FIN DU TOUR DE {player_name.upper()} {self.EMOJIS['end_turn']}{Style.RESET_ALL}")
        print(f"{color_code}Options disponibles: Lancer les dés, Gérer les propriétés, etc.{Style.RESET_ALL}")
        print(f"{border}")

    def display_property_purchase_opportunity(self, player_name: str, property_name: str, property_price: str):
        """Affiche une opportunité d'achat de propriété"""
        # Créer un message formaté
        message = f"{player_name} peut acheter la propriété {property_name} au prix de ${property_price}"
        
        # Déterminer la couleur du joueur
        player_color = 'blue' if player_name.lower() == 'ayari' else 'red'
        color_code = Fore.BLUE if player_color == 'blue' else Fore.RED
        
        # Créer une bordure pour rendre le message plus visible
        border = f"{Fore.YELLOW}{'=' * 60}{Style.RESET_ALL}"
        
        # Afficher un titre pour l'opportunité d'achat
        print(f"\n{border}")
        print(f"{Fore.YELLOW}💰 OPPORTUNITÉ D'ACHAT 💰{Style.RESET_ALL}")
        print(f"{color_code}{player_name.upper()} peut acheter la propriété {property_name} au prix de ${property_price}{Style.RESET_ALL}")
        print(f"{border}")
        
        # Utiliser le format standard d'affichage avec l'emoji d'opportunité d'achat
        # Vérifier si l'emoji 'opportunity' existe, sinon utiliser 'buy'
        emoji_key = 'opportunity' if 'opportunity' in self.EMOJIS else 'buy'
        self._print_change(emoji_key, message, player_color)
        
        # Mettre à jour le dernier message pour éviter les répétitions
        self._last_buy_property_message = message 