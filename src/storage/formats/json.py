import json
from dataclasses import asdict
from ...storage.models import Conversation

class JsonFormatter:
    def format(self, conversation: Conversation) -> str:
        """
        Formats the conversation as a JSON string.
        """
        # A custom encoder to handle datetime objects
        class DateTimeEncoder(json.JSONEncoder):
            def default(self, o):
                if hasattr(o, 'isoformat'):
                    return o.isoformat()
                return super().default(o)

        # Prepare the data structure
        data = {
            "metadata": {
                "date": conversation.start_time,
                "model1": {"name": conversation.model1_name, "provider": conversation.model1_provider, "role": "Story Master"},
                "model2": {"name": conversation.model2_name, "provider": conversation.model2_provider, "role": "Detective"},
                "result": conversation.result,
                "questions_used": conversation.questions_used,
                "max_questions": conversation.max_questions
            },
            "messages": [asdict(msg) for msg in conversation.messages]
        }
        
        return json.dumps(data, cls=DateTimeEncoder, indent=2)
