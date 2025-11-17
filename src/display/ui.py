from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from ..storage.models import Message

console = Console()

def print_message(message: Message, question_count: int = 0, max_questions: int = 0):
    """
    Prints a formatted message box to the console.
    """
    if message.role == "Story Master":
        title = f"🎭 MODELO 1 ({message.model_name}) | Story Master"
        color = "cyan"
        emoji = "🎭"
    else:
        title = f"🔍 MODELO 2 ({message.model_name}) | Detective"
        color = "magenta"
        emoji = "🔍"

    meta = f"⏱️ {message.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
    if message.response_time:
        meta += f" | ⚡ {message.response_time:.2f}s"
    if message.tokens:
        meta += f" | 🎫 {message.tokens} tokens"
    if question_count > 0:
        meta += f" | ❓ {question_count}/{max_questions}"

    header = Text.from_markup(f"[bold {color}]{title}[/]\n[dim]{meta}[/]")
    
    content_panel = Panel(
        Text(message.content, justify="left"),
        title=header,
        border_style=color,
        expand=False
    )
    console.print(content_panel)

def wait_for_enter(no_pause: bool):
    """
    Pauses execution until the user presses Enter.
    """
    if not no_pause:
        input("Presiona ENTER para continuar...")
