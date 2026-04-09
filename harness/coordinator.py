"""Coordinator — queue pipeline: STT → context_assembler → LLM → response_splitter → TTS."""

import queue
import threading
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal

from harness.voice_input import VoiceInput
from harness import code_llm
from harness import tts as tts_mod


class Coordinator(QObject):
    """Central pipeline connecting voice input → LLM → TTS → UI.

    Signals keep the UI updated from background threads.
    """

    # Signals — UI connects to these.
    state_changed = pyqtSignal(str)         # "idle" | "listening" | "processing" | "speaking"
    transcription_ready = pyqtSignal(str)   # final STT text
    llm_response_ready = pyqtSignal(str)    # full LLM response text
    prose_ready = pyqtSignal(str)           # prose portion (read aloud)
    tts_started = pyqtSignal()
    tts_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._voice = VoiceInput()
        self._voice.on_text(self._on_stt_text)

        # Pipeline queue — each item is a message dict.
        self._queue: queue.Queue = queue.Queue()
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False

        # Current file context (set by editor panel when user opens a file).
        self._current_file_content: Optional[str] = None
        self._current_file_path: Optional[str] = None

        # Repo map stub — filled in Phase 3b.
        self._repo_map: Optional[str] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self):
        """Start the voice listener and the pipeline worker."""
        self._running = True
        self._worker_thread = threading.Thread(target=self._pipeline_loop, daemon=True)
        self._worker_thread.start()
        self._voice.start()
        self.state_changed.emit("listening")

    def stop(self):
        """Shut everything down."""
        self._running = False
        self._voice.stop()
        self._queue.put(None)  # sentinel to unblock worker

    def pause_listening(self):
        self._voice.pause()
        self.state_changed.emit("idle")

    def resume_listening(self):
        self._voice.resume()
        self.state_changed.emit("listening")

    # ------------------------------------------------------------------
    # Context management
    # ------------------------------------------------------------------
    def set_file_context(self, path: str, content: str):
        """Called by the editor panel whenever the active file changes."""
        self._current_file_path = path
        self._current_file_content = content

    def clear_file_context(self):
        self._current_file_path = None
        self._current_file_content = None

    # ------------------------------------------------------------------
    # Manual text input (fallback for no mic)
    # ------------------------------------------------------------------
    def submit_text(self, text: str):
        """Enqueue a query typed in the manual input box."""
        self._enqueue(text)

    # ------------------------------------------------------------------
    # Internal: from STT callback → queue
    # ------------------------------------------------------------------
    def _on_stt_text(self, text: str):
        self.transcription_ready.emit(text)
        self._enqueue(text)

    def _enqueue(self, query: str):
        msg = {
            "query": query,
            "context": self._current_file_content,
            "repo_map": self._repo_map,
        }
        self._queue.put(msg)

    # ------------------------------------------------------------------
    # Pipeline worker (runs in background thread)
    # ------------------------------------------------------------------
    def _pipeline_loop(self):
        while self._running:
            msg = self._queue.get()
            if msg is None:
                break
            try:
                self._process_message(msg)
            except Exception as exc:
                self.error_occurred.emit(str(exc))
                self.state_changed.emit("listening")

    def _process_message(self, msg: dict):
        self.state_changed.emit("processing")

        # --- context_assembler stub (pass-through for Phase 1) ---
        query = msg["query"]
        context = msg["context"]
        repo_map = msg["repo_map"]

        # --- LLM ---
        response = code_llm.chat(query, context=context, repo_map=repo_map)
        self.llm_response_ready.emit(response)

        # --- response_splitter stub (pass-through for Phase 1) ---
        prose = code_llm.extract_prose(response)
        self.prose_ready.emit(prose)

        # --- TTS ---
        if prose:
            self.state_changed.emit("speaking")
            self.tts_started.emit()
            try:
                chunks = tts_mod.speak(prose)
                for _sentence, wav_bytes in chunks:
                    if not self._running:
                        break
                    tts_mod.play_wav_bytes(wav_bytes)
            finally:
                self.tts_finished.emit()

        self.state_changed.emit("listening")
