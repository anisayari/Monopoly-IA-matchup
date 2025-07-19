"""
Gestionnaire de démarrage automatique de tous les systèmes
"""
import os
import sys
import time
import subprocess
import threading
from typing import Optional

class AutoStartManager:
    """Gère le démarrage automatique et synchronisé de tous les systèmes"""
    
    def __init__(self, config, event_bus=None):
        self.config = config
        self.event_bus = event_bus
        self.processes = {
            'omniparser': None,
            'monitor': None,
            'omniparser_terminal': None,
            'ai_actions_terminal': None
        }
        self.starting = False
        
    def start_all_systems(self, callback=None):
        """Démarre tous les systèmes dans le bon ordre"""
        if self.starting:
            return False
            
        self.starting = True
        
        # Démarrer dans un thread pour ne pas bloquer
        thread = threading.Thread(
            target=self._start_sequence,
            args=(callback,),
            daemon=True
        )
        thread.start()
        return True
        
    def _start_sequence(self, callback):
        """Séquence de démarrage des systèmes"""
        try:
            # 1. OmniParser est déjà lancé par START_MONOPOLY.bat
            self._log("📡 Vérification d'OmniParser...")
            if self._is_omniparser_running():
                self._log("✅ OmniParser déjà actif")
            else:
                self._log("⚠️  OmniParser non détecté - lancez-le manuellement si nécessaire")
            
            # 2. Attendre un peu pour Dolphin
            self._log("⏳ Attente de l'initialisation de Dolphin...")
            time.sleep(5)
            
            # 3. Les terminaux sont déjà lancés par START_MONOPOLY.bat
            # Ne pas les relancer pour éviter les doublons
            # self._start_omniparser_terminal()
            # self._start_ai_actions_terminal()
            
            # 4. Lancer le Monitor maintenant que Dolphin est démarré
            self._log("🔍 Démarrage du Monitor...")
            self._start_monitor()
            
            # 5. Tout est prêt
            self._log("✅ Tous les systèmes sont opérationnels!")
            
            if self.event_bus:
                self.event_bus.publish('system.ready', {
                    'services': ['omniparser', 'dolphin', 'monitor', 'terminals'],
                    'status': 'operational'
                })
                
            if callback:
                callback(True, "All systems started successfully")
                
        except Exception as e:
            self._log(f"❌ Erreur: {str(e)}", level='error')
            if callback:
                callback(False, str(e))
        finally:
            self.starting = False
    
    def _start_omniparser(self):
        """Démarre OmniParser Lite en natif avec support GPU"""
        omniparser_script = os.path.join(self.config.WORKSPACE_DIR, 'omniparser_lite.py')
        
        if sys.platform == 'win32':
            # Windows - démarrer minimisé
            cmd = f'start "OmniParser Lite" /min cmd /k "python {omniparser_script}"'
            self.processes['omniparser'] = subprocess.Popen(cmd, shell=True)
        else:
            # Linux/Mac
            self.processes['omniparser'] = subprocess.Popen(
                ['python', omniparser_script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
    
    def _start_monitor(self):
        """Démarre le Monitor centralisé"""
        # Vérifier si le monitor n'est pas déjà en cours d'exécution
        if self._is_monitor_running():
            self._log("✅ Monitor déjà en cours d'exécution")
            return
            
        monitor_script = os.path.join(self.config.WORKSPACE_DIR, 'monitor_centralized.py')
        
        if sys.platform == 'win32':
            # Windows - démarrer minimisé
            cmd = f'start "Monopoly IA - Monitor" /min cmd /k "python {monitor_script}"'
            self.processes['monitor'] = subprocess.Popen(cmd, shell=True)
        else:
            # Linux/Mac
            self.processes['monitor'] = subprocess.Popen(
                ['python', monitor_script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
    
    def _start_omniparser_terminal(self):
        """Ouvre un terminal pour OmniParser"""
        if sys.platform == 'win32':
            # Windows - lancer directement omniparser_lite.py ou omniparser_server_native.py
            if os.path.exists(os.path.join(self.config.WORKSPACE_DIR, 'omniparser_lite.py')):
                cmd = f'start "OmniParser Terminal" cmd /k "cd /d {self.config.WORKSPACE_DIR} && python omniparser_lite.py"'
            else:
                cmd = f'start "OmniParser Terminal" cmd /k "cd /d {self.config.WORKSPACE_DIR} && python omniparser_server_native.py"'
            self.processes['omniparser_terminal'] = subprocess.Popen(cmd, shell=True)
        else:
            # Linux/Mac - terminal pour OmniParser
            cmd = ['gnome-terminal', '--', 'python', 'omniparser_server_native.py']
            self.processes['omniparser_terminal'] = subprocess.Popen(cmd)
    
    def _start_ai_actions_terminal(self):
        """Ouvre un terminal pour AI Actions (prêt à utiliser)"""
        if sys.platform == 'win32':
            # Windows - lancer directement ai_actions_server.py
            cmd = f'start "AI Actions Terminal" cmd /k "cd /d {self.config.WORKSPACE_DIR} && python ai_actions_server.py"'
            self.processes['ai_actions_terminal'] = subprocess.Popen(cmd, shell=True)
        else:
            # Linux/Mac - terminal pour AI Actions
            ai_script = os.path.join(self.config.WORKSPACE_DIR, 'ai_actions_server.py')
            cmd = ['gnome-terminal', '--', 'python', ai_script]
            self.processes['ai_actions_terminal'] = subprocess.Popen(cmd)
    
    def _is_omniparser_running(self) -> bool:
        """Vérifie si OmniParser est accessible"""
        try:
            import urllib.request
            response = urllib.request.urlopen('http://localhost:8000/probe/', timeout=2)
            return response.status == 200
        except:
            return False
    
    def _is_monitor_running(self) -> bool:
        """Vérifie si le Monitor est déjà en cours d'exécution"""
        if sys.platform == 'win32':
            # Windows - vérifier si un processus python avec monitor_centralized.py existe
            try:
                result = subprocess.run(
                    'wmic process where "name=\'python.exe\'" get commandline',
                    shell=True,
                    capture_output=True,
                    text=True
                )
                return 'monitor_centralized.py' in result.stdout
            except:
                return False
        else:
            # Linux/Mac - utiliser ps
            try:
                result = subprocess.run(
                    ['ps', 'aux'],
                    capture_output=True,
                    text=True
                )
                return 'monitor_centralized.py' in result.stdout
            except:
                return False
    
    def _wait_for_omniparser(self, timeout=30):
        """Attend qu'OmniParser soit prêt"""
        start_time = time.time()
        self._log("⏳ Attente du démarrage d'OmniParser (jusqu'à 30s)...")
        
        while time.time() - start_time < timeout:
            if self._is_omniparser_running():
                self._log("✅ OmniParser est prêt")
                return True
            time.sleep(2)
            
        self._log("⚠️ OmniParser n'est pas accessible sur http://localhost:8000")
        return False  # Continue anyway
    
    def stop_all_systems(self):
        """Arrête tous les systèmes"""
        self._log("🛑 Arrêt de tous les systèmes...")
        
        # Arrêter le monitor
        if self.processes.get('monitor'):
            try:
                self.processes['monitor'].terminate()
                self._log("Monitor arrêté")
            except:
                pass
        
        # Arrêter les terminaux
        for terminal_name in ['omniparser_terminal', 'ai_actions_terminal']:
            if self.processes.get(terminal_name):
                try:
                    self.processes[terminal_name].terminate()
                    self._log(f"{terminal_name} terminal fermé")
                except:
                    pass
        
        # Arrêter OmniParser
        if self.processes.get('omniparser'):
            try:
                self.processes['omniparser'].terminate()
                self._log("OmniParser arrêté")
            except:
                pass
            
        self.processes = {
            'omniparser': None, 
            'monitor': None, 
            'omniparser_terminal': None, 
            'ai_actions_terminal': None
        }
        self._log("✅ Tous les systèmes arrêtés")
    
    def _log(self, message, level='info'):
        """Log un message"""
        print(message)
        if self.event_bus:
            self.event_bus.publish('system.log', {
                'message': message,
                'level': level
            })