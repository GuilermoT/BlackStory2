import logging
import click
from src.providers.gemini import GeminiProvider
from src.providers.ollama import OllamaProvider
from src.game.orchestrator import GameOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('blackstory.log'),
        logging.StreamHandler()
    ]
)

def get_provider(provider_name: str, model_name: str):
    if provider_name == 'gemini':
        return GeminiProvider(model_name)
    elif provider_name == 'ollama':
        return OllamaProvider(model_name)
    else:
        raise ValueError(f"Unsupported provider: {provider_name}")

@click.command()
@click.option('-m1', '--model1', required=True, help='Name of the first model (Story Master)')
@click.option('-m2', '--model2', required=True, help='Name of the second model (Detective)')
@click.option('-p1', '--provider1', required=True, type=click.Choice(['gemini', 'ollama']), help='Provider of the model 1')
@click.option('-p2', '--provider2', required=True, type=click.Choice(['gemini', 'ollama']), help='Provider of the model 2')
@click.option('--save-format', type=click.Choice(['json', 'txt', 'md']), default='md', help='Format of the saved conversation')
@click.option('--max-questions', type=int, default=20, help='Maximum number of questions allowed')
@click.option('--no-pause', is_flag=True, help='Disables the pause between messages')
@click.option('--output-dir', default='./conversations', help='Folder where conversations will be saved')
def main(model1, model2, provider1, provider2, save_format, max_questions, no_pause, output_dir):
    """
    Black Stories game with AI models competing.
    """
    logging.info("Starting Black Stories AI game")
    
    try:
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
        game.play()

    except ValueError as e:
        logging.error(f"Configuration error: {e}")
        click.echo(f"❌ Error: {e}")
    except KeyboardInterrupt:
        logging.warning("Game interrupted by user.")
        click.echo("\n⚠️ Juego interrumpido por el usuario.")
        # The orchestrator will handle saving on exit
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        click.echo(f"❌ Ocurrió un error inesperado: {e}")

if __name__ == '__main__':
    main()
