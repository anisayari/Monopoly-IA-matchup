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
import requests
import os

# Initialiser colorama pour Windows
init()

class AIActionsMonitor:
    def __init__(self, port=8004):
        self.app = web.Application()
        self.port = port
        self.current_context = {
            'global': {'current_turn': 0, 'current_player': 'N/A'},
            'players': {}
        }
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
        
        # Informations des joueurs - TOUJOURS les afficher
        players = context.get('players', {})
        print(f"\n{Fore.YELLOW}👥 Joueurs:{Style.RESET_ALL}")
        if players:
            for player_key, player_data in players.items():
                name = player_data.get('name', player_key)
                
                # Vérifier si le nom est corrompu (caractères non-ASCII)
                if name and any(ord(c) > 127 for c in name):
                    print(f"\n   {Fore.RED}⚠️  {player_key}: Nom corrompu détecté - réinitialisation nécessaire{Style.RESET_ALL}")
                    print(f"      {Fore.YELLOW}💡 Relancez Dolphin via l'interface web pour réinitialiser les noms{Style.RESET_ALL}")
                    continue
                
                money = player_data.get('money', 0)
                position = player_data.get('current_space', 'Unknown')
                player_properties = player_data.get('properties', [])
                properties_count = len(player_properties)
                is_current = "🎮" if player_data.get('is_current', False) else "  "
                jail = " 🔒" if player_data.get('jail', False) else ""
                
                # Couleur selon l'argent
                if money >= 1500:
                    money_color = Fore.GREEN
                elif money >= 500:
                    money_color = Fore.YELLOW
                else:
                    money_color = Fore.RED
                    
                print(f"   {is_current} {Fore.CYAN}{name}{Style.RESET_ALL}: {money_color}${money}{Style.RESET_ALL} | 🏠 {properties_count} props | 📍 {position}{jail}")
                
                # Toujours afficher les propriétés du joueur (même si vide)
                print(f"      {Fore.LIGHTBLACK_EX}Propriétés:{Style.RESET_ALL}")
                if player_properties:
                    # Grouper par couleur
                    props_by_group = {}
                    for prop in player_properties:
                        group = prop.get('group', 'unknown')
                        if group not in props_by_group:
                            props_by_group[group] = []
                        props_by_group[group].append(prop.get('name', 'Unknown'))
                    
                    # Afficher par groupe avec emojis
                    group_emojis = {
                        'brown': '🏞️',
                        'light_blue': '🌊',
                        'pink': '🌸',
                        'orange': '🍊',
                        'red': '🔴',
                        'yellow': '🌟',
                        'green': '🌳',
                        'dark_blue': '🌃',
                        'station': '🚂',
                        'utility': '⚡'
                    }
                    
                    for group, props in props_by_group.items():
                        emoji = group_emojis.get(group, '🏠')
                        group_color = self._get_group_color(group)
                        print(f"        {emoji} {group_color}{group.replace('_', ' ').title()}{Style.RESET_ALL}: {', '.join(props)}")
                else:
                    print(f"        {Fore.LIGHTBLACK_EX}Aucune propriété pour le moment{Style.RESET_ALL}")
                print()  # Ligne vide entre les joueurs
        else:
            print(f"   {Fore.LIGHTBLACK_EX}Aucun joueur détecté pour le moment{Style.RESET_ALL}")
        
        # Résumé global des propriétés
        properties = global_data.get('properties', [])
        if properties:
            owned_properties = [p for p in properties if p.get('owner') is not None]
            if owned_properties:
                print(f"\n{Fore.YELLOW}🏘️ Résumé des propriétés:{Style.RESET_ALL}")
                print(f"   Total possédées: {len(owned_properties)}/{len(properties)}")
                
                # Compter par groupe
                groups_count = {}
                for prop in owned_properties:
                    group = prop.get('group', 'Other')
                    if group not in groups_count:
                        groups_count[group] = 0
                    groups_count[group] += 1
                
                if groups_count:
                    print(f"   Par groupe: {', '.join([f'{g}: {c}' for g, c in groups_count.items()])}")
                    
        # Statistiques rapides - TOUJOURS les afficher
        print(f"\n{Fore.YELLOW}📈 Statistiques:{Style.RESET_ALL}")
        if players:
            total_money = sum(p.get('money', 0) for p in players.values())
            avg_money = total_money / len(players) if players else 0
            print(f"   Argent total en jeu: ${total_money}")
            print(f"   Argent moyen: ${avg_money:.0f}")
            
            # Statistiques des propriétés
            total_props_owned = sum(len(p.get('properties', [])) for p in players.values())
            print(f"   Propriétés possédées: {total_props_owned}")
        else:
            print(f"   {Fore.LIGHTBLACK_EX}En attente des données...{Style.RESET_ALL}")
            
        print(f"\n{Fore.LIGHTBLACK_EX}{'═' * 60}{Style.RESET_ALL}")
    
    def _get_group_color(self, group):
        """Retourne la couleur Colorama pour un groupe de propriétés"""
        color_map = {
            'brown': Fore.YELLOW,
            'light_blue': Fore.LIGHTCYAN_EX,
            'pink': Fore.LIGHTMAGENTA_EX,
            'orange': Fore.LIGHTYELLOW_EX,
            'red': Fore.RED,
            'yellow': Fore.YELLOW,
            'green': Fore.GREEN,
            'dark_blue': Fore.BLUE,
            'station': Fore.WHITE,
            'utility': Fore.LIGHTWHITE_EX
        }
        return color_map.get(group, Fore.WHITE)
        
    async def fetch_initial_context(self):
        """Récupère le contexte initial depuis l'API Flask"""
        try:
            # Essayer de récupérer le contexte depuis l'API
            response = requests.get('http://localhost:5000/api/context', timeout=2)
            if response.status_code == 200:
                context = response.json()
                if context and 'players' in context and context['players']:
                    print(f"{Fore.GREEN}✅ Contexte récupéré depuis l'API Flask{Style.RESET_ALL}")
                    self.current_context = context
                    return True
                else:
                    print(f"{Fore.YELLOW}⚠️  Contexte vide ou incomplet{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}⚠️  Impossible de récupérer le contexte (status: {response.status_code}){Style.RESET_ALL}")
        except requests.exceptions.ConnectionError:
            print(f"{Fore.RED}❌ Impossible de se connecter à l'API Flask (localhost:5000){Style.RESET_ALL}")
            print(f"{Fore.YELLOW}💡 Assurez-vous que app.py est lancé{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}❌ Erreur lors de la récupération du contexte: {e}{Style.RESET_ALL}")
        
        # Essayer de charger depuis le fichier si disponible
        try:
            context_path = os.path.join(os.path.dirname(__file__), 'contexte', 'game_context.json')
            if os.path.exists(context_path):
                with open(context_path, 'r', encoding='utf-8') as f:
                    context = json.load(f)
                    if context and 'players' in context and context['players']:
                        print(f"{Fore.GREEN}✅ Contexte chargé depuis le fichier{Style.RESET_ALL}")
                        self.current_context = context
                        return True
        except Exception as e:
            print(f"{Fore.YELLOW}⚠️  Impossible de charger le contexte depuis le fichier: {e}{Style.RESET_ALL}")
        
        return False
    
    async def start(self):
        """Démarre le serveur"""
        print(f"{Fore.BLUE}╔══════════════════════════════════════════════════════════╗{Style.RESET_ALL}")
        print(f"{Fore.BLUE}║      AI ACTIONS & GAME CONTEXT MONITOR - PORT {self.port}      ║{Style.RESET_ALL}")
        print(f"{Fore.BLUE}╚══════════════════════════════════════════════════════════╝{Style.RESET_ALL}")
        print(f"\n{Fore.CYAN}📡 En attente des actions et du contexte du jeu...{Style.RESET_ALL}\n")
        
        # Essayer de récupérer le contexte initial
        await self.fetch_initial_context()
        
        # Afficher le contexte initial
        self.display_context(self.current_context)
        
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