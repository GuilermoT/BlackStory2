import time
import logging
from ..providers.base import BaseProvider
from ..storage.models import Conversation, Message
from ..storage.saver import ConversationSaver
from ..display.ui import print_message, wait_for_enter
from .prompts import STORY_MASTER_PROMPT, DETECTIVE_PROMPT

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
            max_questions=self.max_questions
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
        story_and_rules = self.model1.generate_response(prompt)
        response_time = time.time() - start_time
        
        msg = Message("model1", self.model1.model_name, "Story Master", story_and_rules, response_time=response_time)
        self.conversation.add_message(msg)
        print_message(msg)
        wait_for_enter(self.no_pause)

    def _interrogation_loop(self):
        questions_asked = 0
        while questions_asked < self.max_questions:
            # Model 2 asks a question
            story_situation = self.conversation.messages[0].content
            prompt = DETECTIVE_PROMPT.format(
                story_situation=story_situation,
                max_questions=self.max_questions,
                questions_left=self.max_questions - questions_asked
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
            answer = self.model1.generate_response(f"La pregunta es: '{question}'. Responde solo con SÍ, NO o NO ES RELEVANTE.")
            response_time = time.time() - start_time

            msg = Message("model1", self.model1.model_name, "Story Master", answer, response_time=response_time)
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
            final_prompt = f"El detective dice: '{last_response}'. Evalúa si es correcto y revela la historia."
            # A simple check for now, a more robust evaluation could be implemented
            if "correcto" in self.model1.generate_response(final_prompt).lower():
                 self.conversation.result = "Victoria"
            else:
                 self.conversation.result = "Derrota"


        start_time = time.time()
        final_story = self.model1.generate_response(final_prompt)
        response_time = time.time() - start_time

        msg = Message("model1", self.model1.model_name, "Story Master", final_story, response_time=response_time)
        self.conversation.add_message(msg)
        print_message(msg)

    def _save_conversation(self):
        self.saver.save(self.conversation, self.save_format)
