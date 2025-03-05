import dolphin_memory_engine as dme
import re
import time

print("🔌 Tentative de connexion à Dolphin...")
dme.hook()
print("✅ Connecté à Dolphin avec succès.")

# Plage mémoire plus large pour couvrir les différents emplacements possibles
RAM_START = 0x90000000
RAM_SIZE = 0x00100000  # 1 Mo - suffisamment grand sans être excessif

# Pattern simplifié pour trouver les messages de dialogue
pattern = re.compile(b'D\x00o\x00 \x00y\x00o\x00u\x00', re.DOTALL)

already_seen = set()
print("🔍 Début de la surveillance de la mémoire...")

def scan_memory_chunks():
    # Scan la mémoire par morceaux pour éviter de lire de trop gros blocs en une fois
    CHUNK_SIZE = 0x10000  # 64 Ko par chunk
    results = []
    
    for addr in range(RAM_START, RAM_START + RAM_SIZE, CHUNK_SIZE):
        try:
            chunk = dme.read_bytes(addr, CHUNK_SIZE)
            matches = pattern.finditer(chunk)
            
            for match in matches:
                start_pos = match.start()
                # Lire jusqu'à 200 octets après le match pour capturer le message complet
                message_bytes = chunk[start_pos:min(start_pos+200, len(chunk))]
                
                # Calculer l'adresse absolue du match pour l'affichage
                match_addr = addr + start_pos
                
                results.append((match_addr, message_bytes))
        except Exception as e:
            print(f"⚠️ Erreur lors de la lecture à l'adresse 0x{addr:08X}: {e}")
    
    return results

while True:
    print("\n⏳ Scan de la mémoire en cours...")
    matches = scan_memory_chunks()
    
    if matches:
        print(f"📢 {len(matches)} correspondance(s) trouvée(s):")
        for addr, message_bytes in matches:
            try:
                # Convertir les octets en texte lisible
                raw_text = message_bytes.decode('utf-16-le', errors='ignore')
                # Nettoyer le texte pour l'affichage
                cleaned_text = ''.join(char for char in raw_text if ord(char) >= 32 and ord(char) < 127)
                
                message_key = f"{addr:08X}:{cleaned_text[:30]}"  # Utiliser l'adresse + début du texte comme clé
                
                if message_key not in already_seen:
                    print(f"✨ Nouveau à 0x{addr:08X}: \"{cleaned_text}\"")
                    already_seen.add(message_key)
                else:
                    print(f"♻️ Déjà vu à 0x{addr:08X}: \"{cleaned_text}\"")
            except Exception as e:
                print(f"⚠️ Erreur de traitement à 0x{addr:08X}: {e}")
    else:
        print("⚠️ Aucune correspondance trouvée.")
    
    print("⏲️ Pause de 2 secondes avant le prochain scan...")
    time.sleep(2)