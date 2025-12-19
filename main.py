import logging
import click
import threading
from src.providers.gemini import GeminiProvider
from src.providers.ollama import OllamaProvider
from src.game.orchestrator import GameOrchestrator
from src.display.terminal import TerminalObserver

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG to see full model responses
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('blackstory.log'),
        logging.StreamHandler()
    ]
)

@click.command()
@click.option('-m1', '--model1', required=False, help='Name of the first model (Story Master)')
@click.option('-m2', '--model2', required=False, help='Name of the second model (Detective)')
@click.option('-p1', '--provider1', required=False, type=click.Choice(['gemini', 'ollama']), help='Provider of the model 1')
@click.option('-p2', '--provider2', required=False, type=click.Choice(['gemini', 'ollama']), help='Provider of the model 2')
@click.option('--save-format', type=click.Choice(['json', 'txt', 'md']), default='md', help='Format of the saved conversation')
@click.option('--max-questions', type=int, default=10, help='Maximum number of questions allowed')
@click.option('--no-pause', is_flag=True, help='Disables the pause between messages')
@click.option('--output-dir', default='./conversations', help='Folder where conversations will be saved')
@click.option('--ui', is_flag=True, help='Lanza la interfaz gráfica')
@click.option('--human-moderator', is_flag=True, help='Activa el rol de Moderador Humano (solo en UI)')
def main(model1, model2, provider1, provider2, save_format, max_questions, no_pause, output_dir, ui, human_moderator):
    """
    Black Stories game with AI models competing.
    """
    logging.info("Starting Black Stories AI game")
    
    # Check if CLI args are sufficient for headless mode
    cli_mode = model1 and model2 and provider1 and provider2
    
    # Logic:
    # 1. If explicit --ui flag OR missing required CLI args -> Launch GUI
    # 2. If explicit args provided -> Launch CLI (Headless)
    
    launch_gui = ui or not cli_mode
    
    if not launch_gui and not cli_mode:
        # This case is tricky with click required=False. 
        # Ideally we want: "If user provided NOTHING -> GUI". "If user provided PARTIAL args -> Error".
        # But for simplicity, we treat partial args as "Try GUI with defaults" or just GUI.
        pass

    try:
        if launch_gui:
            from src.display.gui import BlackStoryGUI
            
            # If args were provided, we can pre-seed the Game (CLI --ui mode)
            game = None
            if cli_mode:
                 provider1_instance = get_provider(provider1, model1)
                 provider2_instance = get_provider(provider2, model2)
                 game = GameOrchestrator(
                    model1=provider1_instance,
                    model2=provider2_instance,
                    max_questions=max_questions,
                    no_pause=False,  # GUI mode needs pause for step control
                    output_dir=output_dir,
                    save_format=save_format
                )
                 # Add terminal observer too
                 obs = TerminalObserver()
                 game.subscribe(obs)

            app = BlackStoryGUI(orchestrator=game, human_moderator=human_moderator)
            app.mainloop() # CTk mainloop
            
        else:
            # Headless CLI Mode
            from src.game.providers_factory import get_provider
            
            provider1_instance = get_provider(provider1, model1)
            provider2_instance = get_provider(provider2, model2)

            game = GameOrchestrator(
                model1=provider1_instance,
                model2=provider2_instance,
                max_questions=max_questions,
                no_pause=no_pause,
                output_dir=output_dir,
                save_format=save_format
            )
            
            # Modo Consola Clásico
            observer = TerminalObserver()
            game.subscribe(observer)
            game.play()

    except ValueError as e:
        logging.error(f"Configuration error: {e}")
        click.echo(f"❌ Error: {e}")
    except KeyboardInterrupt:
        logging.warning("Game interrupted by user.")
        click.echo("\n⚠️ Juego interrumpido por el usuario.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        click.echo(f"❌ Ocurrió un error inesperado al iniciar: {e}")

if __name__ == '__main__':
    main()
