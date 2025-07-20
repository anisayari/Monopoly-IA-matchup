import time
import requests
import psutil
import logging
from typing import Dict, List, Tuple, Optional
import subprocess
import socket
from pathlib import Path

class HealthCheckService:
    """Service pour vérifier la santé de tous les composants du système"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.services = {
            "flask": {
                "url": "http://localhost:5000/api/context",
                "port": 5000,
                "name": "Flask Main Server",
                "critical": True
            },
            "omniparser": {
                "url": "http://localhost:8002/health",
                "port": 8002,
                "name": "OmniParser Service",
                "critical": True,
                "startup_script": "start_omniparser_with_monitor.bat"
            },
            "redis": {
                "port": 6379,
                "name": "Redis Server",
                "critical": False,
                "check_method": "port"
            }
        }
        
    def check_port(self, port: int) -> bool:
        """Vérifie si un port est ouvert"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result == 0
        
    def check_http_endpoint(self, url: str, timeout: int = 5) -> Tuple[bool, Optional[int]]:
        """Vérifie un endpoint HTTP"""
        try:
            response = requests.get(url, timeout=timeout)
            return response.status_code < 500, response.status_code
        except requests.exceptions.RequestException:
            return False, None
            
    def check_process(self, process_name: str) -> bool:
        """Vérifie si un processus est en cours d'exécution"""
        for process in psutil.process_iter(['name']):
            if process_name.lower() in process.info['name'].lower():
                return True
        return False
        
    def start_service(self, service_config: dict) -> bool:
        """Démarre un service s'il n'est pas actif"""
        if "startup_script" in service_config:
            script_path = Path(service_config["startup_script"])
            if script_path.exists():
                try:
                    subprocess.Popen(
                        str(script_path),
                        shell=True,
                        creationflags=subprocess.CREATE_NEW_CONSOLE
                    )
                    time.sleep(5)  # Attendre le démarrage
                    return True
                except Exception as e:
                    self.logger.error(f"Erreur lors du démarrage de {service_config['name']}: {e}")
        return False
        
    def check_all_services(self) -> Dict[str, Dict]:
        """Vérifie tous les services et retourne leur statut"""
        results = {}
        
        for service_id, config in self.services.items():
            result = {
                "name": config["name"],
                "status": "unknown",
                "details": "",
                "critical": config.get("critical", False)
            }
            
            # Vérification par port
            if "port" in config:
                if self.check_port(config["port"]):
                    result["status"] = "running"
                    result["details"] = f"Port {config['port']} is open"
                    
                    # Vérification HTTP si disponible
                    if "url" in config:
                        http_ok, status_code = self.check_http_endpoint(config["url"])
                        if http_ok:
                            result["status"] = "healthy"
                            result["details"] = f"HTTP endpoint responding (status: {status_code})"
                        else:
                            result["status"] = "unhealthy"
                            result["details"] = f"Port open but HTTP endpoint not responding"
                else:
                    result["status"] = "stopped"
                    result["details"] = f"Port {config['port']} is closed"
                    
            results[service_id] = result
            
        return results
        
    def perform_startup_checks(self, auto_start: bool = True) -> Tuple[bool, List[str]]:
        """
        Perform startup health checks
        
        Args:
            auto_start: If True, attempt to start missing services
            
        Returns:
            Tuple (all_healthy, messages)
        """
        messages = []
        all_healthy = True
        
        self.logger.info("Starting health checks...")
        messages.append("[HEALTH] Starting system health checks...")
        
        # Check Dolphin
        if self.check_process("Dolphin.exe"):
            messages.append("[OK] Dolphin is running")
        else:
            messages.append("[INFO] Dolphin not started (will be launched via interface)")
            
        # Check all services
        results = self.check_all_services()
        
        for service_id, result in results.items():
            config = self.services[service_id]
            
            if result["status"] in ["healthy", "running"]:
                messages.append(f"[OK] {result['name']}: {result['details']}")
            else:
                if config["critical"]:
                    all_healthy = False
                    
                messages.append(f"[FAIL] {result['name']}: {result['details']}")
                
                # Attempt to start service if auto_start is enabled
                if auto_start and result["status"] == "stopped":
                    messages.append(f"[START] Attempting to start {result['name']}...")
                    if self.start_service(config):
                        time.sleep(3)
                        # Recheck after startup
                        new_results = self.check_all_services()
                        if new_results[service_id]["status"] in ["healthy", "running"]:
                            messages.append(f"[OK] {result['name']} started successfully!")
                        else:
                            messages.append(f"[FAIL] Failed to start {result['name']}")
                            
        # Check inter-service communication
        comm_ok, comm_messages = self.check_inter_service_communication()
        messages.extend(comm_messages)
        
        if not comm_ok:
            all_healthy = False
            
        return all_healthy, messages
        
    def check_inter_service_communication(self) -> Tuple[bool, List[str]]:
        """Check communication between services"""
        messages = []
        all_ok = True
        
        # Check if Flask can access OmniParser
        try:
            response = requests.get("http://localhost:5000/api/omniparser/status", timeout=5)
            if response.status_code == 200:
                messages.append("[OK] Communication Flask <-> OmniParser: Working")
            else:
                messages.append("[FAIL] Communication Flask <-> OmniParser: Error")
                all_ok = False
        except:
            messages.append("[FAIL] Communication Flask <-> OmniParser: Unable to verify")
            all_ok = False
            
        return all_ok, messages
        
    def get_system_status(self) -> Dict:
        """Retourne un résumé complet du statut système"""
        results = self.check_all_services()
        
        # Compter les services par statut
        status_counts = {
            "healthy": 0,
            "running": 0,
            "unhealthy": 0,
            "stopped": 0
        }
        
        critical_issues = []
        
        for service_id, result in results.items():
            status_counts[result["status"]] = status_counts.get(result["status"], 0) + 1
            if result["critical"] and result["status"] not in ["healthy", "running"]:
                critical_issues.append(result["name"])
                
        return {
            "services": results,
            "summary": {
                "total": len(results),
                "healthy": status_counts["healthy"] + status_counts["running"],
                "issues": status_counts["unhealthy"] + status_counts["stopped"],
                "critical_issues": critical_issues
            },
            "ready": len(critical_issues) == 0
        }


if __name__ == "__main__":
    # Test the service
    logging.basicConfig(level=logging.INFO)
    checker = HealthCheckService()
    
    print("\n" + "="*60)
    print("         MONOPOLY IA - SYSTEM HEALTH CHECK")
    print("="*60 + "\n")
    
    all_healthy, messages = checker.perform_startup_checks(auto_start=True)
    
    for msg in messages:
        print(msg)
        
    print("\n" + "="*60)
    if all_healthy:
        print("[SUCCESS] SYSTEM READY - All critical services are operational")
    else:
        print("[ERROR] PROBLEMS DETECTED - Some services require attention")
    print("="*60 + "\n")