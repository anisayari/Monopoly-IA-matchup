class EventListeners:
    def __init__(self):
        self._listeners = {}

    def on(self, event_name, callback):
        if event_name not in self._listeners:
            self._listeners[event_name] = []
        self._listeners[event_name].append(callback)
        
    def off(self, event_name, callback):
        if event_name in self._listeners:
            self._listeners[event_name].remove(callback)

    def emit(self, event_name, *args, **kwargs):
        if "*" in self._listeners:
            for callback in self._listeners["*"]:
                callback(event_name, *args, **kwargs)
        if event_name in self._listeners:
            for callback in self._listeners[event_name]:
                callback(*args, **kwargs)
