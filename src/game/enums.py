from enum import Enum, auto

class GameState(Enum):
    """
    Representa los estados internos del juego.
    """
    EN_PROGRESO = auto()      # Juego activo, detective haciendo preguntas
    BLOQUEADO = auto()        # Juego detenido, esperando intervención (ej. límite de preguntas alcanzado)
    CERCA = auto()            # El detective está muy cerca de la solución (opcional, para feedback visual)
    RESUELTO = auto()         # Juego terminado
    ERROR = auto()            # Estado de error irrecuperable

class EventType(Enum):
    """
    Tipos de eventos que pueden ocurrir durante el juego.
    Diseñado para ser extensible.
    """
    INICIO_JUEGO = auto()         # El juego ha comenzado
    NEW_STORY = auto()            # Se ha generado una nueva historia
    PREGUNTA_DETECTIVE = auto()   # El detective ha hecho una pregunta
    RESPUESTA_MAESTRO = auto()    # El maestro de historia ha respondido
    CAMBIO_ESTADO = auto()        # El estado interno del juego ha cambiado
    FIN_JUEGO = auto()            # El juego ha terminado (victoria o derrota)
    ERROR = auto()                # Ha ocurrido un error
    INTERVENCION = auto()         # Un humano o sistema externo ha intervenido (ej. pista forzada)
    LOG = auto()                  # Mensaje de log para mostrar en consola/UI
