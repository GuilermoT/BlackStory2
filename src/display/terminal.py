import logging
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from ..game.interfaces import GameObserver
from ..game.events import GameEvent, EventType
from ..game.enums import GameState
from ..display.ui import print_message

class TerminalObserver(GameObserver):
    """
    Observador que maneja la salida por terminal (legacy mode).
    Escucha eventos y utiliza 'rich' para mostrar la información.
    """
    def __init__(self, console: Console = None):
        self.console = console or Console()

    def on_event(self, event: GameEvent):
        try:
            if event.type == EventType.INICIO_JUEGO:
                self.console.print("[bold green]🎮 Juego Iniciado[/bold green]")

            elif event.type == EventType.NEW_STORY:
                # El mensaje inicial del Story Master
                if "message" in event.payload:
                    print_message(event.payload["message"])
                if "full_solution" in event.payload:
                    # Mostrar solución en modo debug o si se desea
                     self.console.print(Panel(Text(event.payload["full_solution"], justify="left"), title="[bold yellow]Solución Completa (Debug)[/]", border_style="yellow"))

            elif event.type == EventType.PREGUNTA_DETECTIVE:
                if "message" in event.payload:
                    questions_asked = event.payload.get("questions_asked", 0)
                    max_questions = event.payload.get("max_questions", 10)
                    print_message(event.payload["message"], questions_asked, max_questions)

            elif event.type == EventType.RESPUESTA_MAESTRO:
                if "message" in event.payload:
                    print_message(event.payload["message"])

            elif event.type == EventType.FIN_JUEGO:
                result = event.payload.get("result", "Desconocido")
                final_message = event.payload.get("message_obj")
                if final_message:
                     print_message(final_message)
                
                color = "green" if result == "Victoria" else "red"
                self.console.print(f"[{color}]🏁 Fin del juego: {result}[/{color}]")

            elif event.type == EventType.ERROR:
                self.console.print(f"[bold red]❌ Error: {event.message}[/bold red]")

            elif event.type == EventType.LOG:
                # Opcional: mostrar logs en terminal
                pass

        except Exception as e:
            logging.error(f"Error en TerminalObserver: {e}")
