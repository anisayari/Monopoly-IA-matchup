import dolphin_memory_engine as dme
import re
import time
import threading
from typing import List, Tuple, Dict, Set, Callable, Optional

class MemoryReader:
    """Classe utilitaire pour lire/écrire dans la mémoire"""
    
    # Dictionnaire pour stocker les résultats des recherches mémoire
    _memory_search_results = {}
    # Dictionnaire pour stocker les callbacks de notification
    _memory_search_callbacks = {}
    # Ensemble pour stocker les messages déjà vus
    _already_seen_messages = set()
    # Flag pour contrôler le thread de recherche
    _search_running = False
    # Thread de recherche actif
    _search_thread = None
    # Liste des recherches à effectuer
    _search_patterns = {}
    # Intervalle entre les recherches
    _search_interval = 2.0
    
    # Dictionnaires pour stocker les adresses et les résultats de recherche
    _static_addresses = {}
    _dynamic_addresses = {}
    
    @staticmethod
    def get_string(addr: int) -> str:
        """Lit une chaîne de caractères à partir d'une adresse mémoire"""
        string = ""
        valid_chars_found = False
        consecutive_invalid_chars = 0
        max_consecutive_invalid = 3  # Arrêter après 3 caractères invalides consécutifs
        
        try:
            while True:
                char = dme.read_bytes(addr, 2)
                if char == b"\x00\x00":
                    break
                try:
                    # Utiliser utf-16-le pour être cohérent avec le reste du code
                    decoded_char = char.decode("utf-16-le", errors="ignore")
                    
                    # Filtrer les caractères non imprimables ou étranges
                    if decoded_char and (
                        (32 <= ord(decoded_char) <= 126) or  # ASCII imprimable
                        ('À' <= decoded_char <= 'ÿ') or      # Lettres accentuées
                        decoded_char in ['€', '£', '¥', '©', '®', '™', '°', '±', '²', '³', '¼', '½', '¾']  # Symboles courants
                    ):
                        string += decoded_char
                        valid_chars_found = True
                        consecutive_invalid_chars = 0  # Réinitialiser le compteur
                    else:
                        # Si on a déjà trouvé des caractères valides et qu'on rencontre des caractères invalides
                        # consécutifs, on arrête la lecture
                        if valid_chars_found:
                            consecutive_invalid_chars += 1
                            if consecutive_invalid_chars >= max_consecutive_invalid:
                                break
                        # Sinon, on remplace par un point d'interrogation
                        string += "?"
                except:
                    # Si on a déjà trouvé des caractères valides et qu'on rencontre une erreur
                    if valid_chars_found:
                        consecutive_invalid_chars += 1
                        if consecutive_invalid_chars >= max_consecutive_invalid:
                            break
                    string += "?"
                addr += 2
                
            # Si la chaîne contient trop de points d'interrogation, elle est probablement invalide
            if string and string.count("?") / len(string) > 0.3:  # Plus de 30% de caractères invalides
                return ""
                
            return string
        except Exception as e:
            print(f"Erreur lors de la lecture de la chaîne à 0x{addr:08X}: {e}")
            return ""

    @staticmethod
    def set_string(addr: int, text: str) -> None:
        """Écrit une chaîne de caractères à une adresse mémoire"""
        for i in range(len(text)):
            dme.write_bytes(addr + i * 2, text[i].encode("utf-8") + b"\x00")
        dme.write_bytes(addr + len(text) * 2, b"\x00")

    @staticmethod
    def get_short(addr: int) -> int:
        """Lit un entier court (2 octets) à partir d'une adresse mémoire"""
        return int.from_bytes(dme.read_bytes(addr, 2), byteorder="big")

    @staticmethod
    def set_short(addr: int, value: int) -> None:
        """Écrit un entier court (2 octets) à une adresse mémoire"""
        dme.write_bytes(addr, value.to_bytes(2, byteorder="big"))

    @staticmethod
    def get_byte(addr: int) -> int:
        """Lit un octet à partir d'une adresse mémoire"""
        return int.from_bytes(dme.read_bytes(addr, 1), byteorder="big")

    @staticmethod
    def set_byte(addr: int, value: int) -> None:
        """Écrit un octet à une adresse mémoire"""
        dme.write_bytes(addr, value.to_bytes(1, byteorder="big"))
        
    @classmethod
    def search_text_in_memory(cls, 
                              search_pattern: str, 
                              start_addr: int = 0x80000000, 
                              end_addr: int = 0x94000000, 
                              chunk_size: int = 0x10000, 
                              encoding: str = 'utf-16-le',
                              callback: Optional[Callable[[int, str], None]] = None,
                              search_id: str = 'default',
                              is_binary_pattern: bool = False) -> List[Tuple[int, str]]:
        """
        Recherche un pattern dans la mémoire et retourne les correspondances
        
        Args:
            search_pattern: Expression régulière ou pattern binaire à rechercher
            start_addr: Adresse de début de recherche
            end_addr: Adresse de fin de recherche
            chunk_size: Taille des morceaux de mémoire à lire
            encoding: Encodage à utiliser pour décoder les chaînes
            callback: Fonction à appeler pour chaque correspondance
            search_id: Identifiant de la recherche
            is_binary_pattern: True si le pattern est binaire, False sinon
            
        Returns:
            Liste de tuples (adresse, texte) pour chaque correspondance
        """
        results = []
        
        # Compiler le pattern si c'est une chaîne
        if isinstance(search_pattern, str) and not is_binary_pattern:
            pattern = re.compile(search_pattern, re.IGNORECASE | re.DOTALL)
        elif is_binary_pattern and isinstance(search_pattern, bytes):
            pattern = re.compile(search_pattern, re.DOTALL)
        elif is_binary_pattern and isinstance(search_pattern, str):
            # Convertir la chaîne en bytes pour la recherche binaire
            pattern_bytes = search_pattern.encode(encoding)
            pattern = re.compile(pattern_bytes, re.DOTALL)
        else:
            # Utiliser directement le pattern compilé
            pattern = search_pattern
        
        # Parcourir la mémoire par morceaux
        for addr in range(start_addr, end_addr, chunk_size):
            try:
                # Lire un morceau de mémoire
                chunk = dme.read_bytes(addr, chunk_size)
                
                # Si c'est une recherche binaire, chercher directement dans les octets
                if is_binary_pattern:
                    matches = pattern.finditer(chunk)
                    for match in matches:
                        start_pos = match.start()
                        # Lire jusqu'à 200 octets après le match pour capturer le message complet
                        message_bytes = chunk[start_pos:min(start_pos+200, len(chunk))]
                        match_addr = addr + start_pos
                        
                        # Décoder les octets en texte
                        try:
                            message = message_bytes.decode(encoding, errors='ignore')
                            # Nettoyer le texte
                            message = ''.join(char for char in message if ord(char) >= 32)
                        except:
                            message = "Erreur de décodage"
                        
                        # Ajouter aux résultats
                        results.append((match_addr, message))
                        
                        # Appeler le callback si fourni
                        if callback:
                            try:
                                callback(match_addr, message)
                            except Exception as e:
                                print(f"Erreur dans le callback: {e}")
                else:
                    # Pour les recherches textuelles, décoder d'abord le morceau
                    try:
                        text = chunk.decode(encoding, errors='ignore')
                        matches = pattern.finditer(text)
                        
                        for match in matches:
                            start_pos = match.start()
                            match_addr = addr + start_pos * 2  # *2 car utf-16 utilise 2 octets par caractère
                            
                            # Extraire le message complet
                            message = text[start_pos:min(start_pos+100, len(text))]
                            
                            # Ajouter aux résultats
                            results.append((match_addr, message))
                            
                            # Appeler le callback si fourni
                            if callback:
                                try:
                                    callback(match_addr, message)
                                except Exception as e:
                                    print(f"Erreur dans le callback: {e}")
                    except Exception as e:
                        print(f"Erreur lors du décodage du texte: {e}")
            except Exception as e:
                print(f"Erreur lors de la lecture à l'adresse 0x{addr:08X}: {e}")
        
        # Stocker les résultats pour cette recherche
        cls._memory_search_results[search_id] = set((addr, text) for addr, text in results)
        
        return results
    
    @classmethod
    def add_search_pattern(cls, 
                          search_pattern: str, 
                          callback: Callable[[int, str], None],
                          search_id: str = 'default',
                          is_binary_pattern: bool = False):
        """
        Ajoute un motif de recherche à la liste des recherches à effectuer
        
        Args:
            search_pattern: Expression régulière à rechercher
            callback: Fonction à appeler quand un nouveau texte est trouvé
            search_id: Identifiant unique pour cette recherche
            is_binary_pattern: Si True, search_pattern est déjà un pattern binaire compilé
        """
        cls._search_patterns[search_id] = {
            'pattern': search_pattern,
            'callback': callback,
            'is_binary_pattern': is_binary_pattern
        }
        
        # Initialiser le dictionnaire des résultats pour cette recherche
        if search_id not in cls._memory_search_results:
            cls._memory_search_results[search_id] = set()
            
        # Enregistrer le callback
        cls._memory_search_callbacks[search_id] = callback
    
    @classmethod
    def remove_search_pattern(cls, search_id: str):
        """
        Supprime un motif de recherche de la liste
        
        Args:
            search_id: Identifiant de la recherche à supprimer
        """
        if search_id in cls._search_patterns:
            del cls._search_patterns[search_id]
        
        if search_id in cls._memory_search_callbacks:
            del cls._memory_search_callbacks[search_id]
    
    @classmethod
    def start_memory_search_thread(cls, interval: float = 2.0):
        """
        Démarre un thread unique qui recherche périodiquement tous les motifs enregistrés
        
        Args:
            interval: Intervalle entre les cycles de recherche (en secondes)
        """
        if cls._search_thread and cls._search_thread.is_alive():
            # Le thread est déjà en cours d'exécution
            cls._search_interval = interval
            return cls._search_thread
        
        cls._search_running = True
        cls._search_interval = interval
        
        def search_thread_function():
            print(f"Thread de recherche mémoire démarré (intervalle: {cls._search_interval}s)")
            while cls._search_running:
                try:
                    # Créer une copie du dictionnaire pour éviter l'erreur "dictionary changed size during iteration"
                    search_patterns_copy = dict(cls._search_patterns)
                    
                    # Effectuer toutes les recherches enregistrées
                    for search_id, search_info in search_patterns_copy.items():
                        try:
                            cls.search_text_in_memory(
                                search_pattern=search_info['pattern'],
                                callback=search_info['callback'],
                                search_id=search_id,
                                is_binary_pattern=search_info.get('is_binary_pattern', False)
                            )
                        except Exception as e:
                            print(f"Erreur lors de la recherche '{search_id}': {e}")
                    
                    # Attendre avant le prochain cycle
                    time.sleep(cls._search_interval)
                except Exception as e:
                    print(f"Erreur dans le thread de recherche: {e}")
                    # Attendre un peu avant de réessayer
                    time.sleep(1.0)
        
        cls._search_thread = threading.Thread(target=search_thread_function, daemon=True)
        cls._search_thread.start()
        return cls._search_thread
    
    @classmethod
    def stop_memory_search_thread(cls):
        """Arrête le thread de recherche en mémoire"""
        cls._search_running = False
        if cls._search_thread and cls._search_thread.is_alive():
            cls._search_thread.join(timeout=1.0)
            cls._search_thread = None
        
    @classmethod
    def clear_memory_search_results(cls, search_id: str = None):
        """
        Efface les résultats de recherche en mémoire
        
        Args:
            search_id: Identifiant de la recherche à effacer, ou None pour tout effacer
        """
        if search_id:
            if search_id in cls._memory_search_results:
                cls._memory_search_results[search_id].clear()
        else:
            cls._memory_search_results.clear()
    
    @classmethod
    def register_search(cls, 
                       search_id: str, 
                       pattern: str, 
                       address_key: str = None,
                       start_addr: int = 0x90000000, 
                       end_addr: int = 0x90100000, 
                       chunk_size: int = 0x10000,
                       callback: Optional[Callable[[int, str], None]] = None,
                       is_binary: bool = False):
        """
        Enregistre une recherche en mémoire
        
        Args:
            search_id: Identifiant unique pour cette recherche
            pattern: Expression régulière à rechercher
            address_key: Clé pour stocker l'adresse trouvée (optionnel)
            start_addr: Adresse de début de recherche
            end_addr: Adresse de fin de recherche
            chunk_size: Taille des morceaux de mémoire à lire
            callback: Fonction à appeler quand un nouveau texte est trouvé
            is_binary: True si le pattern est binaire, False sinon
        """
        # Créer une fonction de callback qui met à jour l'adresse dynamique
        def internal_callback(addr, text):
            # Si une clé d'adresse est fournie, mettre à jour l'adresse dynamique
            if address_key:
                cls.update_dynamic_address(address_key, addr)
            
            # Appeler le callback externe si fourni
            if callback:
                try:
                    callback(addr, text)
                except Exception as e:
                    print(f"Erreur dans le callback pour '{search_id}': {e}")
        
        # Enregistrer le pattern de recherche
        cls._search_patterns[search_id] = {
            "pattern": pattern,
            "start_addr": start_addr,
            "end_addr": end_addr,
            "chunk_size": chunk_size,
            "callback": internal_callback,
            "is_binary_pattern": is_binary
        }
        
        # Initialiser le dictionnaire des résultats pour cette recherche
        if search_id not in cls._memory_search_results:
            cls._memory_search_results[search_id] = set()
        
        print(f"Recherche '{search_id}' enregistrée")
    
    @classmethod
    def update_dynamic_address(cls, key: str, addr: int):
        """
        Met à jour une adresse dynamique
        
        Args:
            key: Clé de l'adresse à mettre à jour
            addr: Nouvelle adresse
        """
        cls._dynamic_addresses[key] = addr
    
    @classmethod
    def get_dynamic_address(cls, key: str, default: int = None) -> Optional[int]:
        """
        Récupère une adresse dynamique
        
        Args:
            key: Clé de l'adresse à récupérer
            default: Valeur par défaut si l'adresse n'est pas trouvée
            
        Returns:
            L'adresse ou la valeur par défaut
        """
        return cls._dynamic_addresses.get(key, default)
    
    @classmethod
    def get_static_address(cls, key: str, default: int = None) -> Optional[int]:
        """
        Récupère une adresse statique
        
        Args:
            key: Clé de l'adresse à récupérer
            default: Valeur par défaut si l'adresse n'est pas trouvée
            
        Returns:
            L'adresse ou la valeur par défaut
        """
        return cls._static_addresses.get(key, default)
    
    @classmethod
    def start_memory_search_thread(cls, interval: float = 2.0):
        """
        Démarre un thread pour rechercher périodiquement les patterns en mémoire
        
        Args:
            interval: Intervalle entre les recherches en secondes
        """
        if cls._search_thread and cls._search_thread.is_alive():
            print("Le thread de recherche en mémoire est déjà en cours d'exécution")
            return
        
        def search_thread():
            cls._search_running = True
            print(f"Thread de recherche en mémoire démarré (intervalle: {interval}s)")
            
            while cls._search_running:
                try:
                    # Créer une copie du dictionnaire pour éviter les erreurs de modification pendant l'itération
                    search_patterns_copy = cls._search_patterns.copy()
                    
                    for search_id, search_info in search_patterns_copy.items():
                        try:
                            # Effectuer la recherche
                            results = cls.search_text_in_memory(
                                search_pattern=search_info["pattern"],
                                start_addr=search_info["start_addr"],
                                end_addr=search_info["end_addr"],
                                chunk_size=search_info["chunk_size"],
                                callback=search_info["callback"],
                                search_id=search_id,
                                is_binary_pattern=search_info["is_binary_pattern"]
                            )
                        except Exception as e:
                            print(f"Erreur lors de la recherche '{search_id}': {e}")
                    
                    # Attendre l'intervalle spécifié
                    time.sleep(interval)
                except Exception as e:
                    print(f"Erreur dans le thread de recherche en mémoire: {e}")
                    time.sleep(1)  # Attendre un peu en cas d'erreur
        
        # Démarrer le thread
        cls._search_thread = threading.Thread(target=search_thread, daemon=True)
        cls._search_thread.start()
    
    @classmethod
    def stop_memory_search_thread(cls):
        """Arrête le thread de recherche en mémoire"""
        cls._search_running = False
        if cls._search_thread and cls._search_thread.is_alive():
            cls._search_thread.join(timeout=1.0)
            print("Thread de recherche en mémoire arrêté")
        
    @classmethod
    def clear_search_patterns(cls):
        """Efface tous les patterns de recherche enregistrés"""
        cls._search_patterns.clear()
        cls._memory_search_results.clear()
        cls._memory_search_callbacks.clear()
        print("Patterns de recherche effacés") 