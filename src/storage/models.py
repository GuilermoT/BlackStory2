from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

@dataclass
class Message:
    """
    Represents a single message in the conversation.
    """
    model_name: str
    provider: str
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    response_time: Optional[float] = None
    tokens: Optional[int] = None

@dataclass
class Conversation:
    """
    Represents a full game conversation.
    """
    model1_name: str
    model1_provider: str
    model2_name: str
    model2_provider: str
    max_questions: int
    full_solution: str = "" # Added full_solution field
    start_time: datetime = field(default_factory=datetime.now)
    messages: List[Message] = field(default_factory=list)
    result: Optional[str] = None
    questions_used: int = 0

    def add_message(self, message: Message):
        """
        Adds a message to the conversation.
        """
        self.messages.append(message)
