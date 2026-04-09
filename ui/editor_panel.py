"""Editor panel — QPlainTextEdit placeholder (Phase 1).

Replaced by Monaco QWebEngineView in Phase 2b.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit, QLabel
from PyQt6.QtGui import QFont


class EditorPanel(QWidget):
    """Simple code editor placeholder using QPlainTextEdit."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._path_label = QLabel("No file open")
        self._path_label.setStyleSheet(
            "background:#252526; color:#9cdcfe; font-family:Consolas,monospace;"
            " font-size:11px; padding:4px 8px;"
        )
        layout.addWidget(self._path_label)

        self._editor = QPlainTextEdit()
        self._editor.setReadOnly(False)
        self._editor.setFont(QFont("Consolas", 12))
        self._editor.setStyleSheet(
            "QPlainTextEdit { background:#1e1e1e; color:#d4d4d4;"
            " selection-background-color:#264f78; border:none; }"
        )
        self._editor.setPlaceholderText("Open a file or paste code here...")
        layout.addWidget(self._editor)

    @property
    def path(self) -> str:
        return self._path_label.text()

    def set_file(self, path: str, content: str):
        """Load a file's content into the editor."""
        self._path_label.setText(path)
        self._editor.setPlainText(content)

    def get_content(self) -> str:
        return self._editor.toPlainText()
