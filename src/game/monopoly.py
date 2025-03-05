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
        
        # État du jeu pour suivre les changements
        self._game_state = {
            'current_player': '',
            'end_of_turn': False,
            'end_of_turn_displayed': False,
            'last_property_offer': ('', 0)
        }
        
        # Variables pour éviter les répétitions dans les callbacks
        self._last_end_turn_addr = 0
        self._last_buy_property_message = ""
        self._last_chance_card_message = ""
        self._last_community_card_message = ""
        self._last_win_message = ""
        
        # Thread pour réinitialiser les callbacks
        self._reset_callbacks_thread = None
        
        # Démarrer la surveillance de la mémoire
        self.start_monitoring()
        
        # Initialiser les joueurs
        self._players = {}
        
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
        
        # Initialiser l'opportunité actuelle
        self._current_property_opportunity = (None, None, None)  # (player_name, property_name, property_price)

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
            self._monitoring_thread = threading.Thread(target=self._monitor_game, daemon=True)
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

    def _monitor_game(self):
        """Surveille l'état du jeu en continu"""
        self._monitoring_running = True
        previous_buy_message = None
        
        while self._monitoring_running:
            try:
                # Surveillance des messages d'achat de propriété
                buy_message = self.dialog_buy_property
                if buy_message and buy_message != previous_buy_message:
                    # Utiliser la méthode update_buy_property qui maintenant appelle display_property_purchase_opportunity
                    # quand elle extrait correctement les informations
                    self._display.update_buy_property(buy_message)
                    previous_buy_message = buy_message
                    
                # Pause pour éviter de surcharger le CPU
                time.sleep(0.5)
                
            except Exception as e:
                self._display.print_info(f"Erreur lors de la surveillance: {str(e)}")
                time.sleep(1.0)  # Pause plus longue en cas d'erreur
                
    def _monitor_changes(self):
        """Surveille les changements dans le jeu"""
        previous_buy_message = None
        
        while self._monitoring_running:
            try:
                # Surveillance des joueurs
                for color, player in self.players.items():
                    current_state = {
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
                    # Utiliser la méthode update_buy_property qui maintenant appelle display_property_purchase_opportunity
                    # quand elle extrait correctement les informations
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
    
    @property
    def dialog_buy_property(self) -> str:
        """Récupère le message d'achat de propriété actuel"""
        # Vérifier si nous avons trouvé l'adresse dynamiquement
        addr = self._memory_reader.get_dynamic_address("dialog_buy_property")
        
        if addr:
            # Lire la chaîne à cette adresse
            message = self._memory_reader.get_string(addr)
            
            # Vérifier si le message contient des mots-clés d'achat
            keywords = ["buy", "purchase", "property", "would you like", "do you want"]
            if message and any(keyword in message.lower() for keyword in keywords):
                return message
        
        return None

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
        """Callback pour les messages d'achat de propriété"""
        # Nettoyer le message pour enlever les caractères non imprimables
        cleaned_message = re.sub(r'[^\x20-\x7E]', '', message)
        
        # Vérifier si le message contient des mots-clés liés à l'achat
        buy_keywords = ['buy', 'purchase', 'acheter', 'acquérir']
        if not any(keyword in cleaned_message.lower() for keyword in buy_keywords):
            return
        
        # Initialiser les variables
        property_name = None
        property_price = None
        
        # Extraire le nom de la propriété et le prix avec regex
        # Essayer différents patterns pour capturer les formats possibles
        patterns = [
            # "Would you like to buy X for Y"
            r"like to buy\s+([A-Za-z\s]+(?:Station|Avenue|Road|Street|Lane|Place|Gardens|Square|Park|Boardwalk|Walk))\s+for\s+\$?(\d+|\~\d+)",
            # "Do you want to buy X for Y"
            r"want to buy\s+([A-Za-z\s]+(?:Station|Avenue|Road|Street|Lane|Place|Gardens|Square|Park|Boardwalk|Walk))\s+for\s+\$?(\d+|\~\d+)",
            # "buy X for ~Y?"
            r"buy\s+([A-Za-z\s]+(?:Station|Avenue|Road|Street|Lane|Place|Gardens|Square|Park|Boardwalk|Walk))\s+for\s+\$?(\d+|\~\d+)\??",
            # Generic pattern for any property name followed by a price
            r"buy\s+([A-Za-z\s]+)\s+for\s+\$?(\d+|\~\d+)\??"
        ]
        
        for pattern in patterns:
            property_match = re.search(pattern, cleaned_message, re.IGNORECASE)
            if property_match:
                property_name = property_match.group(1).strip()
                property_price = property_match.group(2).strip()
                break
        
        # Obtenir le nom du joueur actuel
        player_name = self._game_state.get('current_player', 'Joueur')
        
        # Si nous avons toutes les informations, appeler directement display_property_purchase_opportunity
        if property_name and property_price:
            # Vérifier si c'est la même opportunité que la dernière fois
            current_opportunity = (player_name, property_name, property_price)
            if current_opportunity == self._current_property_opportunity:
                return True
                
            # Mettre à jour l'opportunité actuelle
            self._current_property_opportunity = current_opportunity
            self._display.display_property_purchase_opportunity(player_name, property_name, property_price)
            return True
        
        # Sinon, utiliser la méthode générique update_buy_property
        # qui tentera d'extraire les informations elle-même
        # et appellera display_property_purchase_opportunity si possible
        self._display.update_buy_property(cleaned_message)
        return True
        
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

    def setup_custom_memory_searches(self):
        """Configure des recherches de texte en mémoire personnalisées"""
        try:
            self._display.print_info("Configuration de recherches de texte personnalisées...")
            
            # Patterns binaires pour les recherches personnalisées
            chance_pattern = re.compile(b'C\x00h\x00a\x00n\x00c\x00e\x00', re.DOTALL)
            community_pattern = re.compile(b'C\x00o\x00m\x00m\x00u\x00n\x00i\x00t\x00y\x00', re.DOTALL)
            win_pattern = re.compile(b'W\x00i\x00n\x00n\x00e\x00r\x00', re.DOTALL)
            
            # Pattern pour détecter "What would you like to do?" (fin de tour)
            end_turn_pattern = re.compile(b'W\x00h\x00a\x00t\x00 \x00w\x00o\x00u\x00l\x00d\x00', re.DOTALL)
            
            # Pattern pour détecter les messages d'achat de propriété
            buy_property_pattern = re.compile(b'b\x00u\x00y\x00', re.DOTALL)
            
            # Démarrer les recherches personnalisées
            self.start_custom_memory_search(
                pattern=chance_pattern,
                callback=self._chance_card_callback,
                search_id="custom_chance_card",
                is_binary=True
            )
            
            self.start_custom_memory_search(
                pattern=community_pattern,
                callback=self._community_card_callback,
                search_id="custom_community_card",
                is_binary=True
            )
            
            self.start_custom_memory_search(
                pattern=win_pattern,
                callback=self._win_callback,
                search_id="custom_win_state",
                is_binary=True
            )
            
            # Démarrer la recherche pour détecter la fin d'un tour
            self.start_custom_memory_search(
                pattern=end_turn_pattern,
                callback=self._end_turn_callback,
                search_id="custom_end_turn",
                is_binary=True
            )
            
            # Démarrer la recherche pour détecter les messages d'achat de propriété
            self.start_custom_memory_search(
                pattern=buy_property_pattern,
                callback=self._buy_property_callback,
                search_id="custom_buy_property",
                is_binary=True
            )
            
            # Démarrer un thread pour réinitialiser périodiquement les callbacks
            self._reset_callbacks_thread = threading.Thread(target=self._reset_callbacks_periodically, daemon=True)
            self._reset_callbacks_thread.start()
            
            self._display.print_info("Recherches personnalisées configurées.")
        except Exception as e:
            self._display.print_error(f"Erreur lors de la configuration des recherches personnalisées: {str(e)}")

    def _reset_callbacks_periodically(self):
        """Réinitialise périodiquement les callbacks désactivés"""
        while True:
            try:
                # Attendre 30 secondes avant de réinitialiser
                time.sleep(30)
                
                # Réinitialiser les callbacks
                self._reset_callbacks()
            except Exception as e:
                print(f"Erreur lors de la réinitialisation des callbacks: {str(e)}")
                time.sleep(5)  # Attendre un peu en cas d'erreur
    
    def _reset_callbacks(self):
        """Réinitialise les callbacks désactivés"""
        try:
            # Réinitialiser les callbacks pour les recherches personnalisées
            search_ids = [
                "custom_chance_card",
                "custom_community_card",
                "custom_win_state",
                "custom_end_turn",
                "custom_buy_property"
            ]
            
            callbacks = {
                "custom_chance_card": self._chance_card_callback,
                "custom_community_card": self._community_card_callback,
                "custom_win_state": self._win_callback,
                "custom_end_turn": self._end_turn_callback,
                "custom_buy_property": self._buy_property_callback
            }
            
            for search_id in search_ids:
                if search_id in self._memory_reader._search_patterns:
                    pattern_info = self._memory_reader._search_patterns[search_id]
                    if pattern_info['callback'] is None:
                        print(f"Réactivation du callback pour '{search_id}'")
                        pattern_info['callback'] = callbacks[search_id]
                        self._memory_reader._search_patterns[search_id] = pattern_info
            
            # Réinitialiser les variables de suivi pour éviter les problèmes de répétition
            # Nous ne réinitialisons pas complètement pour éviter de répéter les messages,
            # mais nous les vidons périodiquement pour éviter les problèmes de mémoire
            if time.time() % 60 < 1:  # Environ une fois par minute
                print("Réinitialisation des variables de suivi des cartes")
                self._last_chance_card_message = ""
                self._last_community_card_message = ""
                self._last_win_message = ""
                
                # Limiter la taille de l'ensemble _seen_messages pour éviter qu'il ne devienne trop grand
                if len(self._seen_messages) > 100:
                    print(f"Nettoyage de l'ensemble _seen_messages ({len(self._seen_messages)} éléments)")
                    self._seen_messages.clear()
        except Exception as e:
            print(f"Erreur lors de la réinitialisation des callbacks: {str(e)}")

    def _chance_card_callback(self, addr, text):
        """Callback pour les cartes chance"""
        if text:
            # Chercher le texte réel de la carte après "Chance"
            if "Chance" in text:
                # Extraire le texte après "Chance"
                card_text = text.split("Chance", 1)[1].strip()
                # Nettoyer le texte
                card_text = self._clean_card_text(card_text)
                
                # Vérifier si le texte est significatif (au moins 5 caractères)
                if len(card_text) < 5:
                    return
                
                # Éviter les répétitions
                if card_text == self._last_chance_card_message:
                    return
                self._last_chance_card_message = card_text
                
                # Marquer ce texte comme une carte chance pour éviter qu'il soit traité comme un achat de propriété
                self._seen_messages.add(card_text)
                
                # Afficher le texte de la carte
                self._display.print_info(f"Carte Chance: {card_text}")
    
    def _community_card_callback(self, addr, text):
        """Callback pour les cartes communauté"""
        if text:
            # Chercher le texte réel de la carte après "Community" ou "Chest"
            if "Community" in text or "Chest" in text:
                # Extraire le texte après "Community" ou "Chest"
                if "Community" in text:
                    card_text = text.split("Community", 1)[1].strip()
                else:
                    card_text = text.split("Chest", 1)[1].strip()
                
                # Nettoyer le texte
                card_text = self._clean_card_text(card_text)
                
                # Vérifier si le texte est significatif (au moins 5 caractères)
                if len(card_text) < 5:
                    return
                
                # Éviter les répétitions - vérifier si le message est similaire au précédent
                # en utilisant une comparaison plus souple pour les cartes Communauté
                if self._last_community_card_message and self._similar_text(card_text, self._last_community_card_message):
                    return
                
                # Stocker le message actuel
                self._last_community_card_message = card_text
                
                # Marquer ce texte comme une carte communauté pour éviter qu'il soit traité comme un achat de propriété
                self._seen_messages.add(card_text)
                
                # Afficher le texte de la carte
                self._display.print_info(f"Carte Communauté: {card_text}")
    
    def _clean_card_text(self, text):
        """Nettoie le texte des cartes pour éliminer les caractères indésirables"""
        # Supprimer les caractères non imprimables
        text = re.sub(r'[^\x20-\x7E\n]', '', text)
        
        # Supprimer les motifs spécifiques comme "XA" et "X04"
        text = re.sub(r'X[A-Z0-9]{1,4}', '', text)
        
        # Supprimer les caractères spéciaux restants tout en conservant la ponctuation utile
        text = re.sub(r'[^\w\s.,!?$%&*()\'"-:;]', '', text)
        
        # Remplacer les tildes par des caractères plus appropriés
        text = text.replace('~', '')
        
        # Supprimer les espaces multiples
        text = re.sub(r'\s+', ' ', text)
        
        # Traitement spécifique pour les cartes Communauté
        # Supprimer les préfixes communs
        text = re.sub(r'^Chest\s*', '', text)
        
        # Supprimer les suffixes numériques
        text = re.sub(r'\s*\d+$', '', text)
        
        # Nettoyer les montants d'argent (remplacer "Pay ~50" par "Pay $50")
        text = re.sub(r'Pay\s*~?(\d+)', r'Pay $\1', text)
        
        # Nettoyer les montants d'argent (remplacer "Collect ~50" par "Collect $50")
        text = re.sub(r'Collect\s*~?(\d+)', r'Collect $\1', text)
        
        # Nettoyer les montants d'argent (remplacer "Receive ~50" par "Receive $50")
        text = re.sub(r'Receive\s*~?(\d+)', r'Receive $\1', text)
        
        return text.strip()
                
    def _win_callback(self, addr, text):
        """Callback pour détecter un gagnant"""
        if text:
            # Chercher le texte réel après "Winner"
            if "Winner" in text:
                # Extraire le texte après "Winner"
                winner_text = text.split("Winner", 1)[1].strip()
                # Nettoyer le texte
                winner_text = self._clean_card_text(winner_text)
                
                # Éviter les répétitions
                if winner_text == self._last_win_message:
                    return
                self._last_win_message = winner_text
                
                # Afficher le texte du gagnant
                self._display.print_info(f"GAGNANT: {winner_text}")
    
    def _end_turn_callback(self, addr, text):
        """Callback pour détecter la fin d'un tour"""
        if text:
            # Utiliser une condition plus large pour détecter la fin d'un tour
            if "What would" in text and "like to do" in text:
                # Stocker l'adresse mémoire pour éviter les détections répétitives
                if self._last_end_turn_addr == addr:
                    return
                self._last_end_turn_addr = addr
                
                # Déterminer le joueur actuel
                current_player = "Inconnu"
                title, message = self.dialog_roll_dice
                if title:
                    current_player = title
                
                # Ne mettre à jour l'état que si ce n'est pas déjà la fin d'un tour
                # ou si c'est un joueur différent
                if not self._game_state['end_of_turn'] or self._game_state['current_player'] != current_player:
                    # Mettre à jour l'état du jeu
                    self._game_state['current_player'] = current_player
                    self._game_state['end_of_turn'] = True
                    self._game_state['end_of_turn_displayed'] = False  # Réinitialiser pour permettre l'affichage
                    
                    # Afficher le message de fin de tour
                    self._display.display_end_turn(current_player)
                    
                    # Marquer le message comme affiché
                    self._game_state['end_of_turn_displayed'] = True
    
    def _buy_property_callback(self, addr, text):
        """Callback pour détecter les messages d'achat de propriété"""
        if text:
            # Nettoyer le texte pour la comparaison
            cleaned_text = self._clean_card_text(text)
            
            # Vérifier si ce texte a déjà été traité comme une carte chance ou communauté
            if cleaned_text in self._seen_messages:
                return
            
            # Vérifier si le texte correspond au format spécifique d'achat de propriété
            # Plusieurs patterns possibles
            property_patterns = [
                # Format standard: "Do you want to buy X for Y?"
                re.compile(r'(Do you want|Would you like) to buy\s+([A-Za-z\s\.]+(?:Station|Avenue|Road|Street|Lane|Place|Gardens|Square|Park|Boardwalk|Walk|Company|Works))\s+for\s+\$?(\d+|\~\d+)\??', re.IGNORECASE),
                # Format court: "buy X for Y?"
                re.compile(r'buy\s+([A-Za-z\s\.]+(?:Station|Avenue|Road|Street|Lane|Place|Gardens|Square|Park|Boardwalk|Walk|Company|Works))\s+for\s+\$?(\d+|\~\d+)\??', re.IGNORECASE)
            ]
            
            # Essayer chaque pattern
            property_name = None
            property_price = None
            
            for pattern in property_patterns:
                match = pattern.search(cleaned_text)
                if match:
                    # Si c'est le pattern court, les groupes sont différents
                    if len(match.groups()) == 2:
                        property_name = match.group(1).strip()
                        property_price = match.group(2).strip().replace('~', '')
                    else:
                        property_name = match.group(2).strip()
                        property_price = match.group(3).strip().replace('~', '')
                    break
            
            if not property_name or not property_price:
                # Si aucun pattern ne correspond, ne pas traiter comme un achat de propriété
                return False
            
            # Convertir le prix en nombre si possible
            try:
                price_value = int(property_price)
            except ValueError:
                price_value = 0
            
            # Vérifier si c'est la même propriété que la dernière fois
            last_property, last_price = self._game_state['last_property_offer']
            
            # Déterminer le joueur actuel
            current_player = self._game_state.get('current_player', 'Inconnu')
            
            # Vérifier si c'est la même opportunité que la dernière fois
            current_opportunity = (current_player, property_name, property_price)
            if current_opportunity == self._current_property_opportunity:
                return False
            
            # Toujours afficher l'opportunité d'achat au début du jeu
            # ou si la propriété est différente de la dernière fois
            if property_name != last_property or price_value != last_price:
                # Mettre à jour l'opportunité actuelle
                self._current_property_opportunity = current_opportunity
                
                # Afficher le message d'achat
                self._display.display_property_purchase_opportunity(current_player, property_name, property_price)
                
                # Mettre à jour la dernière offre
                self._game_state['last_property_offer'] = (property_name, price_value)
                
                # Retourner True pour indiquer qu'une opportunité d'achat a été affichée
                return True
            
            # Retourner False si aucune opportunité d'achat n'a été affichée
            return False
    
    def detect_new_turn(self, message):
        """Détecte le début d'un nouveau tour et réinitialise l'état de fin de tour"""
        # Vérifier si c'est un message de début de tour
        if "shake the Wii Remote" in message and "to roll the dice" in message:
            # Mettre à jour le joueur actuel
            title, _ = self.dialog_roll_dice
            if title:
                # Si le joueur a changé ou si c'était la fin d'un tour
                if self._game_state.get('current_player') != title or self._game_state.get('end_of_turn', False):
                    # Réinitialiser l'état de fin de tour
                    self._game_state['end_of_turn'] = False
                    self._game_state['end_of_turn_displayed'] = False
                    
                    # Mettre à jour le joueur actuel seulement s'il a changé
                    if self._game_state.get('current_player') != title:
                        self._game_state['current_player'] = title
                        
                        # Afficher un message de début de tour
                        self._display.display_new_turn(title)
    
    def handle_property_purchase(self, message):
        """Gère l'affichage des messages d'achat de propriété en évitant les répétitions"""
        # Nettoyer le message
        cleaned_message = ""
        for char in message:
            if (32 <= ord(char) <= 126) or ('À' <= char <= 'ÿ') or char in ['€', '£', '¥', '©', '®', '™', '°', '±', '²', '³', '¼', '½', '¾']:
                cleaned_message += char
            else:
                # Arrêter au premier caractère non imprimable
                break
        
        # Vérifier que le message correspond au format spécifique d'achat de propriété
        # Plusieurs patterns possibles
        property_patterns = [
            # Format standard: "Do you want to buy X for Y?"
            re.compile(r'(Do you want|Would you like) to buy\s+([A-Za-z\s\.]+(?:Station|Avenue|Road|Street|Lane|Place|Gardens|Square|Park|Boardwalk|Walk|Company|Works))\s+for\s+\$?(\d+|\~\d+)\??', re.IGNORECASE),
            # Format court: "buy X for Y?"
            re.compile(r'buy\s+([A-Za-z\s\.]+(?:Station|Avenue|Road|Street|Lane|Place|Gardens|Square|Park|Boardwalk|Walk|Company|Works))\s+for\s+\$?(\d+|\~\d+)\??', re.IGNORECASE)
        ]
        
        # Essayer chaque pattern
        property_name = None
        property_price = None
        
        for pattern in property_patterns:
            match = pattern.search(cleaned_message)
            if match:
                # Si c'est le pattern court, les groupes sont différents
                if len(match.groups()) == 2:
                    property_name = match.group(1).strip()
                    property_price = match.group(2).strip().replace('~', '')
                else:
                    property_name = match.group(2).strip()
                    property_price = match.group(3).strip().replace('~', '')
                break
        
        if not property_name or not property_price:
            # Si aucun pattern ne correspond, ne pas traiter comme un achat de propriété
            return False
        
        # Convertir le prix en nombre si possible
        try:
            price_value = int(property_price)
        except ValueError:
            price_value = 0
        
        # Vérifier si c'est la même propriété que la dernière fois
        last_property, last_price = self._game_state['last_property_offer']
        
        # Déterminer le joueur actuel
        current_player = self._game_state.get('current_player', 'Inconnu')
        
        # Vérifier si c'est la même opportunité que la dernière fois
        current_opportunity = (current_player, property_name, property_price)
        if current_opportunity == self._current_property_opportunity:
            return False
        
        # Toujours afficher l'opportunité d'achat au début du jeu
        # ou si la propriété est différente de la dernière fois
        if property_name != last_property or price_value != last_price:
            # Mettre à jour l'opportunité actuelle
            self._current_property_opportunity = current_opportunity
            
            # Afficher le message d'achat
            self._display.display_property_purchase_opportunity(current_player, property_name, property_price)
            
            # Mettre à jour la dernière offre
            self._game_state['last_property_offer'] = (property_name, price_value)
            
            # Retourner True pour indiquer qu'une opportunité d'achat a été affichée
            return True
        
        # Retourner False si aucune opportunité d'achat n'a été affichée
        return False
    
    def display_game_state(self):
        """Affiche l'état actuel du jeu dans le format demandé, uniquement si des changements sont détectés"""
        try:
            # Récupérer l'état actuel du jeu
            current_state = {
                'blue_player': {
                    'label': self.blue_player.label,
                    'money': self.blue_player.money,
                    'position': self.blue_player.position,
                    'goto': self.blue_player.goto,
                    'dices': self.blue_player.dices
                },
                'red_player': {
                    'label': self.red_player.label,
                    'money': self.red_player.money,
                    'position': self.red_player.position,
                    'goto': self.red_player.goto,
                    'dices': self.red_player.dices
                },
                'dialog_roll_dice': self.dialog_roll_dice,
                'dialog_auction': self.dialog_auction,
                'current_player': self._game_state.get('current_player', ''),
                'end_of_turn': self._game_state.get('end_of_turn', False),
                'end_of_turn_displayed': self._game_state.get('end_of_turn_displayed', False),
                'last_property_offer': self._game_state.get('last_property_offer', ('', 0))
            }
            
            # Vérifier si un nouveau tour a commencé
            _, message = self.dialog_roll_dice
            if message:
                self.detect_new_turn(message)
                
                # Mettre à jour l'état actuel avec les nouvelles valeurs
                current_state['end_of_turn'] = self._game_state['end_of_turn']
                current_state['end_of_turn_displayed'] = self._game_state['end_of_turn_displayed']
                current_state['current_player'] = self._game_state['current_player']
            
            # Vérifier s'il y a un message d'achat de propriété
            buy_message = self.dialog_buy_property
            if buy_message:
                property_handled = self.handle_property_purchase(buy_message)
                if property_handled:
                    # Si une opportunité d'achat a été affichée, mettre à jour l'état actuel
                    current_state['last_property_offer'] = self._game_state['last_property_offer']
            
            # Vérifier s'il y a des changements
            has_changes = False
            
            # Vérifier les changements pour les joueurs
            for player_key in ['blue_player', 'red_player']:
                if self._display._previous_states.get(player_key) != current_state[player_key]:
                    has_changes = True
                    break
            
            # Vérifier les changements pour les dialogues
            if (self._display._previous_states.get('dialog_roll_dice') != current_state['dialog_roll_dice'] or
                self._display._previous_states.get('dialog_auction') != current_state['dialog_auction']):
                has_changes = True
            
            # Si aucun changement, ne rien afficher
            if not has_changes:
                return
            
            # État des joueurs
            for player, color in [(self.blue_player, 'blue'), (self.red_player, 'red')]:
                self._display.update_player(color, {
                    'label': player.label,
                    'money': player.money,
                    'position': player.position,
                    'goto': player.goto,
                    'dices': player.dices
                })
            
            # État des dialogues
            title, message = self.dialog_roll_dice
            self._display.update_dialog(title, message)
            
            # État des enchères
            auction_message, purchaser, name = self.dialog_auction
            self._display.update_auction(auction_message, purchaser, name)
            
            # Mettre à jour l'état précédent dans l'affichage
            self._display._previous_states.update({
                'blue_player': current_state['blue_player'],
                'red_player': current_state['red_player'],
                'dialog_roll_dice': current_state['dialog_roll_dice'],
                'dialog_auction': current_state['dialog_auction']
            })
            
            # Mettre à jour l'état du jeu
            self._game_state.update({
                'current_player': current_state['current_player'],
                'end_of_turn': current_state['end_of_turn'],
                'end_of_turn_displayed': current_state['end_of_turn_displayed'],
                'last_property_offer': current_state['last_property_offer']
            })
        except Exception as e:
            self._display.print_error(f"Erreur lors de l'affichage de l'état du jeu: {str(e)}")
    
    def display_properties(self):
        """Affiche la liste des propriétés une seule fois"""
        try:
            self._display.print_info("Liste des propriétés disponibles:")
            for prop in self.properties:
                loyers = ", ".join([f"${rent}" for rent in prop.rents])
                self._display.print_property(
                    f"{prop.name} - Prix: ${prop.price} | "
                    f"Hypothèque: ${prop.mortgage} | "
                    f"Maison: ${prop.house_cost} | "
                    f"Loyers: [{loyers}]"
                )
        except Exception as e:
            self._display.print_error(f"Erreur lors de l'affichage des propriétés: {str(e)}")

    def _similar_text(self, text1, text2, threshold=0.8):
        """Vérifie si deux textes sont similaires en utilisant une mesure de similarité simple"""
        # Si les textes sont identiques, ils sont similaires
        if text1 == text2:
            return True
        
        # Si l'un des textes est vide, ils ne sont pas similaires
        if not text1 or not text2:
            return False
        
        # Si l'un des textes est contenu dans l'autre, ils sont similaires
        if text1 in text2 or text2 in text1:
            return True
        
        # Compter les mots communs
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        # Si les ensembles de mots sont vides, ils ne sont pas similaires
        if not words1 or not words2:
            return False
        
        # Calculer la similarité de Jaccard
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        # Retourner True si la similarité est supérieure au seuil
        return intersection / union >= threshold 