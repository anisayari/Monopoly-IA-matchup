"""
AI Chat & Thoughts Monitor
Affiche les conversations et pensées des IA en temps réel
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

class AIChatMonitor:
    def __init__(self, port=8003):
        self.app = web.Application()
        self.port = port
        self.setup_routes()
        
    def setup_routes(self):
        """Configure les routes du serveur"""
        self.app.router.add_post('/chat', self.handle_chat)
        self.app.router.add_post('/thought', self.handle_thought)
        self.app.router.add_get('/health', self.health_check)
        
    async def handle_chat(self, request):
        """Reçoit et affiche un message de chat entre IA"""
        try:
            data = await request.json()
            
            # Extraire les données
            from_player = data.get('from', 'Unknown')
            to_player = data.get('to', 'All')
            message = data.get('message', '')
            timestamp = data.get('timestamp', datetime.now().isoformat())
            
            # Formater et afficher
            self.display_chat(from_player, to_player, message, timestamp)
            
            return web.json_response({'status': 'ok'})
        except Exception as e:
            print(f"❌ Erreur: {e}")
            return web.json_response({'error': str(e)}, status=500)
            
    async def handle_thought(self, request):
        """Reçoit et affiche une pensée/réflexion d'IA"""
        try:
            data = await request.json()
            
            # Extraire les données
            player = data.get('player', 'Unknown')
            thought_type = data.get('type', 'general')  # decision, strategy, analysis
            content = data.get('content', '')
            context = data.get('context', {})
            timestamp = data.get('timestamp', datetime.now().isoformat())
            
            # Formater et afficher
            self.display_thought(player, thought_type, content, context, timestamp)
            
            return web.json_response({'status': 'ok'})
        except Exception as e:
            print(f"❌ Erreur: {e}")
            return web.json_response({'error': str(e)}, status=500)
            
    async def health_check(self, request):
        """Endpoint de santé"""
        return web.json_response({'status': 'healthy', 'service': 'ai_chat_monitor'})
        
    def display_chat(self, from_player, to_player, message, timestamp):
        """Affiche un message de chat formaté"""
        time_str = datetime.fromisoformat(timestamp).strftime("%H:%M:%S")
        
        # Couleurs par joueur - détection intelligente
        player_colors = {
            'player1': Fore.CYAN,
            'player2': Fore.GREEN,
            'player3': Fore.YELLOW,
            'player4': Fore.MAGENTA,
            'GPT1': Fore.CYAN + Style.BRIGHT,
            'GPT2': Fore.GREEN + Style.BRIGHT,
            'Claude': Fore.MAGENTA + Style.BRIGHT,
            'Gemini': Fore.YELLOW + Style.BRIGHT,
            'Unknown': Fore.WHITE
        }
        
        color = player_colors.get(from_player, Fore.WHITE)
        
        print(f"\n{Fore.LIGHTBLACK_EX}[{time_str}]{Style.RESET_ALL} 💬 {color}{from_player}{Style.RESET_ALL} → {to_player}")
        print(f"   {message}")
        print(f"{Fore.LIGHTBLACK_EX}{'─' * 60}{Style.RESET_ALL}")
        
    def display_thought(self, player, thought_type, content, context, timestamp):
        """Affiche une pensée d'IA formatée"""
        time_str = datetime.fromisoformat(timestamp).strftime("%H:%M:%S")
        
        # Emojis par type de pensée
        thought_emojis = {
            'decision': '🎯',
            'strategy': '🧠',
            'analysis': '📊',
            'planning': '📋',
            'evaluation': '⚖️',
            'general': '💭'
        }
        
        # Couleurs par type
        thought_colors = {
            'decision': Fore.RED,
            'strategy': Fore.BLUE,
            'analysis': Fore.GREEN,
            'planning': Fore.YELLOW,
            'evaluation': Fore.MAGENTA,
            'general': Fore.WHITE
        }
        
        emoji = thought_emojis.get(thought_type, '💭')
        color = thought_colors.get(thought_type, Fore.WHITE)
        
        # Déterminer la couleur du joueur
        player_color = Fore.CYAN + Style.BRIGHT
        if 'Claude' in player:
            player_color = Fore.MAGENTA + Style.BRIGHT
        elif 'GPT2' in player:
            player_color = Fore.GREEN + Style.BRIGHT
        elif 'Gemini' in player:
            player_color = Fore.YELLOW + Style.BRIGHT
            
        print(f"\n{Fore.LIGHTBLACK_EX}[{time_str}]{Style.RESET_ALL} {emoji} {player_color}{player}{Style.RESET_ALL} - {color}{thought_type.upper()}{Style.RESET_ALL}")
        
        # Afficher le contenu principal avec formatage amélioré
        if isinstance(content, dict):
            if thought_type == 'analysis':
                if 'popup' in content:
                    print(f"   📋 {Fore.WHITE}Popup:{Style.RESET_ALL} \"{content['popup']}\"")
                if 'options_count' in content:
                    print(f"   🔢 {Fore.WHITE}Options:{Style.RESET_ALL} {content['options_count']} choix disponibles")
                if 'options' in content:
                    for idx, opt in enumerate(content['options'],1):
                        print(f"   {Fore.LIGHTBLUE_EX}{idx} Option : {Style.RESET_ALL} {opt}")
                if 'argent' in content:
                    print(f"   💰 {Fore.WHITE}Argent:{Style.RESET_ALL} {content['argent']}€")
            elif thought_type == 'decision':
                if 'choix' in content:
                    print(f"   ✅ {Fore.GREEN}Décision:{Style.RESET_ALL} {content['choix']}")
                if 'raison' in content:
                    print(f"   💭 {Fore.WHITE}Raison:{Style.RESET_ALL} {content['raison']}")
                if 'confiance' in content:
                    print(f"   📊 {Fore.WHITE}Confiance:{Style.RESET_ALL} {content['confiance']}")
            else:
                for key, value in content.items():
                    print(f"   {Fore.LIGHTBLACK_EX}{key}:{Style.RESET_ALL} {value}")
        else:
            print(f"   {content}")
            
        # Afficher le contexte si disponible avec meilleur formatage
        if context:
            context_items = []
            if 'tour' in context:
                context_items.append(f"Tour {context['tour']}")
            if 'position' in context:
                context_items.append(f"Position: {context['position']}")
            if context_items:
                print(f"   {Fore.LIGHTBLACK_EX}[{' | '.join(context_items)}]{Style.RESET_ALL}")
                
        print(f"{Fore.LIGHTBLACK_EX}{'═' * 60}{Style.RESET_ALL}")
        
    async def start(self):
        """Démarre le serveur"""
        print(f"{Fore.GREEN}╔══════════════════════════════════════════════════════════╗{Style.RESET_ALL}")
        print(f"{Fore.GREEN}║        AI CHAT & THOUGHTS MONITOR - PORT {self.port}        ║{Style.RESET_ALL}")
        print(f"{Fore.GREEN}╚══════════════════════════════════════════════════════════╝{Style.RESET_ALL}")
        print(f"\n{Fore.CYAN}📡 En attente des conversations et pensées des IA...{Style.RESET_ALL}\n")
        
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
    monitor = AIChatMonitor(port=8003)
    asyncio.run(monitor.start())