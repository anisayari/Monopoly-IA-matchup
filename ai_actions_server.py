"""
AI Actions & Game Context Monitor
Affiche les actions des IA et l'état du jeu en temps réel
"""

import asyncio
import aiohttp
from aiohttp import web
import json
from datetime import datetime
from colorama import init, Fore, Style, Back
import sys

# Initialiser colorama pour Windows
init()

class AIActionsMonitor:
    def __init__(self, port=8004):
        self.app = web.Application()
        self.port = port
        self.current_context = {}
        self.setup_routes()
        
    def setup_routes(self):
        """Configure les routes du serveur"""
        self.app.router.add_post('/action', self.handle_action)
        self.app.router.add_post('/context', self.handle_context)
        self.app.router.add_get('/health', self.health_check)
        
    async def handle_action(self, request):
        """Reçoit et affiche une action d'IA"""
        try:
            data = await request.json()
            
            # Extraire les données
            player = data.get('player', 'Unknown')
            action_type = data.get('type', 'unknown')
            decision = data.get('decision', '')
            reason = data.get('reason', '')
            confidence = data.get('confidence', 0)
            options = data.get('options', [])
            timestamp = data.get('timestamp', datetime.now().isoformat())
            
            # Afficher l'action
            self.display_action(player, action_type, decision, reason, confidence, options, timestamp)
            
            return web.json_response({'status': 'ok'})
        except Exception as e:
            print(f"❌ Erreur: {e}")
            return web.json_response({'error': str(e)}, status=500)
            
    async def handle_context(self, request):
        """Reçoit et affiche le contexte du jeu"""
        try:
            data = await request.json()
            self.current_context = data
            
            # Afficher le contexte
            self.display_context(data)
            
            return web.json_response({'status': 'ok'})
        except Exception as e:
            print(f"❌ Erreur: {e}")
            return web.json_response({'error': str(e)}, status=500)
            
    async def health_check(self, request):
        """Endpoint de santé"""
        return web.json_response({'status': 'healthy', 'service': 'ai_actions_monitor'})
        
    def display_action(self, player, action_type, decision, reason, confidence, options, timestamp):
        """Affiche une action d'IA formatée"""
        time_str = datetime.fromisoformat(timestamp).strftime("%H:%M:%S")
        
        # Emojis par type d'action
        action_emojis = {
            'buy': '🏠',
            'sell': '💰',
            'trade': '🤝',
            'build': '🏗️',
            'roll': '🎲',
            'jail': '🔒',
            'card': '🃏',
            'auction': '🔨',
            'rent': '💸',
            'turn': '⏭️',
            'unknown': '❓'
        }
        
        emoji = action_emojis.get(action_type, '❓')
        
        # Couleur selon la confiance
        if confidence >= 0.8:
            conf_color = Fore.GREEN
        elif confidence >= 0.5:
            conf_color = Fore.YELLOW
        else:
            conf_color = Fore.RED
            
        print(f"\n{Fore.LIGHTBLACK_EX}[{time_str}]{Style.RESET_ALL} {emoji} {Fore.CYAN}{player}{Style.RESET_ALL} - ACTION")
        print(f"   {Fore.WHITE}Décision:{Style.RESET_ALL} {Fore.YELLOW}{decision}{Style.RESET_ALL}")
        print(f"   {Fore.WHITE}Raison:{Style.RESET_ALL} {reason}")
        print(f"   {Fore.WHITE}Confiance:{Style.RESET_ALL} {conf_color}{confidence:.0%}{Style.RESET_ALL}")
        
        if options:
            print(f"   {Fore.WHITE}Options disponibles:{Style.RESET_ALL} {', '.join(options)}")
            
        print(f"{Fore.LIGHTBLACK_EX}{'─' * 60}{Style.RESET_ALL}")
        
    def display_context(self, context):
        """Affiche le contexte du jeu"""
        print(f"\n{Fore.GREEN}╔══════════════════════════════════════════════════════════╗{Style.RESET_ALL}")
        print(f"{Fore.GREEN}║                    GAME CONTEXT UPDATE                    ║{Style.RESET_ALL}")
        print(f"{Fore.GREEN}╚══════════════════════════════════════════════════════════╝{Style.RESET_ALL}")
        
        # Informations globales
        global_data = context.get('global', {})
        print(f"\n{Fore.YELLOW}📊 État Global:{Style.RESET_ALL}")
        print(f"   Tour: {global_data.get('current_turn', 'N/A')}")
        print(f"   Joueur actuel: {Fore.CYAN}{global_data.get('current_player', 'N/A')}{Style.RESET_ALL}")
        
        # Informations des joueurs
        players = context.get('players', {})
        if players:
            print(f"\n{Fore.YELLOW}👥 Joueurs:{Style.RESET_ALL}")
            for player_key, player_data in players.items():
                name = player_data.get('name', player_key)
                money = player_data.get('money', 0)
                position = player_data.get('current_space', 'Unknown')
                properties = len(player_data.get('properties', []))
                is_current = "🎮" if player_data.get('is_current', False) else "  "
                jail = " 🔒" if player_data.get('jail', False) else ""
                
                # Couleur selon l'argent
                if money >= 1500:
                    money_color = Fore.GREEN
                elif money >= 500:
                    money_color = Fore.YELLOW
                else:
                    money_color = Fore.RED
                    
                print(f"   {is_current} {Fore.CYAN}{name}{Style.RESET_ALL}: {money_color}${money}{Style.RESET_ALL} | 🏠 {properties} props | 📍 {position}{jail}")
        
        # Propriétés par groupe
        properties = global_data.get('properties', [])
        if properties:
            print(f"\n{Fore.YELLOW}🏘️ Propriétés par groupe:{Style.RESET_ALL}")
            groups = {}
            for prop in properties:
                if prop.get('owner'):
                    group = prop.get('group', 'Other')
                    owner = prop['owner']
                    if group not in groups:
                        groups[group] = {}
                    if owner not in groups[group]:
                        groups[group][owner] = []
                    groups[group][owner].append(prop['name'])
            
            for group, owners in groups.items():
                print(f"   {Fore.LIGHTBLACK_EX}{group}:{Style.RESET_ALL}")
                for owner, props in owners.items():
                    print(f"      {owner}: {', '.join(props[:3])}" + (" ..." if len(props) > 3 else ""))
                    
        # Statistiques rapides
        if players:
            total_money = sum(p.get('money', 0) for p in players.values())
            avg_money = total_money / len(players) if players else 0
            print(f"\n{Fore.YELLOW}📈 Statistiques:{Style.RESET_ALL}")
            print(f"   Argent total en jeu: ${total_money}")
            print(f"   Argent moyen: ${avg_money:.0f}")
            
        print(f"\n{Fore.LIGHTBLACK_EX}{'═' * 60}{Style.RESET_ALL}")
        
    async def start(self):
        """Démarre le serveur"""
        print(f"{Fore.BLUE}╔══════════════════════════════════════════════════════════╗{Style.RESET_ALL}")
        print(f"{Fore.BLUE}║      AI ACTIONS & GAME CONTEXT MONITOR - PORT {self.port}      ║{Style.RESET_ALL}")
        print(f"{Fore.BLUE}╚══════════════════════════════════════════════════════════╝{Style.RESET_ALL}")
        print(f"\n{Fore.CYAN}📡 En attente des actions et du contexte du jeu...{Style.RESET_ALL}\n")
        
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', self.port)
        await site.start()
        
        # Garder le serveur actif
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Arrêt du serveur...{Style.RESET_ALL}")
            
if __name__ == '__main__':
    monitor = AIActionsMonitor(port=8004)
    asyncio.run(monitor.start())