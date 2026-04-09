"""AI panel — response display + voice status + manual input."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPlainTextEdit, QLineEdit, QPushButton,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont


class AiPanel(QWidget):
    """Right-side panel: voice status, AI response log, and manual text input."""

    text_submitted = pyqtSignal(str)       # user typed a manual query
    pause_toggled = pyqtSignal(bool)       # True = paused, False = resumed

    def __init__(self, parent=None):
        super().__init__(parent)
        self._paused = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # --- Status indicator ---
        self._status = QLabel("idle")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setFont(QFont("Consolas", 11))
        self._status.setStyleSheet(
            "background:#252526; color:#608b4e; padding:6px; border-radius:4px;"
        )
        layout.addWidget(self._status)

        # --- Response log ---
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setFont(QFont("Consolas", 11))
        self._log.setStyleSheet(
            "QPlainTextEdit { background:#1e1e1e; color:#d4d4d4; border:none; }"
        )
        self._log.setPlaceholderText("AI responses will appear here...")
        layout.addWidget(self._log, stretch=1)

        # --- Manual input ---
        input_row = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setPlaceholderText("Type a query (fallback for no mic)...")
        self._input.setFont(QFont("Consolas", 11))
        self._input.setStyleSheet(
            "QLineEdit { background:#252526; color:#d4d4d4; border:1px solid #3c3c3c;"
            " padding:4px 8px; border-radius:3px; }"
        )
        self._input.returnPressed.connect(self._on_submit)
        input_row.addWidget(self._input, stretch=1)

        send_btn = QPushButton("Send")
        send_btn.setStyleSheet(
            "QPushButton { background:#0e639c; color:white; padding:4px 12px;"
            " border-radius:3px; border:none; }"
            "QPushButton:hover { background:#1177bb; }"
        )
        send_btn.clicked.connect(self._on_submit)
        input_row.addWidget(send_btn)
        layout.addLayout(input_row)

        # --- Pause button ---
        self._pause_btn = QPushButton("Pause Listening")
        self._pause_btn.setCheckable(True)
        self._pause_btn.setStyleSheet(
            "QPushButton { background:#c24038; color:white; padding:6px 16px;"
            " font-weight:bold; border-radius:3px; border:none; }"
            "QPushButton:checked { background:#388c2c; }"
            "QPushButton:hover { opacity:0.9; }"
        )
        self._pause_btn.clicked.connect(self._on_pause_toggle)
        layout.addWidget(self._pause_btn)

    # ------------------------------------------------------------------
    # Public slots for coordinator signals
    # ------------------------------------------------------------------
    def set_state(self, state: str):
        """Update the status label.  state: idle | listening | processing | speaking."""
        colors = {
            "idle": "#608b4e",
            "listening": "#4ec9b0",
            "processing": "#dcdcaa",
            "speaking": "#ce9178",
        }
        self._status.setText(state.capitalize())
        self._status.setStyleSheet(
            f"background:#252526; color:{colors.get(state, '#d4d4d4')};"
            " padding:6px; border-radius:4px;"
        )

    def append_response(self, text: str):
        """Append an LLM response to the log."""
        self._log.appendPlainText(f"\n{'─' * 40}\n{text}\n")

    def append_transcription(self, text: str):
        """Show what the user said."""
        self._log.appendPlainText(f"🎤 You: {text}")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _on_submit(self):
        text = self._input.text().strip()
        if text:
            self._input.clear()
            self.text_submitted.emit(text)

    def _on_pause_toggle(self):
        self._paused = self._pause_btn.isChecked()
        self._pause_btn.setText("Resume Listening" if self._paused else "Pause Listening")
        self.pause_toggled.emit(self._paused)
