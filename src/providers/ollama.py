import os
import logging
from typing import Any
import ollama
from dotenv import load_dotenv
from .base import BaseProvider

# Load environment variables
load_dotenv()

class OllamaProvider(BaseProvider):
    """
    Provider for Ollama models.
    """

    def __init__(self, model_name: str):
        """
        Initializes the Ollama provider.
        """
        super().__init__(model_name)
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.client = ollama.Client(host=self.base_url)
        logging.info(f"Ollama provider initialized with model: {self.model_name} at {self.base_url}")

    def generate_response(self, prompt: str, **kwargs: Any) -> str:
        """
        Generates a response from the Ollama model.
        """
        try:
            response = self.client.chat(
                model=self.model_name,
                messages=[{'role': 'user', 'content': prompt}]
            )
            return response['message']['content']
        except Exception as e:
            logging.error(f"Error generating response from Ollama: {e}")
            logging.error("Is Ollama running? You can start it with 'ollama serve'")
            return "Error: Could not get a response from the model."
