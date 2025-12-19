from abc import ABC, abstractmethod
from .events import GameEvent

class GameObserver(ABC):
    """
    Interfaz para cualquier clase que quiera escuchar eventos del juego.
    """
    
    @abstractmethod
    def on_event(self, event: GameEvent):
        """
        Método llamado cuando ocurre un evento.
        """
        pass
