"""
Service de logging unifié pour tous les composants
"""
import os
import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional
from .event_bus import EventBus, EventTypes

class LoggingService:
    """Service centralisé pour le logging avec persistance"""
    
    def __init__(self, event_bus: EventBus, log_dir: str = "logs"):
        self.event_bus = event_bus
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Créer les fichiers de log
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.main_log_file = self.log_dir / f"monopoly_{timestamp}.log"
        self.popup_log_file = self.log_dir / f"popups_{timestamp}.log"
        self.error_log_file = self.log_dir / f"errors_{timestamp}.log"
        
        # Configurer les loggers
        self._setup_loggers()
        
        # Buffer pour les logs récents (pour l'API)
        self.recent_logs = []
        self.log_lock = threading.Lock()
        
        # S'abonner à tous les événements
        self.event_bus.subscribe('*', self._log_event)
        
    def _setup_loggers(self):
        """Configure les différents loggers"""
        # Logger principal
        self.main_logger = self._create_logger(
            'monopoly.main',
            self.main_log_file,
            logging.INFO
        )
        
        # Logger popups
        self.popup_logger = self._create_logger(
            'monopoly.popups',
            self.popup_log_file,
            logging.DEBUG
        )
        
        # Logger erreurs
        self.error_logger = self._create_logger(
            'monopoly.errors',
            self.error_log_file,
            logging.ERROR
        )
    
    def _create_logger(self, name: str, file_path: Path, level: int) -> logging.Logger:
        """Crée et configure un logger"""
        logger = logging.getLogger(name)
        logger.setLevel(level)
        
        # Handler fichier
        file_handler = logging.FileHandler(file_path, encoding='utf-8')
        file_handler.setLevel(level)
        
        # Format
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        return logger
    
    def log(self, message: str, level: str = 'info', component: str = 'system', extra: dict = None):
        """Log un message"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': level,
            'component': component,
            'message': message,
            'extra': extra or {}
        }
        
        # Ajouter au buffer récent
        with self.log_lock:
            self.recent_logs.append(log_entry)
            if len(self.recent_logs) > 1000:
                self.recent_logs.pop(0)
        
        # Logger selon le niveau
        if level == 'error':
            self.error_logger.error(f"[{component}] {message}", extra=extra)
        elif level == 'warning':
            self.main_logger.warning(f"[{component}] {message}", extra=extra)
        elif level == 'debug':
            self.main_logger.debug(f"[{component}] {message}", extra=extra)
        else:
            self.main_logger.info(f"[{component}] {message}", extra=extra)
        
        # Publier l'événement de log
        self.event_bus.publish('log.created', log_entry, source='logging_service')
        
        return log_entry
    
    def log_popup(self, popup_id: str, action: str, details: dict):
        """Log spécifique pour les popups"""
        log_data = {
            'popup_id': popup_id,
            'action': action,
            'details': details,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self.popup_logger.info(json.dumps(log_data))
        
        # Aussi dans le log principal
        self.log(
            f"Popup {popup_id}: {action}",
            level='info',
            component='popup_system',
            extra=log_data
        )
    
    def log_error(self, error: Exception, component: str, context: dict = None):
        """Log une erreur avec le contexte"""
        import traceback
        
        error_data = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc(),
            'component': component,
            'context': context or {}
        }
        
        self.error_logger.error(json.dumps(error_data, indent=2))
        
        # Publier l'événement d'erreur
        self.event_bus.publish(
            EventTypes.SERVICE_ERROR,
            error_data,
            source='logging_service'
        )
        
        return self.log(
            f"{type(error).__name__}: {str(error)}",
            level='error',
            component=component,
            extra=error_data
        )
    
    def get_recent_logs(self, count: int = 100, level: Optional[str] = None, component: Optional[str] = None):
        """Récupère les logs récents avec filtres optionnels"""
        with self.log_lock:
            logs = list(self.recent_logs)
        
        # Filtrer si nécessaire
        if level:
            logs = [l for l in logs if l['level'] == level]
        if component:
            logs = [l for l in logs if l['component'] == component]
        
        # Retourner les N derniers
        return logs[-count:]
    
    def _log_event(self, event: dict):
        """Callback pour logger tous les événements"""
        # Ne pas logger les événements de log pour éviter la récursion
        if event['type'].startswith('log.'):
            return
        
        # Logger l'événement
        self.log(
            f"Event: {event['type']}",
            level='debug',
            component=event.get('source', 'unknown'),
            extra={
                'event_id': event.get('id'),
                'event_data': event.get('data')
            }
        )
    
    def get_log_files(self):
        """Retourne la liste des fichiers de log"""
        return {
            'main': str(self.main_log_file),
            'popups': str(self.popup_log_file),
            'errors': str(self.error_log_file)
        }