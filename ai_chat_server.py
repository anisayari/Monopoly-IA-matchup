"""
AI Chat Server - Affiche les pensées et discussions des IA
"""
import os
import sys
import time
from datetime import datetime
from colorama import init, Fore, Back, Style
import json
from collections import deque

# Ajouter le répertoire parent au path pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.event_bus import EventBus, EventTypes
from flask import Flask

# Initialiser colorama pour les couleurs Windows
init()

class AIChatServer:
    def __init__(self):
        self.app = Flask(__name__)
        self.event_bus = EventBus(self.app)
        self.chat_history = deque(maxlen=50)  # Garder les 50 derniers messages
        self.current_turn = 0
        self.players = {}
        
        # S'abonner aux événements
        self._subscribe_to_events()
        
    def _subscribe_to_events(self):
        """S'abonne aux événements pertinents"""
        # Événements de décision IA
        self.event_bus.subscribe('ai.decision_requested', self._on_decision_requested)
        self.event_bus.subscribe('ai.decision_made', self._on_decision_made)
        self.event_bus.subscribe('popup.decision_made', self._on_popup_decision)
        
        # Événements de jeu
        self.event_bus.subscribe('game_context.updated', self._on_game_context_updated)
        self.event_bus.subscribe('player.turn_started', self._on_turn_started)
        self.event_bus.subscribe('player.action', self._on_player_action)
        
        # Messages de chat IA
        self.event_bus.subscribe('ai.thought', self._on_ai_thought)
        self.event_bus.subscribe('ai.chat_message', self._on_ai_chat)
        
    def clear_screen(self):
        """Efface l'écran"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
    def display_header(self):
        """Affiche l'en-tête"""
        print(f"{Back.MAGENTA}{Fore.WHITE} AI CHAT & THOUGHTS MONITOR {Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}")
        print(f"Tour actuel: {self.current_turn} | Messages: {len(self.chat_history)}")
        print(f"{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}\n")
        
    def _format_timestamp(self, timestamp=None):
        """Formate un timestamp"""
        if timestamp is None:
            timestamp = datetime.now()
        return timestamp.strftime("%H:%M:%S")
        
    def _get_player_color(self, player_name):
        """Retourne une couleur pour chaque joueur"""
        colors = {
            "GPT1": Fore.BLUE,
            "GPT2": Fore.GREEN,
            "GPT3": Fore.YELLOW,
            "GPT4": Fore.CYAN
        }
        return colors.get(player_name, Fore.WHITE)
        
    def _add_message(self, message_type, player, content, extra=None):
        """Ajoute un message à l'historique"""
        self.chat_history.append({
            'timestamp': self._format_timestamp(),
            'type': message_type,
            'player': player,
            'content': content,
            'extra': extra or {}
        })
        
    def _on_decision_requested(self, event):
        """Quand une décision est demandée à l'IA"""
        data = event.get('data', {})
        player = data.get('player', 'Unknown')
        popup_text = data.get('popup_text', '')
        
        self._add_message(
            'thinking',
            player,
            f"🤔 Réflexion sur: {popup_text[:50]}...",
            {'popup_id': data.get('popup_id')}
        )
        
    def _on_decision_made(self, event):
        """Quand l'IA a pris une décision"""
        data = event.get('data', {})
        player = data.get('player', 'Unknown')
        decision = data.get('decision', '')
        reason = data.get('reason', '')
        confidence = data.get('confidence', 0)
        
        # Icône selon la confiance
        if confidence > 0.8:
            icon = "✅"
        elif confidence > 0.5:
            icon = "🤷"
        else:
            icon = "❓"
            
        self._add_message(
            'decision',
            player,
            f"{icon} Décision: {decision} ({confidence:.0%})\n   → {reason}",
            {'confidence': confidence}
        )
        
    def _on_popup_decision(self, event):
        """Décision sur un popup"""
        data = event.get('data', {})
        decision = data.get('decision', '')
        reason = data.get('reason', '')
        player = data.get('player', 'System')
        
        self._add_message(
            'popup_decision',
            player,
            f"📋 Popup: {decision} - {reason}"
        )
        
    def _on_game_context_updated(self, event):
        """Mise à jour du contexte de jeu"""
        data = event.get('data', {})
        if 'players' in data:
            self.players = data['players']
        if 'global' in data and 'current_turn' in data['global']:
            self.current_turn = data['global']['current_turn']
            
    def _on_turn_started(self, event):
        """Début du tour d'un joueur"""
        data = event.get('data', {})
        player = data.get('player', 'Unknown')
        
        self._add_message(
            'turn',
            player,
            f"🎲 C'est mon tour!",
            {'turn': self.current_turn}
        )
        
    def _on_player_action(self, event):
        """Action d'un joueur"""
        data = event.get('data', {})
        player = data.get('player', 'Unknown')
        action = data.get('action', '')
        details = data.get('details', '')
        
        self._add_message(
            'action',
            player,
            f"🎯 {action}: {details}"
        )
        
    def _on_ai_thought(self, event):
        """Pensée interne de l'IA"""
        data = event.get('data', {})
        player = data.get('player', 'Unknown')
        thought = data.get('thought', '')
        
        self._add_message(
            'thought',
            player,
            f"💭 {thought}"
        )
        
    def _on_ai_chat(self, event):
        """Message de chat public de l'IA"""
        data = event.get('data', {})
        player = data.get('player', 'Unknown')
        message = data.get('message', '')
        
        self._add_message(
            'chat',
            player,
            f"💬 {message}"
        )
        
    def display_messages(self):
        """Affiche les messages"""
        # Afficher les messages du plus ancien au plus récent
        for msg in self.chat_history:
            timestamp = msg['timestamp']
            msg_type = msg['type']
            player = msg['player']
            content = msg['content']
            
            # Couleur selon le type
            if msg_type == 'thinking':
                type_color = Fore.YELLOW
            elif msg_type == 'decision':
                type_color = Fore.GREEN
            elif msg_type == 'thought':
                type_color = Fore.CYAN
            elif msg_type == 'chat':
                type_color = Fore.WHITE
            elif msg_type == 'turn':
                type_color = Fore.MAGENTA
            else:
                type_color = Fore.WHITE
                
            # Couleur du joueur
            player_color = self._get_player_color(player)
            
            # Afficher le message
            print(f"{Fore.LIGHTBLACK_EX}[{timestamp}]{Style.RESET_ALL} "
                  f"{player_color}{player}{Style.RESET_ALL}: "
                  f"{type_color}{content}{Style.RESET_ALL}")
                  
        # Ligne de séparation
        print(f"\n{Fore.LIGHTBLACK_EX}{'─'*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}En attente de nouvelles pensées...{Style.RESET_ALL}")
        
    def display_loop(self):
        """Boucle d'affichage principal"""
        last_message_count = 0
        
        while True:
            # Rafraîchir seulement s'il y a de nouveaux messages
            if len(self.chat_history) != last_message_count:
                self.clear_screen()
                self.display_header()
                self.display_messages()
                last_message_count = len(self.chat_history)
                
            time.sleep(0.5)  # Vérifier toutes les 500ms
            
    def run(self):
        """Lance le serveur"""
        print(f"{Fore.MAGENTA}🧠 AI Chat Server démarré!{Style.RESET_ALL}")
        print("Affichage des pensées et discussions des IA...")
        print("Appuyez sur Ctrl+C pour arrêter\n")
        
        # Ajouter un message de bienvenue
        self._add_message(
            'system',
            'System',
            '🚀 AI Chat Monitor activé - En attente des IA...'
        )
        
        try:
            self.display_loop()
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Arrêt du serveur...{Style.RESET_ALL}")

if __name__ == "__main__":
    server = AIChatServer()
    server.run()