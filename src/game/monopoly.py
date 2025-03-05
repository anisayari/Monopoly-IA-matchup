from typing import List, Tuple
import dolphin_memory_engine as dme
import time
from threading import Thread
import re
import json
import threading

from ..core.memory_reader import MemoryReader
from ..core.memory_addresses import MemoryAddresses
from ..models.player import Player
from ..models.property import Property
from ..models.enums import PlayerColor
from ..display.game_display import GameDisplay

class MonopolyGame:
    """Classe principale gérant le jeu Monopoly"""
    def __init__(self):
        """Initialise le jeu Monopoly"""
        # Vérifier la connexion à Dolphin
        if not dme.is_hooked():
            dme.hook()
        if not dme.is_hooked():
            raise Exception("Impossible de se connecter à Dolphin Memory Engine")
            
        # Initialiser l'affichage
        self._display = GameDisplay()
        self._display.print_info("Initialisation du jeu Monopoly...")
        
        # Initialiser le lecteur de mémoire
        self._memory_reader = MemoryReader()
        
        # Dictionnaire pour stocker les adresses mémoire trouvées dynamiquement
        self._dynamic_addresses = {}
        
        # Dictionnaire pour stocker les propriétés déjà identifiées avec leurs adresses
        # Format: {property_key: [addr1, addr2, ...]}
        self._property_addresses = {}
        
        # Ensemble pour stocker les messages déjà vus
        self._seen_messages = set()
        
        # Démarrer la surveillance de la mémoire
        self.start_monitoring()
        
        # Initialiser les joueurs
        self._players = {}
        
        # Initialiser l'état du jeu
        self._game_state = {
            "current_player": None,
            "dice_roll": None,
            "last_property_message": None
        }
        
        # Initialiser l'IA
        self._ai = None
        
        # Initialiser les joueurs
        self.blue_player = Player(PlayerColor.BLUE)
        self.red_player = Player(PlayerColor.RED)
        
        # Charger les propriétés
        self.properties = self._load_properties()
        
        # Thread de surveillance
        self._monitor_thread = None
        self._running = False
        
        # Threads de recherche de texte
        self._text_search_threads = {}
        
        # Démarrer la surveillance
        self.start_monitoring()

    def _load_properties(self) -> List[Property]:
        """Charge les propriétés depuis la mémoire du jeu"""
        start, end = MemoryAddresses.PROPERTY_RANGE
        data = dme.read_bytes(start, end - start)
        lines = str(data)[2:-1].split("\\r\\n")
        cols = [line.split(",") for line in lines]
        
        properties = []
        if len(cols) > 1:  # Vérifie qu'il y a au moins une ligne d'en-tête et une ligne de données
            headers = [col.strip().lower() for col in cols[0]]
            for col in cols[1:]:
                if len(col) == len(headers):  # Vérifie que la ligne a le bon nombre de colonnes
                    prop_data = {headers[i]: col[i].strip() for i in range(len(headers))}
                    properties.append(Property.from_dict(prop_data))
        return properties

    def start_monitoring(self):
        """Démarre la surveillance de la mémoire du jeu"""
        try:
            # Afficher un message de débogage
            print("Démarrage de la surveillance de la mémoire...")
            
            # Configurer les recherches en mémoire
            self._setup_memory_searches()
            
            # Démarrer le thread de surveillance
            self._monitoring_thread = threading.Thread(target=self._monitor_game_state, daemon=True)
            self._monitoring_thread.start()
            
            # Afficher un message de confirmation
            if self._display:
                self._display.print_info("Surveillance du jeu démarrée")
            else:
                print("ERREUR: L'affichage n'est pas initialisé!")
                self._display = GameDisplay()
                self._display.print_info("Affichage initialisé et surveillance du jeu démarrée")
        except Exception as e:
            if self._display:
                self._display.print_info(f"Erreur lors du démarrage de la surveillance: {e}")
            else:
                print(f"ERREUR: {e}")
            
    def stop_monitoring(self):
        """Arrête la surveillance de la mémoire du jeu"""
        self._monitoring_running = False
        if hasattr(self, '_monitoring_thread') and self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=1.0)
            self._display.print_info("Surveillance du jeu arrêtée")
            
        # Arrêter le thread de recherche en mémoire
        self._memory_reader.stop_memory_search_thread()

    def _monitor_game_state(self):
        """Surveille l'état du jeu en continu"""
        self._monitoring_running = True
        previous_buy_message = None
        
        while self._monitoring_running:
            try:
                # Surveillance des messages d'achat de propriété
                buy_message = self.dialog_buy_property
                if buy_message and buy_message != previous_buy_message:
                    self._display.update_buy_property(buy_message)
                    previous_buy_message = buy_message
                    
                # Pause pour éviter de surcharger le CPU
                time.sleep(0.5)
                
            except Exception as e:
                self._display.print_info(f"Erreur lors de la surveillance: {str(e)}")
                time.sleep(1.0)  # Pause plus longue en cas d'erreur
                
    def _monitor_changes(self):
        """Surveille les changements dans le jeu"""
        previous_buy_message = ""
        
        while self._running:
            try:
                # Surveillance des joueurs
                for player, color in [(self.blue_player, 'blue'), (self.red_player, 'red')]:
                    current_state = {
                        'label': player.label,
                        'money': player.money,
                        'position': player.position,
                        'goto': player.goto,
                        'dices': player.dices
                    }
                    self._display.update_player(color, current_state)

                # Surveillance des dialogues
                title, message = self.dialog_roll_dice
                self._display.update_dialog(title, message)

                # Surveillance des enchères
                message, purchaser, name = self.dialog_auction
                self._display.update_auction(message, purchaser, name)
                
                # Surveillance des demandes d'achat
                buy_message = self.dialog_buy_property
                if buy_message and buy_message != previous_buy_message:
                    self._display.update_buy_property(buy_message)
                    previous_buy_message = buy_message

            except Exception as e:
                self._display.print_info(f"Erreur lors de la surveillance: {str(e)}")

            # Pause pour éviter de surcharger le CPU
            time.sleep(0.1)

    @property
    def dialog_roll_dice(self) -> Tuple[str, str]:
        """Récupère le titre et le message du dialogue de lancer de dés"""
        title = MemoryReader.get_string(MemoryAddresses.ADDRESSES["DIALOG_ROLL_DICE_TITLE"][0])
        message = MemoryReader.get_string(MemoryAddresses.ADDRESSES["DIALOG_ROLL_DICE_MESSAGE"][0])
        return title, message
    
    @property
    def dialog_title(self) -> str:
        """Récupère le titre du dialogue actuel"""
        # Utiliser l'adresse du dialogue de lancer de dés comme dialogue par défaut
        addr = MemoryAddresses.ADDRESSES["DIALOG_ROLL_DICE_TITLE"][0]
        
        # Vérifier si nous avons trouvé l'adresse dynamiquement
        if "DIALOG_TITLE" in self._dynamic_addresses:
            addr = self._dynamic_addresses["DIALOG_TITLE"]
            
        return MemoryReader.get_string(addr)
    
    @property
    def dialog_message(self) -> str:
        """Récupère le message du dialogue actuel"""
        # Utiliser l'adresse du dialogue de lancer de dés comme dialogue par défaut
        addr = MemoryAddresses.ADDRESSES["DIALOG_ROLL_DICE_MESSAGE"][0]
        
        # Vérifier si nous avons trouvé l'adresse dynamiquement
        if "DIALOG_MESSAGE" in self._dynamic_addresses:
            addr = self._dynamic_addresses["DIALOG_MESSAGE"]
            
        return MemoryReader.get_string(addr)
    
    @property
    def dialog_auction(self) -> Tuple[str, str, str]:
        """Récupère les informations du dialogue d'enchères"""
        message = MemoryReader.get_string(MemoryAddresses.ADDRESSES["DIALOG_AUCTION_BID_MESSAGE"][0])
        purchaser = MemoryReader.get_string(MemoryAddresses.ADDRESSES["DIALOG_AUCTION_PURCHASER_NAME"][0])
        name = MemoryReader.get_string(MemoryAddresses.ADDRESSES["DIALOG_AUCTION_MESSAGE_NAME"][0])
        return message, purchaser, name

    def _setup_memory_searches(self):
        """Configure les recherches en mémoire pour les messages importants du jeu"""
        # Recherche des messages d'achat de propriété uniquement
        
        # Patterns binaires pour trouver les messages d'achat de propriété
        # Ces patterns sont similaires à ceux utilisés dans test_search_buy_property.py
        self._memory_reader.register_search(
            search_id="buy_property",
            pattern=b'D\x00o\x00 \x00y\x00o\x00u\x00',  # "Do you"
            address_key="dialog_buy_property",
            start_addr=0x90000000,
            end_addr=0x90100000,
            chunk_size=0x10000,
            callback=self._on_buy_property_message,
            is_binary=True
        )
        
        self._memory_reader.register_search(
            search_id="buy_property_2",
            pattern=b'b\x00u\x00y\x00',  # "buy"
            address_key="dialog_buy_property",
            start_addr=0x90000000,
            end_addr=0x90100000,
            chunk_size=0x10000,
            callback=self._on_buy_property_message,
            is_binary=True
        )
        
        self._memory_reader.register_search(
            search_id="buy_property_3",
            pattern=b'p\x00r\x00o\x00p\x00e\x00r\x00t\x00y\x00',  # "property"
            address_key="dialog_buy_property",
            start_addr=0x90000000,
            end_addr=0x90100000,
            chunk_size=0x10000,
            callback=self._on_buy_property_message,
            is_binary=True
        )
        
        self._memory_reader.register_search(
            search_id="buy_property_4",
            pattern=b'p\x00u\x00r\x00c\x00h\x00a\x00s\x00e\x00',  # "purchase"
            address_key="dialog_buy_property",
            start_addr=0x90000000,
            end_addr=0x90100000,
            chunk_size=0x10000,
            callback=self._on_buy_property_message,
            is_binary=True
        )
        
        self._memory_reader.register_search(
            search_id="buy_property_5",
            pattern=b'W\x00o\x00u\x00l\x00d\x00 \x00y\x00o\x00u\x00',  # "Would you"
            address_key="dialog_buy_property",
            start_addr=0x90000000,
            end_addr=0x90100000,
            chunk_size=0x10000,
            callback=self._on_buy_property_message,
            is_binary=True
        )
        
        # Pattern pour capturer les prix
        self._memory_reader.register_search(
            search_id="buy_property_price",
            pattern=b'f\x00o\x00r\x00 \x00\$\x00',  # "for $"
            address_key="dialog_buy_property",
            start_addr=0x90000000,
            end_addr=0x90100000,
            chunk_size=0x10000,
            callback=self._on_buy_property_message,
            is_binary=True
        )
        
        # Démarrer le thread de recherche en mémoire
        self._memory_reader.start_memory_search_thread(interval=2.0)
        print("Recherches en mémoire configurées.")
        
    def _on_buy_property_message(self, addr, message):
        """Callback appelé quand un message d'achat de propriété est trouvé"""
        # Mettre à jour l'adresse dynamique
        self._memory_reader.update_dynamic_address("dialog_buy_property", addr)
        
        # Nettoyer le message pour supprimer les caractères binaires
        cleaned_message = ""
        for char in message:
            if (32 <= ord(char) <= 126) or ('À' <= char <= 'ÿ') or char in ['€', '£', '¥', '©', '®', '™', '°', '±', '²', '³', '¼', '½', '¾']:
                cleaned_message += char
            else:
                # Arrêter au premier caractère non imprimable pour éviter d'afficher des données binaires
                break
        
        # Vérifier si le message contient des mots-clés d'achat
        keywords = ["buy", "purchase", "property", "would you like", "do you want"]
        if any(keyword in cleaned_message.lower() for keyword in keywords):
            # Extraire le nom de la propriété et le prix si possible
            property_name = None
            property_price = None
            
            # Recherche du nom et du prix de la propriété
            # Format typique: "buy Marylebone Station for $200?"
            property_match = re.search(r"buy\s+([A-Za-z\s]+(?:Station|Avenue|Road|Street|Lane|Place|Gardens|Square|Park|Boardwalk|Walk))\s+for\s+\$?(\d+|\~\d+)", cleaned_message, re.IGNORECASE)
            
            if not property_match:
                # Essayer un autre pattern pour "Do you want to buy X for Y"
                property_match = re.search(r"want to buy\s+([A-Za-z\s]+(?:Station|Avenue|Road|Street|Lane|Place|Gardens|Square|Park|Boardwalk|Walk))\s+for\s+\$?(\d+|\~\d+)", cleaned_message, re.IGNORECASE)
            
            if property_match:
                property_name = property_match.group(1).strip()
                property_price = property_match.group(2).strip()
                
                # Créer une clé unique pour cette propriété
                property_key = f"{property_name}:{property_price}"
                
                # Vérifier si cette adresse a déjà été enregistrée pour cette propriété
                if property_key not in self._property_addresses:
                    self._property_addresses[property_key] = []
                
                # Si cette adresse n'est pas déjà enregistrée pour cette propriété
                if addr not in self._property_addresses[property_key]:
                    self._property_addresses[property_key].append(addr)
                    # Toujours mettre à jour l'affichage, même si l'adresse est déjà connue
                    if self._display:
                        self._display.update_buy_property(cleaned_message)
                else:
                    # Message déjà connu, ne pas mettre à jour l'affichage pour éviter les doublons
                    pass
            else:
                # Si aucune propriété n'est identifiée, vérifier si ce message a déjà été vu
                message_key = f"{addr:08X}:{cleaned_message[:30]}"
                if message_key not in self._seen_messages:
                    self._seen_messages.add(message_key)
                    # Mettre à jour l'affichage avec le message nettoyé
                    if self._display:
                        self._display.update_buy_property(cleaned_message)
                else:
                    # Message déjà vu, ne pas mettre à jour l'affichage
                    pass
        
    @property
    def dialog_buy_property(self):
        """Récupère le message d'achat de propriété actuel"""
        # Récupérer l'adresse dynamique principale
        addr = self._memory_reader.get_dynamic_address("dialog_buy_property")
        
        if addr:
            # Lire la chaîne à cette adresse
            message = self._memory_reader.get_string(addr)
            
            # Vérifier si le message contient des mots-clés d'achat
            keywords = ["buy", "purchase", "property", "would you like", "do you want"]
            if message and any(keyword in message.lower() for keyword in keywords):
                return message
        
        # Si aucun message n'est trouvé à l'adresse dynamique principale,
        # vérifier toutes les adresses connues pour les propriétés
        for property_key, addresses in self._property_addresses.items():
            for addr in addresses:
                message = self._memory_reader.get_string(addr)
                if message and any(keyword in message.lower() for keyword in ["buy", "purchase", "property", "would you like", "do you want"]):
                    # Mettre à jour l'adresse dynamique principale
                    self._memory_reader.update_dynamic_address("dialog_buy_property", addr)
                    return message
        
        return None
        
    def start_custom_memory_search(self, pattern, callback, search_id, is_binary=False):
        """
        Démarre une recherche personnalisée en mémoire
        
        Args:
            pattern: Motif de recherche (regex ou binaire)
            callback: Fonction à appeler lorsqu'un résultat est trouvé
            search_id: Identifiant unique pour cette recherche
            is_binary: True si le pattern est binaire, False sinon
        """
        try:
            # Utiliser le memory_reader pour enregistrer la recherche
            self._memory_reader.register_search(
                search_id=search_id,
                pattern=pattern,
                address_key=search_id,
                start_addr=0x90000000,
                end_addr=0x90100000,
                chunk_size=0x10000,
                callback=callback,
                is_binary=is_binary
            )
            
            # Démarrer le thread de recherche s'il n'est pas déjà en cours
            self._memory_reader.start_memory_search_thread(interval=2.0)
            
            print(f"Recherche '{search_id}' enregistrée")
        except Exception as e:
            print(f"Erreur lors de l'enregistrement de la recherche '{search_id}': {str(e)}")
        
    def __del__(self):
        """Nettoyage lors de la destruction de l'objet"""
        try:
            # Arrêter le thread de surveillance
            if hasattr(self, '_running') and self._running:
                self.stop_monitoring()
            
            # Arrêter le thread de recherche de texte
            if hasattr(MemoryReader, '_search_running') and MemoryReader._search_running:
                MemoryReader.stop_memory_search_thread()
                
            # Afficher un message de fermeture
            if hasattr(self, '_display'):
                self._display.print_info("Fermeture propre du jeu")
        except Exception as e:
            # En cas d'erreur, ne rien faire (on est déjà en train de fermer)
            pass 