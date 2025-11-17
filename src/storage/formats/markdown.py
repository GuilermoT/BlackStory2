from ...storage.models import Conversation

class MarkdownFormatter:
    def format(self, conversation: Conversation) -> str:
        """
        Formats the conversation as a Markdown string.
        """
        content = f"# Black Story Game\n\n"
        content += f"**Fecha:** {conversation.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        content += f"**Modelo 1:** {conversation.model1_name} (Story Master)\n"
        content += f"**Modelo 2:** {conversation.model2_name} (Detective)\n"
        content += f"**Resultado:** {conversation.result}\n"
        content += f"**Preguntas usadas:** {conversation.questions_used}/{conversation.max_questions}\n\n---\n\n"

        for msg in conversation.messages:
            if msg.role == "Story Master":
                content += f"## 🎭 Modelo 1 [{msg.timestamp.strftime('%H:%M:%S')}] ⚡{msg.response_time:.2f}s\n"
            else:
                content += f"## 🔍 Modelo 2 [{msg.timestamp.strftime('%H:%M:%S')}] ⚡{msg.response_time:.2f}s\n"
            content += f"{msg.content}\n\n"
        
        return content
