#!/usr/bin/env python3
"""
Script de nettoyage des ports utilisés par le système Monopoly IA
Tue tous les processus qui utilisent les ports configurés
"""

import os
import sys
import subprocess
import platform
import socket
from colorama import init, Fore, Style

# Initialiser colorama
init()

# Liste des ports utilisés par le système
PORTS_TO_CHECK = [
    (5000, "Flask App"),
    (7000, "AI Decision Server"),
    (8000, "OmniParser Server"),
    (8001, "Popup Service"),
    (8002, "AI Service"),
    (8003, "AI Chat Monitor"),
    (8004, "AI Actions Monitor"),
    (9000, "Monitor Centralisé")
]

def is_windows():
    """Vérifie si on est sur Windows"""
    return platform.system().lower() == 'windows'

def check_port(port):
    """Vérifie si un port est utilisé"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    return result == 0  # True si le port est utilisé

def get_pid_using_port_windows(port):
    """Trouve le PID du processus utilisant un port sur Windows"""
    try:
        # Utiliser netstat pour trouver le processus
        cmd = f'netstat -ano | findstr :{port}'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.stdout:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                parts = line.split()
                if len(parts) >= 5 and f':{port}' in parts[1]:
                    # Le PID est le dernier élément
                    return int(parts[-1])
    except Exception as e:
        print(f"Erreur lors de la recherche du PID: {e}")
    return None

def get_pid_using_port_unix(port):
    """Trouve le PID du processus utilisant un port sur Unix/Linux"""
    try:
        # Utiliser lsof pour trouver le processus
        cmd = f'lsof -ti:{port}'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.stdout:
            return int(result.stdout.strip())
    except Exception as e:
        print(f"Erreur lors de la recherche du PID: {e}")
    return None

def kill_process_windows(pid):
    """Tue un processus sur Windows"""
    try:
        cmd = f'taskkill /F /PID {pid}'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def kill_process_unix(pid):
    """Tue un processus sur Unix/Linux"""
    try:
        os.kill(pid, 9)  # SIGKILL
        return True
    except:
        return False

def cleanup_port(port, service_name):
    """Nettoie un port spécifique"""
    print(f"\n{Fore.CYAN}Vérification du port {port} ({service_name})...{Style.RESET_ALL}")
    
    if not check_port(port):
        print(f"  {Fore.GREEN}✓ Port {port} disponible{Style.RESET_ALL}")
        return True
    
    print(f"  {Fore.YELLOW}⚠ Port {port} utilisé{Style.RESET_ALL}")
    
    # Trouver le PID
    if is_windows():
        pid = get_pid_using_port_windows(port)
    else:
        pid = get_pid_using_port_unix(port)
    
    if pid:
        print(f"  {Fore.YELLOW}→ Processus trouvé (PID: {pid}){Style.RESET_ALL}")
        
        # Tuer le processus
        if is_windows():
            success = kill_process_windows(pid)
        else:
            success = kill_process_unix(pid)
        
        if success:
            print(f"  {Fore.GREEN}✓ Processus tué avec succès{Style.RESET_ALL}")
            return True
        else:
            print(f"  {Fore.RED}✗ Impossible de tuer le processus{Style.RESET_ALL}")
            return False
    else:
        print(f"  {Fore.RED}✗ Impossible de trouver le processus{Style.RESET_ALL}")
        return False

def main():
    """Fonction principale"""
    print(f"{Fore.BLUE}{'=' * 50}{Style.RESET_ALL}")
    print(f"{Fore.BLUE}     NETTOYAGE DES PORTS - MONOPOLY IA{Style.RESET_ALL}")
    print(f"{Fore.BLUE}{'=' * 50}{Style.RESET_ALL}")
    
    all_cleaned = True
    
    for port, service_name in PORTS_TO_CHECK:
        if not cleanup_port(port, service_name):
            all_cleaned = False
    
    print(f"\n{Fore.BLUE}{'=' * 50}{Style.RESET_ALL}")
    
    if all_cleaned:
        print(f"{Fore.GREEN}✓ Tous les ports ont été nettoyés avec succès!{Style.RESET_ALL}")
        return 0
    else:
        print(f"{Fore.YELLOW}⚠ Certains ports n'ont pas pu être nettoyés{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}  Vous devrez peut-être fermer manuellement les applications{Style.RESET_ALL}")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Nettoyage interrompu par l'utilisateur{Style.RESET_ALL}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Fore.RED}Erreur: {e}{Style.RESET_ALL}")
        sys.exit(1)