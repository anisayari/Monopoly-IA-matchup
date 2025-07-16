"""
Event Bus centralisé pour la communication entre services
"""
import json
import threading
from datetime import datetime
from typing import Dict, List, Callable, Any
import redis
from flask_socketio import SocketIO

class EventBus:
    """Système de messaging centralisé avec Redis et WebSocket"""
    
    def __init__(self, app=None, redis_host='localhost', redis_port=6379):
        self.app = app
        self.redis_client = None
        self.socketio = None
        self.subscribers: Dict[str, List[Callable]] = {}
        self.redis_thread = None
        self.running = False
        
        if app:
            self.init_app(app, redis_host, redis_port)
    
    def init_app(self, app, redis_host='localhost', redis_port=6379):
        """Initialise l'Event Bus avec Flask"""
        self.app = app
        
        # Initialiser SocketIO
        self.socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
        
        # Initialiser Redis
        try:
            self.redis_client = redis.Redis(
                host=redis_host, 
                port=redis_port, 
                decode_responses=True
            )
            self.redis_client.ping()
            print(f"✅ Connecté à Redis sur {redis_host}:{redis_port}")
            
            # Démarrer l'écoute Redis
            self.start_redis_listener()
        except redis.ConnectionError:
            print(f"⚠️  Redis non disponible sur {redis_host}:{redis_port}")
            print("   Les événements ne seront pas persistés")
    
    def publish(self, event_type: str, data: Any, source: str = 'system'):
        """Publie un événement"""
        event = {
            'type': event_type,
            'data': data,
            'source': source,
            'timestamp': datetime.utcnow().isoformat(),
            'id': self._generate_event_id()
        }
        
        # Publier sur Redis si disponible
        if self.redis_client:
            try:
                self.redis_client.publish('monopoly_events', json.dumps(event))
            except:
                pass
        
        # Émettre via WebSocket si disponible
        if self.socketio:
            self.socketio.emit(event_type, event)
        
        # Appeler les callbacks locaux
        self._call_local_subscribers(event_type, event)
        
        return event['id']
    
    def subscribe(self, event_type: str, callback: Callable):
        """S'abonne à un type d'événement"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)
    
    def unsubscribe(self, event_type: str, callback: Callable):
        """Se désabonne d'un type d'événement"""
        if event_type in self.subscribers:
            self.subscribers[event_type].remove(callback)
    
    def _call_local_subscribers(self, event_type: str, event: dict):
        """Appelle les callbacks locaux"""
        # Callbacks pour ce type spécifique
        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                try:
                    callback(event)
                except Exception as e:
                    print(f"⚠️  Erreur dans callback {callback.__name__}: {e}")
        
        # Callbacks wildcard
        if '*' in self.subscribers:
            for callback in self.subscribers['*']:
                try:
                    callback(event)
                except Exception as e:
                    print(f"⚠️  Erreur dans callback wildcard: {e}")
    
    def start_redis_listener(self):
        """Démarre l'écoute des événements Redis"""
        if not self.redis_client:
            return
        
        def listen():
            pubsub = self.redis_client.pubsub()
            pubsub.subscribe('monopoly_events')
            
            self.running = True
            while self.running:
                try:
                    message = pubsub.get_message(timeout=1.0)
                    if message and message['type'] == 'message':
                        event = json.loads(message['data'])
                        
                        # Réémettre via WebSocket
                        if self.socketio:
                            self.socketio.emit(event['type'], event)
                        
                        # Appeler les callbacks locaux
                        self._call_local_subscribers(event['type'], event)
                except Exception as e:
                    print(f"⚠️  Erreur Redis listener: {e}")
        
        self.redis_thread = threading.Thread(target=listen, daemon=True)
        self.redis_thread.start()
    
    def stop(self):
        """Arrête l'Event Bus"""
        self.running = False
        if self.redis_thread:
            self.redis_thread.join(timeout=2)
    
    def _generate_event_id(self):
        """Génère un ID unique pour l'événement"""
        import uuid
        return str(uuid.uuid4())

# Types d'événements standards
class EventTypes:
    # Popup events
    POPUP_DETECTED = 'popup.detected'
    POPUP_ANALYZED = 'popup.analyzed'
    POPUP_DECISION = 'popup.decision'
    POPUP_EXECUTED = 'popup.executed'
    
    # Game events
    GAME_STARTED = 'game.started'
    GAME_STOPPED = 'game.stopped'
    GAME_STATE_UPDATED = 'game.state_updated'
    
    # System events
    SERVICE_STARTED = 'service.started'
    SERVICE_STOPPED = 'service.stopped'
    SERVICE_ERROR = 'service.error'
    
    # AI events
    AI_DECISION_REQUESTED = 'ai.decision_requested'
    AI_DECISION_MADE = 'ai.decision_made'
    AI_ERROR = 'ai.error'