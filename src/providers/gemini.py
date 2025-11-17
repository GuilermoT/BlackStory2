import os
import logging
from typing import Any
import google.generativeai as genai
from dotenv import load_dotenv
from .base import BaseProvider

# Load environment variables
load_dotenv()

class GeminiProvider(BaseProvider):
    """
    Provider for Google Gemini models.
    """

    def __init__(self, model_name: str):
        """
        Initializes the Gemini provider.
        """
        super().__init__(model_name)
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in .env file")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)
        logging.info(f"Gemini provider initialized with model: {self.model_name}")

    def generate_response(self, prompt: str, **kwargs: Any) -> str:
        """
        Generates a response from the Gemini model.
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logging.error(f"Error generating response from Gemini: {e}")
            return "Error: Could not get a response from the model."
