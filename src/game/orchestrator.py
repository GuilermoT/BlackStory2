import time
import logging
import threading
from typing import List, Optional
from rich.console import Console # Kept for fail-safe or direct logging if strictly needed
from ..providers.base import BaseProvider
from ..storage.models import Conversation, Message
from ..storage.saver import ConversationSaver
# Removed wait_for_enter import - using _wait_for_continue instead
from .prompts import STORY_MASTER_PROMPT, DETECTIVE_PROMPT
from .interfaces import GameObserver
from .events import GameEvent, EventType
from .enums import GameState

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
            full_solution=""
        )
        
        self._observers: List[GameObserver] = []
        self._state: GameState = GameState.EN_PROGRESO
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()  # Para control paso a paso
        self._pause_event.set()  # Inicialmente no pausado
        self._intervention_queue = [] # Para intervenciones del moderador

    def subscribe(self, observer: GameObserver):
        """Añade un observador."""
        self._observers.append(observer)

    def _notify(self, type: EventType, message: str = None, payload: dict = None):
        """Notifica un evento a todos los observadores."""
        event = GameEvent(type=type, message=message, payload=payload or {})
        for observer in self._observers:
            try:
                observer.on_event(event)
            except Exception as e:
                logging.error(f"Error notificando a observador {observer}: {e}")

    def _set_state(self, new_state: GameState):
        self._state = new_state
        self._notify(EventType.CAMBIO_ESTADO, payload={"state": new_state})

    def continue_game(self):
        """Permite que el juego continúe al siguiente paso."""
        self._pause_event.set()
    
    def _wait_for_continue(self):
        """Espera hasta que se llame continue_game() o se detenga el juego."""
        if not self.no_pause:
            self._pause_event.clear()
            self._notify(EventType.LOG, message="⏸️ Esperando continuar...")
            while not self._pause_event.is_set() and not self._stop_event.is_set():
                time.sleep(0.1)
    
    def process_intervention(self, action: str, data: dict = None):
        """
        Método para recibir acciones del moderador humano.
        Puede ser llamado desde otro hilo (UI).
        """
        logging.info(f"Intervención recibida: {action}")
        self._notify(EventType.INTERVENCION, message=f"Intervención: {action}", payload=data or {})
        
        if action == "force_end":
            self._stop_event.set()
            
        elif action == "hint" or action == "warn":
            text = data.get("text", "")
            if text:
                # Crear mensaje de sistema/moderador
                role_title = "Moderador (Pista)" if action == "hint" else "Moderador (Advertencia)"
                emoji = "💡" if action == "hint" else "⚠️"
                formatted_content = f"{emoji} {role_title}: {text}"
                
                # Lo añadimos a la conversación como un mensaje especial del Story Master para que quede registro
                # o como un mensaje de sistema. Usaremos Story Master para simplificar, pero marcándolo.
                msg = Message("human_mod", "Human", "Moderator", formatted_content)
                self.conversation.add_message(msg)
                
                # Notificar para que salga en la UI
                self._notify(EventType.RESPUESTA_MAESTRO, payload={"message": msg}) 

    def play(self):
        """
        Método principal de ejecución. 
        Ahora diseñado para ser thread-safe en cuanto a la notificación de eventos.
        """
        try:
            logging.info("Starting a new game.")
            self._notify(EventType.INICIO_JUEGO)
            
            # Fase 1: Inicio
            if self._stop_event.is_set(): return
            self._start_game()

            # Fase 2: Interrogatorio
            if self._stop_event.is_set(): return
            self._interrogation_loop()

            # Fase 3: Resolución (si no se detuvo antes)
            if not self._stop_event.is_set() and self._state != GameState.RESUELTO:
                self._resolve_game()

             # Fase 4: Guardado
            self._save_conversation()
            
            # Asegurar estado final
            if self._state != GameState.RESUELTO:
                 self._set_state(GameState.RESUELTO)

        except Exception as e:
            logging.error(f"Error crítico en el juego: {e}", exc_info=True)
            self._notify(EventType.ERROR, message=str(e))
            self._set_state(GameState.ERROR)

    def _start_game(self):
        prompt = STORY_MASTER_PROMPT.format(max_questions=self.max_questions)
        start_time = time.time()
        
        # Notificar estado
        self._notify(EventType.LOG, message="Generando historia...")
        
        raw_story_response = self.model1.generate_response(prompt)
        response_time = time.time() - start_time
        
        # Debug logging
        logging.info(f"Raw story response length: {len(raw_story_response)}")
        logging.debug(f"Raw story response: {raw_story_response[:500]}...")  # First 500 chars
        
        story_situation = ""
        full_solution = ""
        
        # Intentar extraer con diferentes variaciones
        response_upper = raw_story_response.upper()
        
        if "SITUACIÓN:" in response_upper and "SOLUCIÓN:" in response_upper:
            # Encontrar las posiciones case-insensitive
            sit_idx = response_upper.find("SITUACIÓN:")
            sol_idx = response_upper.find("SOLUCIÓN:")
            
            # Extraer usando las posiciones encontradas
            story_situation = raw_story_response[sit_idx+10:sol_idx].strip()
            full_solution = raw_story_response[sol_idx+9:].strip()
            logging.info("Extracted using SITUACIÓN/SOLUCIÓN format")
        elif "SITUACION:" in response_upper and "SOLUCION:" in response_upper:
            # Sin tilde
            sit_idx = response_upper.find("SITUACION:")
            sol_idx = response_upper.find("SOLUCION:")
            
            story_situation = raw_story_response[sit_idx+10:sol_idx].strip()
            full_solution = raw_story_response[sol_idx+9:].strip()
            logging.info("Extracted using SITUACION/SOLUCION format (no accents)")
        else:
            # Fallback: intentar dividir por líneas y buscar patrones
            lines = raw_story_response.split('\n')
            in_solution = False
            situation_lines = []
            solution_lines = []
            
            for line in lines:
                line_upper = line.upper()
                if "SITUACIÓN:" in line_upper or "SITUACION:" in line_upper:
                    # Extraer lo que viene después de SITUACIÓN:
                    if ":" in line:
                        situation_lines.append(line.split(":", 1)[1].strip())
                    in_solution = False
                elif "SOLUCIÓN:" in line_upper or "SOLUCION:" in line_upper:
                    # Extraer lo que viene después de SOLUCIÓN:
                    if ":" in line:
                        solution_lines.append(line.split(":", 1)[1].strip())
                    in_solution = True
                elif in_solution and line.strip():
                    solution_lines.append(line.strip())
                elif not in_solution and line.strip() and not situation_lines:
                    situation_lines.append(line.strip())
            
            if situation_lines:
                story_situation = " ".join(situation_lines)
            if solution_lines:
                full_solution = " ".join(solution_lines)
            
            logging.info(f"Used fallback extraction. Found {len(situation_lines)} situation lines, {len(solution_lines)} solution lines")
            
            # Si aún no tenemos nada, usar toda la respuesta como situación
            if not story_situation:
                logging.warning("Story Master did not follow format. Using full response as situation.")
                story_situation = raw_story_response.strip()
                full_solution = "No se pudo extraer la solución completa. Por favor, revisa el formato de respuesta del modelo."

        logging.info(f"Final solution length: {len(full_solution)}")
        logging.debug(f"Final solution: {full_solution[:200]}...")  # First 200 chars
        
        self.conversation.full_solution = full_solution
        
        display_content = f"🎭 HISTORIA:\n\n{story_situation}\n\n📋 REGLAS:\n\n- Solo puedes hacer preguntas que se respondan con SÍ, NO o NO ES RELEVANTE\n- Cuando creas tener la solución completa, di \"RESOLVER:\" seguido de tu explicación\n- Tienes un máximo de {self.max_questions} preguntas\n\n¡Empieza a preguntar!"

        msg = Message("model1", self.model1.model_name, "Story Master", display_content, response_time=response_time)
        self.conversation.add_message(msg)
        
        # Notificar evento
        self._notify(EventType.NEW_STORY, payload={
            "message": msg,
            "story_situation": story_situation,
            "full_solution": full_solution
        })

        # Story displayed, wait for user to continue
        self._wait_for_continue()

    def _format_history(self):
        history = []
        for msg in self.conversation.messages[1:]:
            role = "Detective" if msg.role == "Detective" else "Respuesta"
            history.append(f"- {role}: {msg.content.strip()}")
        return "\n".join(history) if history else "Aún no hay preguntas."

    def _interrogation_loop(self):
        questions_asked = 0
        score_feedback = "Esta es tu primera pregunta. ¡Analiza bien la situación!"
        
        while questions_asked < self.max_questions and not self._stop_event.is_set():
            # Check interaction queue or manual pause here if needed
            self._set_state(GameState.EN_PROGRESO)

            story_situation = self.conversation.messages[0].content
            conversation_history = self._format_history()

            force_solve_instructions = ""
            if questions_asked >= 5:
                force_solve_instructions = "YA HAS HECHO 5 PREGUNTAS. DEBES INTENTAR RESOLVER LA HISTORIA AHORA. USA 'RESOLVER:'."
                self._set_state(GameState.CERCA) # Indicativo visual opcional

            prompt = DETECTIVE_PROMPT.format(
                story_situation=story_situation,
                conversation_history=conversation_history,
                max_questions=self.max_questions,
                questions_left=self.max_questions - questions_asked,
                score_feedback=score_feedback,
                force_solve_instructions=force_solve_instructions
            )
            
            self._notify(EventType.LOG, message="Detective pensando...")
            start_time = time.time()
            question = self.model2.generate_response(prompt)
            response_time = time.time() - start_time
            
            questions_asked += 1
            msg = Message("model2", self.model2.model_name, "Detective", question, response_time=response_time)
            self.conversation.add_message(msg)
            
            self._notify(EventType.PREGUNTA_DETECTIVE, payload={
                "message": msg,
                "questions_asked": questions_asked,
                "max_questions": self.max_questions
            })
            
            # Question asked, wait for user to continue
            self._wait_for_continue()

            if "RESOLVER:" in question.upper():
                break
            
            # --- Respuesta del Maestro ---
            self._notify(EventType.LOG, message="Maestro evaluando...")
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

            self._notify(EventType.RESPUESTA_MAESTRO, payload={"message": msg})
            
            # Esperar confirmación para continuar (GUI mode)
            self._wait_for_continue()

        self.conversation.questions_used = questions_asked

    def _resolve_game(self):
        last_response = self.conversation.messages[-1].content
        final_story = ""
        response_time = 0

        self._notify(EventType.LOG, message="Resolviendo partida...")

        if "RESOLVER:" not in last_response.upper():
            logging.info("Game ended due to reaching max questions.")
            final_story = f"Has agotado tus preguntas. La solución era:\n\n{self.conversation.full_solution}"
            self.conversation.result = "Derrota"
        else:
            logging.info("Detective attempts to solve.")
            detective_solution = last_response.replace("RESOLVER:", "").strip()
            
            start_time = time.time()
            evaluation_prompt = (
                f"El detective ha propuesto la siguiente solución: '{detective_solution}'.\n"
                f"La verdadera historia es: '{self.conversation.full_solution}'.\n"
                "Evalúa si la solución del detective es CORRECTA o INCORRECTA. "
                "Responde únicamente con '🎉 ¡CORRECTO!' si es correcta, o '❌ INCORRECTO.' si es incorrecta. "
                "Luego, en una nueva línea, revela la historia completa."
            )
            final_story = self.model1.generate_response(evaluation_prompt)
            response_time = time.time() - start_time
            
            if "🎉 ¡CORRECTO!" in final_story:
                self.conversation.result = "Victoria"
            else:
                self.conversation.result = "Derrota"

        self._set_state(GameState.RESUELTO)
        
        msg = Message("model1", self.model1.model_name, "Story Master", final_story, response_time=response_time)
        self.conversation.add_message(msg)
        
        self._notify(EventType.FIN_JUEGO, payload={
            "result": self.conversation.result,
            "message_obj": msg,
            "final_story": final_story
        })

    def _save_conversation(self):
        self._notify(EventType.LOG, message="Guardando partida...")
        self.saver.save(self.conversation, self.save_format)
