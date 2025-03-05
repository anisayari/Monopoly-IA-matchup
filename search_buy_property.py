import dolphin_memory_engine as dme
import re
import time
from colorama import init, Fore, Style

# Initialiser colorama pour les couleurs dans le terminal
init()

print(f"{Fore.GREEN}🔌 Tentative de connexion à Dolphin...{Style.RESET_ALL}")
dme.hook()
if not dme.is_hooked():
    print(f"{Fore.RED}❌ Impossible de se connecter à Dolphin. Assurez-vous que l'émulateur est en cours d'exécution.{Style.RESET_ALL}")
    exit(1)
print(f"{Fore.GREEN}✅ Connecté à Dolphin avec succès.{Style.RESET_ALL}")

# Plage mémoire pour la recherche
RAM_START = 0x90000000
RAM_SIZE = 0x00100000  # 1 Mo
CHUNK_SIZE = 0x10000   # 64 Ko par chunk

# Patterns pour trouver les messages d'achat de propriété
# Plusieurs patterns pour augmenter les chances de trouver les messages
patterns = [
    re.compile(b'D\x00o\x00 \x00y\x00o\x00u\x00', re.DOTALL),  # "Do you"
    re.compile(b'b\x00u\x00y\x00', re.DOTALL),                 # "buy"
    re.compile(b'p\x00r\x00o\x00p\x00e\x00r\x00t\x00y\x00', re.DOTALL),  # "property"
    re.compile(b'p\x00u\x00r\x00c\x00h\x00a\x00s\x00e\x00', re.DOTALL),  # "purchase"
    re.compile(b'W\x00o\x00u\x00l\x00d\x00 \x00y\x00o\x00u\x00', re.DOTALL),  # "Would you"
]

# Dictionnaire pour stocker les messages déjà vus
already_seen = {}

print(f"{Fore.CYAN}🔍 Début de la surveillance des messages d'achat de propriété...{Style.RESET_ALL}")
print(f"{Fore.YELLOW}Appuyez sur Ctrl+C pour arrêter.{Style.RESET_ALL}")

def scan_memory_for_buy_property():
    """Scan la mémoire par morceaux pour trouver les messages d'achat de propriété"""
    results = []
    
    for addr in range(RAM_START, RAM_START + RAM_SIZE, CHUNK_SIZE):
        try:
            chunk = dme.read_bytes(addr, CHUNK_SIZE)
            
            # Vérifier chaque pattern
            for pattern in patterns:
                matches = pattern.finditer(chunk)
                
                for match in matches:
                    start_pos = match.start()
                    # Lire jusqu'à 200 octets après le match pour capturer le message complet
                    message_bytes = chunk[start_pos:min(start_pos+200, len(chunk))]
                    
                    # Calculer l'adresse absolue du match
                    match_addr = addr + start_pos
                    
                    results.append((match_addr, message_bytes))
        except Exception as e:
            print(f"{Fore.RED}⚠️ Erreur lors de la lecture à l'adresse 0x{addr:08X}: {e}{Style.RESET_ALL}")
    
    return results

def is_buy_property_message(text):
    """Vérifie si le texte est un message d'achat de propriété"""
    keywords = ["buy", "purchase", "property", "would you like", "do you want"]
    return any(keyword in text.lower() for keyword in keywords)

try:
    while True:
        print(f"\n{Fore.CYAN}⏳ Scan de la mémoire en cours...{Style.RESET_ALL}")
        matches = scan_memory_for_buy_property()
        
        if matches:
            print(f"{Fore.GREEN}📢 {len(matches)} correspondance(s) trouvée(s):{Style.RESET_ALL}")
            for addr, message_bytes in matches:
                try:
                    # Convertir les octets en texte lisible
                    raw_text = message_bytes.decode('utf-16-le', errors='ignore')
                    # Nettoyer le texte pour l'affichage
                    cleaned_text = ''.join(char for char in raw_text if ord(char) >= 32)
                    
                    # Vérifier si c'est un message d'achat de propriété
                    if is_buy_property_message(cleaned_text):
                        message_key = f"{addr:08X}"
                        
                        if message_key not in already_seen or already_seen[message_key] != cleaned_text:
                            print(f"{Fore.YELLOW}✨ Nouveau message d'achat à 0x{addr:08X}:{Style.RESET_ALL}")
                            print(f"{Fore.GREEN}\"{cleaned_text}\"{Style.RESET_ALL}")
                            already_seen[message_key] = cleaned_text
                except Exception as e:
                    print(f"{Fore.RED}⚠️ Erreur de traitement à 0x{addr:08X}: {e}{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}⚠️ Aucun message d'achat trouvé.{Style.RESET_ALL}")
        
        print(f"{Fore.CYAN}⏲️ Pause de 2 secondes avant le prochain scan...{Style.RESET_ALL}")
        time.sleep(2)
except KeyboardInterrupt:
    print(f"\n{Fore.YELLOW}Arrêt demandé par l'utilisateur.{Style.RESET_ALL}")
except Exception as e:
    print(f"\n{Fore.RED}Erreur: {e}{Style.RESET_ALL}")
    import traceback
    traceback.print_exc()
finally:
    print(f"{Fore.GREEN}Nettoyage et fermeture...{Style.RESET_ALL}") 