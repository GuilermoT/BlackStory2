import time
import logging
from rich.panel import Panel
from rich.text import Text
from rich.console import Console
from ..providers.base import BaseProvider
from ..storage.models import Conversation, Message
from ..storage.saver import ConversationSaver
from ..display.ui import print_message, wait_for_enter
from .prompts import STORY_MASTER_PROMPT, DETECTIVE_PROMPT

console = Console()

class GameOrchestrator:
    def __init__(self, model1: BaseProvider, model2: BaseProvider, max_questions: int, no_pause: bool, output_dir: str, save_format: str):
        self.model1 = model1
        self.model2 = model2
        self.max_questions = max_questions
        self.no_pause = no_pause
        self.output_dir = output_dir
        self.save_format = save_format
        self.saver = ConversationSaver(output_dir)
        self.conversation = Conversation(
            model1_name=self.model1.model_name,
            model1_provider=self.model1.__class__.__name__,
            model2_name=self.model2.model_name,
            model2_provider=self.model2.__class__.__name__,
            max_questions=self.max_questions,
            full_solution="" # Add full_solution to Conversation model
        )

    def play(self):
        logging.info("Starting a new game.")
        
        # Fase 1: Inicio
        self._start_game()

        # Fase 2: Interrogatorio
        self._interrogation_loop()

        # Fase 3: Resolución
        self._resolve_game()

        # Fase 4: Guardado
        self._save_conversation()

    def _start_game(self):
        # Model 1 creates the story
        prompt = STORY_MASTER_PROMPT.format(max_questions=self.max_questions)
        start_time = time.time()
        raw_story_response = self.model1.generate_response(prompt)
        response_time = time.time() - start_time
        
        # Parse the story and solution
        story_situation = ""
        full_solution = ""
        
        if "SITUACIÓN:" in raw_story_response and "SOLUCIÓN:" in raw_story_response:
            parts = raw_story_response.split("SOLUCIÓN:", 1)
            story_situation = parts[0].replace("SITUACIÓN:", "").strip()
            full_solution = parts[1].strip()
        else:
            logging.warning("Story Master did not follow the expected format. Using full response as situation.")
            story_situation = raw_story_response.strip()
            full_solution = "No se pudo extraer la solución completa." # Fallback

        self.conversation.full_solution = full_solution
        
        # Display the full solution for debugging
        console.print(Panel(Text(full_solution, justify="left"), title="[bold yellow]Solución Completa (Debug)[/]", border_style="yellow"))

        # The message displayed to the detective should only contain the situation and rules
        display_content = f"🎭 HISTORIA:\n\n{story_situation}\n\n📋 REGLAS:\n\n- Solo puedes hacer preguntas que se respondan con SÍ, NO o NO ES RELEVANTE\n- Cuando creas tener la solución completa, di \"RESOLVER:\" seguido de tu explicación\n- Tienes un máximo de {self.max_questions} preguntas\n\n¡Empieza a preguntar!"

        msg = Message("model1", self.model1.model_name, "Story Master", display_content, response_time=response_time)
        self.conversation.add_message(msg)
        print_message(msg)
        wait_for_enter(self.no_pause)

    def _format_history(self):
        history = []
        # Skip the first message (initial story)
        for msg in self.conversation.messages[1:]:
            role = "Detective" if msg.role == "Detective" else "Respuesta"
            history.append(f"- {role}: {msg.content.strip()}")
        return "\n".join(history) if history else "Aún no hay preguntas."

    def _interrogation_loop(self):
        questions_asked = 0
        score_feedback = "Esta es tu primera pregunta. ¡Analiza bien la situación!"
        while questions_asked < self.max_questions:
            # Model 2 asks a question
            story_situation = self.conversation.messages[0].content
            conversation_history = self._format_history()
            prompt = DETECTIVE_PROMPT.format(
                story_situation=story_situation,
                conversation_history=conversation_history,
                max_questions=self.max_questions,
                questions_left=self.max_questions - questions_asked,
                score_feedback=score_feedback
            )
            start_time = time.time()
            question = self.model2.generate_response(prompt)
            response_time = time.time() - start_time
            
            questions_asked += 1
            msg = Message("model2", self.model2.model_name, "Detective", question, response_time=response_time)
            self.conversation.add_message(msg)
            print_message(msg, questions_asked, self.max_questions)
            wait_for_enter(self.no_pause)

            if "RESOLVER:" in question.upper():
                break

            # Model 1 answers
            start_time = time.time()
            answer_prompt = (
                f"La pregunta del detective es: '{question}'.\n"
                f"La historia completa y secreta es: '{self.conversation.full_solution}'.\n"
                "Basa tu respuesta ÚNICAMENTE en la historia secreta. Responde con SÍ, NO o NO ES RELEVANTE. "
                "Luego, en una nueva línea, añade una puntuación de 1 a 10 sobre qué tan cerca está el detective de la solución, "
                "usando el formato PUNTUACIÓN: X/10."
            )
            answer_raw = self.model1.generate_response(answer_prompt)
            response_time = time.time() - start_time

            # Parse score and update feedback for the detective
            answer_display = answer_raw
            try:
                if "PUNTUACIÓN:" in answer_raw:
                    parts = answer_raw.split("PUNTUACIÓN:")
                    answer_display = parts[0].strip()
                    score = parts[1].strip()
                    score_feedback = f"La puntuación de tu última pregunta fue {score}. ¡Sigue investigando!"
                else:
                    score_feedback = "No se recibió puntuación. Intenta ser más específico."
            except Exception:
                score_feedback = "Hubo un problema al procesar la puntuación."

            msg = Message("model1", self.model1.model_name, "Story Master", answer_display, response_time=response_time)
            self.conversation.add_message(msg)
            print_message(msg)
            wait_for_enter(self.no_pause)

        self.conversation.questions_used = questions_asked

    def _resolve_game(self):
        # Final evaluation by Model 1
        last_response = self.conversation.messages[-1].content
        if "RESOLVER:" not in last_response.upper():
            logging.info("Game ended due to reaching max questions.")
            final_prompt = "El detective ha agotado sus preguntas. Revela la historia completa."
            self.conversation.result = "Derrota"
        else:
            logging.info("Detective attempts to solve.")
            detective_solution = last_response.replace("RESOLVER:", "").strip()
            
            evaluation_prompt = (
                f"El detective ha propuesto la siguiente solución: '{detective_solution}'.\n"
                f"La verdadera historia es: '{self.conversation.full_solution}'.\n"
                "Evalúa si la solución del detective es CORRECTA o INCORRECTA. "
                "Responde únicamente con '🎉 ¡CORRECTO!' si es correcta, o '❌ INCORRECTO.' si es incorrecta. "
                "Luego, explica la historia completa."
            )
            
            evaluation_response = self.model1.generate_response(evaluation_prompt)
            
            if "🎉 ¡CORRECTO!" in evaluation_response:
                self.conversation.result = "Victoria"
            else:
                self.conversation.result = "Derrota"
            
            final_prompt = evaluation_response # Use the evaluation response directly


        start_time = time.time()
        final_story = self.model1.generate_response(final_prompt)
        response_time = time.time() - start_time

        msg = Message("model1", self.model1.model_name, "Story Master", final_story, response_time=response_time)
        self.conversation.add_message(msg)
        print_message(msg)

    def _save_conversation(self):
        self.saver.save(self.conversation, self.save_format)
