from abc import ABC, abstractmethod
from typing import Any

class BaseProvider(ABC):
    """
    Abstract base class for AI model providers.
    """

    def __init__(self, model_name: str):
        """
        Initializes the provider with a specific model name.

        Args:
            model_name (str): The name of the model to use.
        """
        self.model_name = model_name

    @abstractmethod
    def generate_response(self, prompt: str, **kwargs: Any) -> str:
        """
        Generates a response from the AI model.

        Args:
            prompt (str): The prompt to send to the model.
            **kwargs: Additional provider-specific arguments.

        Returns:
            str: The generated text response from the model.
        """
        pass
