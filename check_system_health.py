#!/usr/bin/env python3
"""
Script pour vérifier la santé complète du système Monopoly IA
"""

import requests
import time
import sys
from colorama import init, Fore, Style

init()  # Initialiser colorama pour Windows

def print_header():
    print("\n" + "="*60)
    print("         MONOPOLY IA - SYSTEM HEALTH CHECK")
    print("="*60 + "\n")

def check_service(name, url, timeout=5):
    """Vérifie qu'un service répond"""
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code < 500:
            return True, response.status_code, response.elapsed.total_seconds()
        return False, response.status_code, response.elapsed.total_seconds()
    except requests.exceptions.ConnectionError:
        return False, "Connection refused", None
    except requests.exceptions.Timeout:
        return False, "Timeout", None
    except Exception as e:
        return False, str(e), None

def main():
    print_header()
    
    services = [
        ("Flask Server", "http://localhost:5000/api/health", 5000),
        ("OmniParser", "http://localhost:8000/health", 8000),
        ("Unified Decision Server", "http://localhost:7000/api/decision/health", 7000),
        ("Redis (optional)", "http://localhost:6379", 6379)
    ]
    
    all_ok = True
    results = []
    
    print("Vérification des services...\n")
    
    for name, url, port in services:
        print(f"Checking {name}...", end=" ")
        is_ok, status, response_time = check_service(name, url)
        
        if is_ok:
            if response_time:
                print(f"{Fore.GREEN}✓ OK{Style.RESET_ALL} (Status: {status}, Time: {response_time:.2f}s)")
            else:
                print(f"{Fore.GREEN}✓ OK{Style.RESET_ALL} (Status: {status})")
            results.append((name, True))
        else:
            print(f"{Fore.RED}✗ FAILED{Style.RESET_ALL} ({status})")
            if "Redis" not in name:  # Redis est optionnel
                all_ok = False
            results.append((name, False))
    
    # Test de communication inter-services
    print("\nTest de communication inter-services...")
    
    try:
        # Test Flask -> Health Check complet
        print("Testing Flask health check endpoint...", end=" ")
        response = requests.get("http://localhost:5000/api/health")
        if response.ok:
            health_data = response.json()
            if health_data.get("ready"):
                print(f"{Fore.GREEN}✓ System Ready{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}⚠ System Degraded{Style.RESET_ALL}")
                critical_issues = health_data.get("summary", {}).get("critical_issues", [])
                if critical_issues:
                    print(f"  Critical issues: {', '.join(critical_issues)}")
        else:
            print(f"{Fore.RED}✗ Failed{Style.RESET_ALL}")
            all_ok = False
    except:
        print(f"{Fore.RED}✗ Failed{Style.RESET_ALL}")
        all_ok = False
    
    # Résumé
    print("\n" + "="*60)
    if all_ok:
        print(f"{Fore.GREEN}✅ SYSTÈME OPÉRATIONNEL{Style.RESET_ALL}")
        print("\nTous les services critiques sont actifs!")
        print("\nInterfaces disponibles:")
        print(f"  - Dashboard: {Fore.CYAN}http://localhost:5000{Style.RESET_ALL}")
        print(f"  - Monitoring: {Fore.CYAN}http://localhost:5000/monitoring{Style.RESET_ALL}")
        print(f"  - Admin: {Fore.CYAN}http://localhost:5000/admin{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}❌ PROBLÈMES DÉTECTÉS{Style.RESET_ALL}")
        print("\nCertains services ne répondent pas correctement.")
        print("Vérifiez que tous les services sont démarrés avec:")
        print(f"  {Fore.YELLOW}start_monopoly_ia_v2.bat{Style.RESET_ALL}")
    
    print("="*60 + "\n")
    
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())