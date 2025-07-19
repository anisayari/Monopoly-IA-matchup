"""
Service pour gérer le démarrage des processus dans un terminal intégré
"""
import os
import sys
import subprocess
import platform
import json
from pathlib import Path
from typing import List, Dict, Optional

class TerminalManager:
    """Gère le lancement de plusieurs processus dans un terminal divisé"""
    
    def __init__(self):
        self.system = platform.system()
        self.terminal_configs = self._load_terminal_configs()
        
    def _load_terminal_configs(self) -> dict:
        """Charge les configurations de terminaux supportés"""
        return {
            'windows_terminal': {
                'name': 'Windows Terminal',
                'check_command': 'where wt',
                'available': False
            },
            'conemu': {
                'name': 'ConEmu',
                'check_command': 'where ConEmu64',
                'available': False
            },
            'cmder': {
                'name': 'Cmder',
                'check_command': 'where cmder',
                'available': False
            },
            'tmux': {
                'name': 'tmux',
                'check_command': 'which tmux',
                'available': False
            }
        }
    
    def detect_available_terminals(self) -> List[str]:
        """Détecte les terminaux disponibles sur le système"""
        available = []
        
        for terminal_id, config in self.terminal_configs.items():
            try:
                if self.system == 'Windows' and terminal_id == 'tmux':
                    continue  # tmux n'est pas natif sur Windows
                    
                result = subprocess.run(
                    config['check_command'].split(),
                    capture_output=True,
                    shell=True
                )
                if result.returncode == 0:
                    config['available'] = True
                    available.append(terminal_id)
            except:
                pass
                
        return available
    
    def launch_integrated_terminal(self, services: List[Dict[str, str]]) -> bool:
        """
        Lance les services dans un terminal intégré
        
        Args:
            services: Liste de dicts avec 'name', 'command', 'delay'
        
        Returns:
            True si lancé avec succès
        """
        available_terminals = self.detect_available_terminals()
        
        if not available_terminals:
            print("❌ Aucun terminal avancé disponible")
            return False
        
        # Préférence: Windows Terminal > ConEmu > Cmder > tmux
        if 'windows_terminal' in available_terminals:
            return self._launch_windows_terminal(services)
        elif 'conemu' in available_terminals:
            return self._launch_conemu(services)
        elif 'cmder' in available_terminals:
            return self._launch_cmder(services)
        elif 'tmux' in available_terminals:
            return self._launch_tmux(services)
        
        return False
    
    def _launch_windows_terminal(self, services: List[Dict[str, str]]) -> bool:
        """Lance avec Windows Terminal"""
        try:
            # Construire la commande wt
            cmd = ['wt', '--title', 'Monopoly IA Manager', '--maximized']
            
            # Premier service dans l'onglet principal
            first_service = services[0]
            cmd.extend([
                'new-tab', '--title', 'Monopoly IA',
                '--suppressApplicationTitle',
                'cmd', '/k', f'cd /d {os.getcwd()} && echo === {first_service["name"]} === && {first_service["command"]}'
            ])
            
            # Services suivants en split-pane
            for i, service in enumerate(services[1:], 1):
                if i == 1:
                    # Split horizontal pour le 2e service
                    cmd.extend([';', 'split-pane', '-H', '-s', '0.5'])
                elif i == 2:
                    # Split vertical du panneau de gauche pour le 3e
                    cmd.extend([';', 'split-pane', '-V', '-t', '0', '-s', '0.5'])
                elif i == 3:
                    # Split vertical du panneau de droite pour le 4e
                    cmd.extend([';', 'split-pane', '-V', '-t', '1', '-s', '0.5'])
                
                delay = f'timeout /t {service.get("delay", 0)} && ' if service.get("delay", 0) > 0 else ''
                cmd.extend([
                    'cmd', '/k', 
                    f'cd /d {os.getcwd()} && echo === {service["name"]} === && {delay}{service["command"]}'
                ])
            
            # Lancer Windows Terminal
            subprocess.Popen(cmd)
            print("✅ Windows Terminal lancé avec tous les services")
            return True
            
        except Exception as e:
            print(f"❌ Erreur avec Windows Terminal: {e}")
            return False
    
    def _launch_conemu(self, services: List[Dict[str, str]]) -> bool:
        """Lance avec ConEmu"""
        try:
            # Construire la commande ConEmu
            cmd = ['ConEmu64', '-new_console:t:Monopoly IA', '-runlist']
            
            for i, service in enumerate(services):
                delay = f'timeout /t {service.get("delay", 0)} && ' if service.get("delay", 0) > 0 else ''
                service_cmd = f'cmd /k cd /d {os.getcwd()} && echo === {service["name"]} === && {delay}{service["command"]}'
                
                if i == 0:
                    cmd.append(service_cmd)
                else:
                    # Ajouter les splits
                    if i == 1:
                        cmd.extend(['-cur_console:s1TVn', '|||', service_cmd])
                    elif i == 2:
                        cmd.extend(['-cur_console:s1THn', '|||', service_cmd])
                    elif i == 3:
                        cmd.extend(['-cur_console:s2THn', '|||', service_cmd])
            
            subprocess.Popen(cmd)
            print("✅ ConEmu lancé avec tous les services")
            return True
            
        except Exception as e:
            print(f"❌ Erreur avec ConEmu: {e}")
            return False
    
    def _launch_tmux(self, services: List[Dict[str, str]]) -> bool:
        """Lance avec tmux (Linux/Mac/WSL)"""
        try:
            session_name = "monopoly-ia"
            
            # Créer une nouvelle session tmux
            subprocess.run(['tmux', 'new-session', '-d', '-s', session_name])
            
            # Configuration du layout
            for i, service in enumerate(services):
                if i == 0:
                    # Premier panneau (déjà créé avec la session)
                    subprocess.run([
                        'tmux', 'send-keys', '-t', f'{session_name}:0.0',
                        f'cd {os.getcwd()} && echo "=== {service["name"]} ===" && {service["command"]}',
                        'Enter'
                    ])
                elif i == 1:
                    # Split horizontal
                    subprocess.run(['tmux', 'split-window', '-h', '-t', f'{session_name}:0'])
                    subprocess.run([
                        'tmux', 'send-keys', '-t', f'{session_name}:0.1',
                        f'cd {os.getcwd()} && echo "=== {service["name"]} ===" && sleep {service.get("delay", 0)} && {service["command"]}',
                        'Enter'
                    ])
                elif i == 2:
                    # Split vertical du panneau de gauche
                    subprocess.run(['tmux', 'split-window', '-v', '-t', f'{session_name}:0.0'])
                    subprocess.run([
                        'tmux', 'send-keys', '-t', f'{session_name}:0.2',
                        f'cd {os.getcwd()} && echo "=== {service["name"]} ===" && sleep {service.get("delay", 0)} && {service["command"]}',
                        'Enter'
                    ])
                elif i == 3:
                    # Split vertical du panneau de droite
                    subprocess.run(['tmux', 'split-window', '-v', '-t', f'{session_name}:0.1'])
                    subprocess.run([
                        'tmux', 'send-keys', '-t', f'{session_name}:0.3',
                        f'cd {os.getcwd()} && echo "=== {service["name"]} ===" && sleep {service.get("delay", 0)} && {service["command"]}',
                        'Enter'
                    ])
            
            # Attacher à la session
            subprocess.run(['tmux', 'attach-session', '-t', session_name])
            print("✅ tmux lancé avec tous les services")
            return True
            
        except Exception as e:
            print(f"❌ Erreur avec tmux: {e}")
            return False
    
    def _launch_cmder(self, services: List[Dict[str, str]]) -> bool:
        """Lance avec Cmder"""
        # Cmder nécessite une configuration de tâche pré-définie
        print("⚠️  Cmder nécessite une configuration manuelle des tâches")
        print("   Créez une tâche 'monopoly_ia' avec 4 panneaux dans les paramètres Cmder")
        return False
    
    def create_config_file(self, services: List[Dict[str, str]]):
        """Crée un fichier de configuration pour les terminaux"""
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)
        
        config = {
            "services": services,
            "layout": "2x2",
            "terminal_preferences": [
                "windows_terminal",
                "conemu", 
                "tmux",
                "cmder"
            ]
        }
        
        config_file = config_dir / "terminal_layout.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        print(f"✅ Configuration sauvegardée dans {config_file}")


if __name__ == "__main__":
    # Test du terminal manager
    manager = TerminalManager()
    
    print("🔍 Détection des terminaux disponibles...")
    available = manager.detect_available_terminals()
    
    if available:
        print(f"✅ Terminaux disponibles: {', '.join(available)}")
    else:
        print("❌ Aucun terminal avancé détecté")
    
    # Configuration des services
    services = [
        {
            "name": "FLASK SERVER",
            "command": "python app.py",
            "delay": 0
        },
        {
            "name": "OMNIPARSER",
            "command": "python omniparser_server_native.py",
            "delay": 5
        },
        {
            "name": "MONITOR",
            "command": "python monitor_centralized.py",
            "delay": 10
        },
        {
            "name": "AI ACTIONS",
            "command": "echo Ready for AI actions",
            "delay": 0
        }
    ]
    
    # Créer le fichier de config
    manager.create_config_file(services)