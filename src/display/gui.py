import threading
import queue
import customtkinter as ctk
from datetime import datetime
from ..game.interfaces import GameObserver
from ..game.events import GameEvent, EventType
from ..game.enums import GameState
# Importamos factoría para el launcher
from ..game.providers_factory import get_provider
from ..game.orchestrator import GameOrchestrator
from .terminal import TerminalObserver

# Configuración de apariencia
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class BlackStoryGUI(ctk.CTk):
    def __init__(self, orchestrator=None, human_moderator=False):
        super().__init__()
        
        self.title("Black Stories - AI Launcher")
        self.geometry("1400x800")
        
        # Container principal para cambiar de views
        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True)
        
        # State
        self.orchestrator = orchestrator
        self.human_moderator_flag = human_moderator

        # Si ya nos pasan un orquestador (modo CLI --ui), vamos directo al juego
        if self.orchestrator:
            self.show_game_frame(self.orchestrator, self.human_moderator_flag)
        else:
            self.show_launcher_frame()

    def show_launcher_frame(self):
        for widget in self.container.winfo_children():
            widget.destroy()
        
        launcher = LauncherFrame(self.container, self)
        launcher.pack(fill="both", expand=True)

    def show_game_frame(self, orchestrator, human_moderator):
        for widget in self.container.winfo_children():
            widget.destroy()
            
        game_ui = GameFrame(self.container, orchestrator, human_moderator, self.quit_game)
        game_ui.pack(fill="both", expand=True)
        game_ui.start_game_thread()
        
    def quit_game(self):
        # Volver al launcher o cerrar?
        # Por simplicidad, volvemos al launcher
        if self.orchestrator:
             # Si vino de CLI, cerrar app
             self.destroy()
        else:
             self.show_launcher_frame()


class LauncherFrame(ctk.CTkFrame):
    def __init__(self, master, app_controller):
        super().__init__(master)
        self.app = app_controller
        
        # --- HEADER ---
        lbl_title = ctk.CTkLabel(self, text="🕵️ Black Stories AI - Launcher", font=("Roboto", 32, "bold"))
        lbl_title.pack(pady=(40, 20))
        
        # --- FORM CONTAINER ---
        self.form_frame = ctk.CTkFrame(self)
        self.form_frame.pack(padx=50, pady=20, fill="both", expand=True)
        
        self.form_frame.grid_columnconfigure(0, weight=1)
        self.form_frame.grid_columnconfigure(1, weight=1)
        
        # MODEL 1 (Story Master)
        lbl_m1 = ctk.CTkLabel(self.form_frame, text="🎭 Story Master (Modelo 1)", font=("Roboto", 16, "bold"))
        lbl_m1.grid(row=0, column=0, padx=20, pady=(20,10), sticky="w")
        
        self.entry_m1_name = ctk.CTkEntry(self.form_frame, placeholder_text="Nombre Modelo (ej: gemini-2.0-flash-exp)")
        self.entry_m1_name.insert(0, "gemini-2.0-flash-exp")
        self.entry_m1_name.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        self.opt_m1_provider = ctk.CTkOptionMenu(self.form_frame, values=["gemini", "ollama"])
        self.opt_m1_provider.set("gemini")
        self.opt_m1_provider.grid(row=2, column=0, padx=20, pady=10, sticky="w")

        # MODEL 2 (Detective)
        lbl_m2 = ctk.CTkLabel(self.form_frame, text="🔍 Detective (Modelo 2)", font=("Roboto", 16, "bold"))
        lbl_m2.grid(row=0, column=1, padx=20, pady=(20,10), sticky="w")
        
        self.entry_m2_name = ctk.CTkEntry(self.form_frame, placeholder_text="Nombre Modelo (ej: gemini-2.0-flash-exp)")
        self.entry_m2_name.insert(0, "gemini-2.0-flash-exp")
        self.entry_m2_name.grid(row=1, column=1, padx=20, pady=10, sticky="ew")
        
        self.opt_m2_provider = ctk.CTkOptionMenu(self.form_frame, values=["gemini", "ollama"])
        self.opt_m2_provider.set("gemini")
        self.opt_m2_provider.grid(row=2, column=1, padx=20, pady=10, sticky="w")

        # SETTINGS
        lbl_settings = ctk.CTkLabel(self.form_frame, text="⚙️ Configuración", font=("Roboto", 16, "bold"))
        lbl_settings.grid(row=3, column=0, padx=20, pady=(30,10), sticky="w")
        
        self.entry_max_q = ctk.CTkEntry(self.form_frame, placeholder_text="Max Preguntas")
        self.entry_max_q.insert(0, "10")
        self.entry_max_q.grid(row=4, column=0, padx=20, pady=10, sticky="w")
        
        self.chk_moderator = ctk.CTkCheckBox(self.form_frame, text="Habilitar Moderador Humano")
        self.chk_moderator.grid(row=4, column=1, padx=20, pady=10, sticky="w")
        
        # START BUTTON
        self.btn_start = ctk.CTkButton(self, text="🚀 INICIAR PARTIDA", font=("Roboto", 20, "bold"), height=50, command=self.start_game)
        self.btn_start.pack(pady=40, padx=100, fill="x")
        
        self.lbl_error = ctk.CTkLabel(self, text="", text_color="red")
        self.lbl_error.pack(pady=5)

    def start_game(self):
        try:
            m1_name = self.entry_m1_name.get()
            m2_name = self.entry_m2_name.get()
            p1_prov = self.opt_m1_provider.get()
            p2_prov = self.opt_m2_provider.get()
            max_q = int(self.entry_max_q.get())
            human_mod = self.chk_moderator.get() == 1
            
            # Instanciar proveedores
            prov1_instance = get_provider(p1_prov, m1_name)
            prov2_instance = get_provider(p2_prov, m2_name)
            
            # Crear orquestador
            game = GameOrchestrator(
                model1=prov1_instance,
                model2=prov2_instance,
                max_questions=max_q,
                no_pause=False, # GUI needs pause for step-by-step control
                output_dir="./conversations",
                save_format="md"
            )
            
            # Conectar observador terminal para logs de consola tambien
            term = TerminalObserver()
            game.subscribe(term)
            
            # Cambiar a vista de juego
            self.app.show_game_frame(game, human_mod)

        except Exception as e:
            self.lbl_error.configure(text=f"Error al iniciar: {str(e)}")


class GameFrame(ctk.CTkFrame, GameObserver):
    def __init__(self, master, orchestrator, human_moderator, on_quit_callback):
        ctk.CTkFrame.__init__(self, master) # Explicit super call for multi-inheritance safety
        
        self.orchestrator = orchestrator
        self.human_moderator = human_moderator
        self.on_quit_callback = on_quit_callback
        
        self.orchestrator.subscribe(self)
        self.event_queue = queue.Queue()
        
        # Grid Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Panels
        self.panel_detective = ctk.CTkFrame(self, corner_radius=10)
        self.panel_detective.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self._setup_detective_panel()
        
        self.panel_narrative = ctk.CTkFrame(self, corner_radius=10)
        self.panel_narrative.grid(row=0, column=1, sticky="nsew", padx=5, pady=10)
        self._setup_narrative_panel()
        
        self.panel_moderator = ctk.CTkFrame(self, corner_radius=10)
        self.panel_moderator.grid(row=0, column=2, sticky="nsew", padx=10, pady=10)
        self._setup_moderator_panel()
        
        # Back Button
        self.btn_back = ctk.CTkButton(self.panel_detective, text="⬅️ Volver / Salir", command=self.on_quit, fg_color="#555")
        self.btn_back.pack(side="bottom", pady=10)

        # Loop
        self.after(100, self._check_queue)
        
        # Variables
        self.questions_count = 0

    def start_game_thread(self):
        thread = threading.Thread(target=self.orchestrator.play, daemon=True)
        thread.start()

    def on_quit(self):
        # TODO: Implement cleaner shutdown in orchestrator
        self.on_quit_callback()
    
    def on_next_question(self):
        """Permite que el juego continúe a la siguiente pregunta."""
        self.orchestrator.continue_game()

    # --- SETUP METHODS (COPIED/REFACTORED FROM ORIGINAL GUI) ---
    def _setup_detective_panel(self):
        lbl = ctk.CTkLabel(self.panel_detective, text="🕵️ Detective Log", font=("Roboto", 20, "bold"))
        lbl.pack(pady=10)
        self.detective_log = ctk.CTkTextbox(self.panel_detective, width=300, font=("Consolas", 12))
        self.detective_log.pack(fill="both", expand=True, padx=10, pady=5)
        self.detective_log.configure(state="disabled")
        self.lbl_status = ctk.CTkLabel(self.panel_detective, text="Estado: Esperando...", text_color="gray")
        self.lbl_status.pack(pady=5)
        self.lbl_counters = ctk.CTkLabel(self.panel_detective, text="Preguntas: 0 / ?")
        self.lbl_counters.pack(pady=5)
        
        # Botón para continuar al siguiente paso
        self.btn_next = ctk.CTkButton(self.panel_detective, text="▶️ Siguiente Pregunta", command=self.on_next_question, fg_color="#2ecc71", height=40)
        self.btn_next.pack(pady=10, padx=10, fill="x")
    
    def _setup_narrative_panel(self):
        lbl = ctk.CTkLabel(self.panel_narrative, text="📖 Historia Negra", font=("Roboto", 20, "bold"))
        lbl.pack(pady=10)
        self.story_text = ctk.CTkTextbox(self.panel_narrative, height=150, font=("Georgia", 14), wrap="word")
        self.story_text.pack(fill="x", padx=10, pady=5)
        self.story_text.insert("0.0", "Esperando historia...")
        self.story_text.configure(state="disabled")
        self.interaction_view = ctk.CTkTextbox(self.panel_narrative, font=("Arial", 16), wrap="word")
        self.interaction_view.configure(state="disabled")
        self.interaction_view.pack(fill="both", expand=True, padx=10, pady=10)

    def _setup_moderator_panel(self):
        title = "🧑‍⚖️ Moderador" if self.human_moderator else "👁️ Espectador"
        lbl = ctk.CTkLabel(self.panel_moderator, text=title, font=("Roboto", 20, "bold"))
        lbl.pack(pady=10)
        self.lbl_solution_title = ctk.CTkLabel(self.panel_moderator, text="🔐 Solución (Secreto):", anchor="w")
        self.lbl_solution_title.pack(fill="x", padx=10)
        self.secret_solution = ctk.CTkTextbox(self.panel_moderator, height=200, font=("Consolas", 11), wrap="word", text_color="#ffcc00")
        self.secret_solution.pack(fill="x", padx=10, pady=5)
        self.secret_solution.configure(state="disabled")
        
        # Controls
        self.frame_controls = ctk.CTkFrame(self.panel_moderator)
        self.frame_controls.pack(fill="both", expand=True, padx=10, pady=10)
        
        if self.human_moderator:
            ctk.CTkButton(self.frame_controls, text="💡 Forzar Pista", command=lambda: self._intervene("hint"), fg_color="#e67e22").pack(fill="x", pady=5)
            ctk.CTkButton(self.frame_controls, text="⚠️ Advertencia", command=lambda: self._intervene("warn"), fg_color="#f39c12").pack(fill="x", pady=5)
            ctk.CTkButton(self.frame_controls, text="🛑 Finalizar", command=lambda: self._intervene("force_end"), fg_color="#c0392b").pack(fill="x", pady=5)
        else:
            ctk.CTkLabel(self.frame_controls, text="Solo lectura", text_color="gray").pack()

    def _intervene(self, action):
        data = {}
        if action == "hint":
            # Auto-generate hint via AI instead of manual input
            self.orchestrator.process_intervention("hint", data)
        elif action == "warn":
            # Manual warning still uses input dialog
            title = "Escribir Advertencia"
            dialog = ctk.CTkInputDialog(text=f"Mensaje:", title=title)
            text = dialog.get_input()
            if not text: return
            data["text"] = text
            self.orchestrator.process_intervention(action, data)
        else:
            # Other actions (force_end, etc.)
            self.orchestrator.process_intervention(action, data)

    def on_event(self, event: GameEvent):
        self.event_queue.put(event)

    def _check_queue(self):
        try:
            while True:
                event = self.event_queue.get_nowait()
                self._handle_event(event)
        except queue.Empty:
            pass
        finally:
            self.after(100, self._check_queue)
            
    def _handle_event(self, event):
        # Reutilizamos logica de evento anterior, simplificada
        if event.type == EventType.CAMBIO_ESTADO:
             self.lbl_status.configure(text=f"Estado: {event.payload.get('state').name}")
        elif event.type == EventType.NEW_STORY:
             self.story_text.configure(state="normal")
             self.story_text.delete("0.0", "end")
             self.story_text.insert("0.0", event.payload.get("story_situation"))
             self.story_text.configure(state="disabled")
             self.secret_solution.configure(state="normal")
             self.secret_solution.delete("0.0", "end")
             self.secret_solution.insert("0.0", event.payload.get("full_solution"))
             self.secret_solution.configure(state="disabled")
        elif event.type == EventType.PREGUNTA_DETECTIVE:
             self.interaction_view.configure(state="normal")
             self.interaction_view.insert("end", f"\n❓ DETECTIVE:\n{event.payload.get('message').content}\n")
             self.interaction_view.see("end")
             self.interaction_view.configure(state="disabled")
             q_asked = event.payload.get("questions_asked")
             self.lbl_counters.configure(text=f"Preguntas: {q_asked} / 10")
        elif event.type == EventType.RESPUESTA_MAESTRO:
             self.interaction_view.configure(state="normal")
             self.interaction_view.insert("end", f"\n🎭 MAESTRO:\n{event.payload.get('message').content}\n{'-'*40}\n")
             self.interaction_view.see("end")
             self.interaction_view.configure(state="disabled")
        elif event.type == EventType.FIN_JUEGO:
             self.interaction_view.configure(state="normal")
             self.interaction_view.insert("end", f"\n🏁 {event.payload.get('result')}\n")
             self.interaction_view.see("end")
             self.interaction_view.configure(state="disabled")
        elif event.type == EventType.LOG:
             self.detective_log.configure(state="normal")
             self.detective_log.insert("end", f"> {event.message}\n")
             self.detective_log.see("end")
             self.detective_log.configure(state="disabled")
