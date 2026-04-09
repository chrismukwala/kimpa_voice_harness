"""Voice Harness — entry point."""

import os
import sys

# Env vars that must be set before any Qt / torch imports.
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--in-process-gpu"
os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
os.environ.setdefault("OLLAMA_HOST", "127.0.0.1")

from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
from harness.coordinator import Coordinator


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Voice Harness")

    coordinator = Coordinator()
    window = MainWindow(coordinator)
    window.show()

    coordinator.start()
    code = app.exec()

    coordinator.stop()
    sys.exit(code)


if __name__ == "__main__":
    main()
