from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import time
from .enums import EventType

@dataclass
class GameEvent:
    """
    Representa un evento ocurrido en el juego.
    """
    type: EventType
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    message: Optional[str] = None  # Mensaje legible opcional

    def __str__(self):
        return f"[{self.timestamp}] {self.type.name}: {self.message or ''} | Payload: {self.payload}"
