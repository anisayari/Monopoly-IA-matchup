"""
AI Actions Server - Gère les décisions IA et affiche le contexte du jeu
"""
import os
import sys
import time
import json
import requests
from datetime import datetime
from typing import Dict, Optional
import threading
from colorama import init, Fore, Back, Style

# Initialiser colorama pour les couleurs Windows
init()

class AIActionsServer:
    def __init__(self, api_url="http://localhost:5000"):
        self.api_url = api_url
        self.running = False
        self.game_context = {}
        self.last_update = None
        self.last_action = None
        self.stats = {
            'popups_detected': 0,
            'decisions_made': 0,
            'ai_calls': 0,
            'errors': 0,
            'keyboard_actions': 0
        }
        
    def clear_screen(self):
        """Efface l'écran"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
    def display_header(self):
        """Affiche l'en-tête"""
        print(f"{Back.BLUE}{Fore.WHITE} AI ACTIONS & GAME CONTEXT MONITOR {Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"API: {self.api_url} | Dernière mise à jour: {self.last_update or 'N/A'}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
        
    def display_players(self):
        """Affiche les informations des joueurs"""
        players = self.game_context.get('players', {})
        if not players:
            print(f"{Fore.YELLOW}Aucun joueur détecté{Style.RESET_ALL}\n")
            return
            
        print(f"{Fore.GREEN}JOUEURS:{Style.RESET_ALL}")
        print(f"{'Nom':<15} {'Argent':>10} {'Position':>10} {'Propriétés':>12}")
        print("-" * 50)
        
        for player_id, player in players.items():
            name = player.get('name', 'Inconnu')
            money = player.get('money', 0)
            position = player.get('position', 0)
            properties = len(player.get('properties', []))
            
            # Couleur selon l'argent
            if money < 500:
                color = Fore.RED
            elif money < 1500:
                color = Fore.YELLOW
            else:
                color = Fore.GREEN
                
            print(f"{name:<15} {color}{money:>10}€{Style.RESET_ALL} {position:>10} {properties:>12}")
        print()
        
    def display_game_state(self):
        """Affiche l'état global du jeu"""
        global_info = self.game_context.get('global', {})
        
        print(f"{Fore.GREEN}ÉTAT DU JEU:{Style.RESET_ALL}")
        print(f"Tour actuel: {global_info.get('current_turn', 0)}")
        print(f"Nombre de joueurs: {global_info.get('player_count', 0)}")
        print(f"Propriétés sur le plateau: {len(global_info.get('properties', []))}")
        
        # Afficher le dernier événement
        events = self.game_context.get('events', [])
        if events:
            last_event = events[-1]
            print(f"\nDernier événement: {Fore.CYAN}{last_event.get('description', 'N/A')}{Style.RESET_ALL}")
        print()
        
    def display_ai_stats(self):
        """Affiche les statistiques IA"""
        print(f"{Fore.GREEN}STATISTIQUES IA:{Style.RESET_ALL}")
        print(f"Popups détectés: {self.stats['popups_detected']}")
        print(f"Décisions prises: {self.stats['decisions_made']}")
        print(f"Appels IA: {self.stats['ai_calls']}")
        print(f"Actions clavier: {self.stats['keyboard_actions']}")
        print(f"Erreurs: {Fore.RED}{self.stats['errors']}{Style.RESET_ALL}")
        print()
        
    def display_active_popups(self):
        """Affiche les popups actifs"""
        try:
            response = requests.get(f"{self.api_url}/api/popups/active", timeout=2)
            if response.ok:
                popups = response.json()
                if popups:
                    print(f"{Fore.YELLOW}POPUPS ACTIFS:{Style.RESET_ALL}")
                    for popup in popups:
                        print(f"- [{popup.get('id', 'N/A')}] {popup.get('text', 'N/A')[:50]}...")
                        if popup.get('decision'):
                            print(f"  → Décision: {Fore.GREEN}{popup['decision']}{Style.RESET_ALL}")
                    print()
        except:
            pass
    
    def display_last_action(self):
        """Affiche la dernière action effectuée"""
        if hasattr(self, 'last_action') and self.last_action is not None:
            print(f"{Fore.CYAN}DERNIÈRE ACTION:{Style.RESET_ALL}")
            print(f"Type: {self.last_action.get('type', 'N/A')}")
            print(f"Description: {self.last_action.get('description', 'N/A')}")
            print(f"Timestamp: {self.last_action.get('timestamp', 'N/A')}")
            print()
            
    def fetch_game_context(self):
        """Récupère le contexte du jeu"""
        try:
            response = requests.get(f"{self.api_url}/api/context", timeout=2)
            if response.ok:
                self.game_context = response.json()
                self.last_update = datetime.now().strftime("%H:%M:%S")
                return True
        except Exception as e:
            self.stats['errors'] += 1
        return False
        
    def handle_popup_decisions(self):
        """Gère les décisions de popups en attente"""
        try:
            # Vérifier les popups actifs
            response = requests.get(f"{self.api_url}/api/popups/active", timeout=2)
            if response.ok:
                popups = response.json()
                
                for popup in popups:
                    if popup.get('status') == 'analyzed' and not popup.get('decision'):
                        # Popup en attente de décision
                        self.stats['popups_detected'] += 1
                        
                        # Demander une décision
                        decision_response = requests.post(
                            f"{self.api_url}/api/popups/{popup['id']}/decide",
                            json={'game_context': self.game_context},
                            timeout=5
                        )
                        
                        if decision_response.ok:
                            self.stats['decisions_made'] += 1
                            self.stats['ai_calls'] += 1
                            print(f"{Fore.GREEN}✓ Décision prise pour popup {popup['id']}{Style.RESET_ALL}")
                        
        except Exception as e:
            self.stats['errors'] += 1
            
    def display_loop(self):
        """Boucle d'affichage principal"""
        while self.running:
            self.clear_screen()
            self.display_header()
            
            if self.fetch_game_context():
                self.display_game_state()
                self.display_players()
                self.display_active_popups()
                self.display_last_action()
                self.display_ai_stats()
                
                # Gérer les décisions en arrière-plan
                threading.Thread(target=self.handle_popup_decisions, daemon=True).start()
            else:
                print(f"{Fore.RED}⚠ Impossible de récupérer le contexte du jeu{Style.RESET_ALL}")
                print("Vérifiez que le serveur Flask est démarré sur http://localhost:5000")
                
            # Instructions
            print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
            print("Appuyez sur Ctrl+C pour arrêter")
            print(f"Rafraîchissement automatique toutes les 2 secondes")
            
            time.sleep(2)
            
    def run(self):
        """Lance le serveur"""
        self.running = True
        print(f"{Fore.GREEN}🚀 AI Actions Server démarré !{Style.RESET_ALL}")
        print("Connexion au serveur principal...")
        
        try:
            self.display_loop()
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Arrêt du serveur...{Style.RESET_ALL}")
            self.running = False

if __name__ == "__main__":
    # Permettre de spécifier l'URL du serveur
    api_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
    
    server = AIActionsServer(api_url)
    server.run()