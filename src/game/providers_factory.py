from ..providers.gemini import GeminiProvider
from ..providers.ollama import OllamaProvider

def get_provider(provider_name: str, model_name: str):
    if provider_name == 'gemini':
        return GeminiProvider(model_name)
    elif provider_name == 'ollama':
        return OllamaProvider(model_name)
    else:
        raise ValueError(f"Unsupported provider: {provider_name}")
