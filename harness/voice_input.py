"""Voice input — thin adapter around RealtimeSTT."""

import threading
from typing import Callable, Optional


class VoiceInput:
    """Thin wrapper: start()/stop()/on_text(cb).

    Nothing else in the project imports RealtimeSTT directly.
    If RealtimeSTT needs replacing, only this file changes.
    """

    def __init__(self):
        self._callback: Optional[Callable[[str], None]] = None
        self._recorder = None
        self._running = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def on_text(self, callback: Callable[[str], None]):
        """Register callback invoked with each final transcription."""
        self._callback = callback

    def start(self):
        """Begin listening.  Spawns RealtimeSTT in its own thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop listening and shut down the recorder."""
        self._running = False
        if self._recorder is not None:
            try:
                self._recorder.stop()
            except Exception:
                pass
            self._recorder = None

    def pause(self):
        """Temporarily mute mic input (for video calls)."""
        if self._recorder is not None:
            try:
                self._recorder.stop()
            except Exception:
                pass

    def resume(self):
        """Resume after pause."""
        if self._running and self._recorder is not None:
            try:
                self._recorder.start()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _listen_loop(self):
        from RealtimeSTT import AudioToTextRecorder

        self._recorder = AudioToTextRecorder(
            model="large-v3",
            compute_type="int8_float16",
            language="en",
            wake_words="hey_jarvis",
            min_length=3,
            min_gap_between_recordings=0,
            spinner=False,
            use_microphone=True,
            silero_sensitivity=0.4,
            post_speech_silence_duration=1.2,
        )
        self._recorder.start()
        while self._running:
            text = self._recorder.text()
            if text and self._callback:
                self._callback(text.strip())
