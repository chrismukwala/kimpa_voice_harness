"""Main window — 3-panel layout: file tree | editor | AI panel."""

from PyQt6.QtWidgets import (
    QMainWindow, QSplitter, QTreeView, QWidget, QVBoxLayout,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFileSystemModel

from ui.editor_panel import EditorPanel
from ui.ai_panel import AiPanel


class MainWindow(QMainWindow):
    def __init__(self, coordinator, parent=None):
        super().__init__(parent)
        self._coordinator = coordinator
        self.setWindowTitle("Voice Harness")
        self.resize(1400, 850)
        self.setStyleSheet("QMainWindow { background:#1e1e1e; }")

        # --- File tree (left) ---
        self._fs_model = QFileSystemModel()
        self._fs_model.setReadOnly(True)
        self._file_tree = QTreeView()
        self._file_tree.setModel(self._fs_model)
        self._file_tree.setHeaderHidden(True)
        # Hide Size, Type, Date columns — keep only Name.
        for col in (1, 2, 3):
            self._file_tree.hideColumn(col)
        self._file_tree.setStyleSheet(
            "QTreeView { background:#252526; color:#cccccc; border:none;"
            " font-family:Consolas; font-size:12px; }"
            "QTreeView::item:selected { background:#094771; }"
        )
        self._file_tree.doubleClicked.connect(self._on_file_double_click)

        # --- Editor (centre) ---
        self._editor = EditorPanel()

        # --- AI panel (right) ---
        self._ai_panel = AiPanel()

        # --- Splitter ---
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._file_tree)
        splitter.addWidget(self._editor)
        splitter.addWidget(self._ai_panel)
        splitter.setSizes([220, 700, 380])
        splitter.setStyleSheet("QSplitter::handle { background:#3c3c3c; width:2px; }")
        self.setCentralWidget(splitter)

        # --- Wire coordinator signals → UI ---
        coordinator.state_changed.connect(self._ai_panel.set_state)
        coordinator.transcription_ready.connect(self._ai_panel.append_transcription)
        coordinator.llm_response_ready.connect(self._ai_panel.append_response)
        coordinator.error_occurred.connect(
            lambda msg: self._ai_panel.append_response(f"⚠ Error: {msg}")
        )

        # --- Wire UI → coordinator ---
        self._ai_panel.text_submitted.connect(self._on_manual_query)
        self._ai_panel.pause_toggled.connect(self._on_pause_toggle)

        # --- Sync editor content to coordinator on text change ---
        self._editor._editor.textChanged.connect(self._sync_editor_context)

    # ------------------------------------------------------------------
    # File tree
    # ------------------------------------------------------------------
    def set_root_path(self, path: str):
        """Set the file tree root to a project directory."""
        root_idx = self._fs_model.setRootPath(path)
        self._file_tree.setRootIndex(root_idx)

    def _on_file_double_click(self, index):
        path = self._fs_model.filePath(index)
        if self._fs_model.isDir(index):
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError:
            return
        self._editor.set_file(path, content)
        self._coordinator.set_file_context(path, content)

    # ------------------------------------------------------------------
    # Manual query
    # ------------------------------------------------------------------
    def _on_manual_query(self, text: str):
        self._sync_editor_context()
        self._coordinator.submit_text(text)

    # ------------------------------------------------------------------
    # Pause / resume
    # ------------------------------------------------------------------
    def _on_pause_toggle(self, paused: bool):
        if paused:
            self._coordinator.pause_listening()
        else:
            self._coordinator.resume_listening()

    # ------------------------------------------------------------------
    # Keep coordinator's file context in sync with editor
    # ------------------------------------------------------------------
    def _sync_editor_context(self):
        path = self._editor.path
        content = self._editor.get_content()
        if path and path != "No file open":
            self._coordinator.set_file_context(path, content)
