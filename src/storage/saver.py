import os
import logging
from datetime import datetime
from .models import Conversation
from .formats.markdown import MarkdownFormatter
from .formats.json import JsonFormatter
from .formats.txt import TxtFormatter

class ConversationSaver:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.formatters = {
            'md': MarkdownFormatter(),
            'json': JsonFormatter(),
            'txt': TxtFormatter()
        }
        self._create_output_dir()

    def _create_output_dir(self):
        """
        Creates the output directory if it doesn't exist.
        """
        try:
            os.makedirs(self.output_dir, exist_ok=True)
        except OSError as e:
            logging.error(f"Error creating output directory {self.output_dir}: {e}")

    def save(self, conversation: Conversation, file_format: str):
        """
        Saves the conversation to a file in the specified format.
        """
        if file_format not in self.formatters:
            logging.error(f"Unsupported file format: {file_format}")
            return

        formatter = self.formatters[file_format]
        content = formatter.format(conversation)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"blackstory_{timestamp}.{file_format}"
        filepath = os.path.join(self.output_dir, filename)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            logging.info(f"Conversation saved to {filepath}")
        except IOError as e:
            logging.error(f"Error writing to file {filepath}: {e}")
