from ...storage.models import Conversation

class TxtFormatter:
    def format(self, conversation: Conversation) -> str:
        """
        Formats the conversation as a plain text string.
        """
        content = "=== BLACK STORY GAME ===\n"
        content += f"Fecha: {conversation.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        content += f"Modelo 1: {conversation.model1_name} (Story Master)\n"
        content += f"Modelo 2: {conversation.model2_name} (Detective)\n"
        content += f"Resultado: {conversation.result}\n"
        content += f"Preguntas: {conversation.questions_used}/{conversation.max_questions}\n\n---\n\n"

        for msg in conversation.messages:
            meta = f"({msg.response_time:.2f}s"
            if msg.tokens:
                meta += f", {msg.tokens} tokens"
            meta += ")"
            
            if msg.role == "Story Master":
                content += f"[{msg.timestamp.strftime('%H:%M:%S')}] MODELO 1 {meta}:\n"
            else:
                content += f"[{msg.timestamp.strftime('%H:%M:%S')}] MODELO 2 {meta}:\n"
            
            content += f"{msg.content}\n\n"
        
        return content
