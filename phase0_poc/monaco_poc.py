"""
Phase 0 — Monaco POC Gate
=========================
Binary pass/fail test. Run this BEFORE writing any voice/LLM code.

Tests:
  1. QWebEngineView loads Monaco via custom app:// URL scheme (NOT file://)
  2. QWebChannel bridge round-trips: Python injects text → reads it back
  3. Monaco AMD loader works (no silent Web Worker failures)
  4. QWebChannel js object available before monaco.editor.create()

Pass: "ROUND-TRIP OK" printed to console + shown in window.
Fail: timeout / JS error / empty round-trip result.

If this script fails, editor_panel.py uses QPlainTextEdit throughout.
Monaco phases (2b, 3a-diff) are dropped. See plan Phase 0 for details.

Usage:
    python phase0_poc/monaco_poc.py
"""

import os
import sys
import json
import pathlib

# Dual-GPU fix for Razer Blade (Intel iGPU + RTX 4080 Optimus)
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import (
    QWebEngineProfile,
    QWebEngineUrlSchemeHandler,
    QWebEngineUrlRequestJob,
    QWebEngineUrlScheme,
    QWebEngineSettings,
)
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import QObject, pyqtSlot, pyqtSignal, QTimer, QUrl, QBuffer, QIODevice
from PyQt6.QtGui import QColor


# ---------------------------------------------------------------------------
# Register the app:// custom URL scheme BEFORE QApplication is created.
# This is mandatory — schemes must be registered at startup.
# ---------------------------------------------------------------------------
_SCHEME = b"app"
_scheme_obj = QWebEngineUrlScheme(_SCHEME)
_scheme_obj.setFlags(
    QWebEngineUrlScheme.Flag.SecureScheme
    | QWebEngineUrlScheme.Flag.LocalScheme
    | QWebEngineUrlScheme.Flag.LocalAccessAllowed
    | QWebEngineUrlScheme.Flag.CorsEnabled
)
QWebEngineUrlScheme.registerScheme(_scheme_obj)


# ---------------------------------------------------------------------------
# URL scheme handler — serves files from assets/monaco/ at app://harness/
# ---------------------------------------------------------------------------
ASSETS_ROOT = pathlib.Path(__file__).parent.parent / "assets" / "monaco"

MIME_MAP = {
    ".js": "application/javascript",
    ".html": "text/html",
    ".css": "text/css",
    ".json": "application/json",
    ".ttf": "font/ttf",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
}


class AppSchemeHandler(QWebEngineUrlSchemeHandler):
    def requestStarted(self, job: QWebEngineUrlRequestJob):
        url_path = job.requestUrl().path().lstrip("/")
        file_path = ASSETS_ROOT / url_path

        if not file_path.exists() or not file_path.is_file():
            job.fail(QWebEngineUrlRequestJob.Error.UrlNotFound)
            return

        suffix = file_path.suffix.lower()
        mime = MIME_MAP.get(suffix, "application/octet-stream")

        data = file_path.read_bytes()
        buf = QBuffer()
        buf.setData(data)
        buf.open(QIODevice.OpenModeFlag.ReadOnly)
        job.reply(mime.encode(), buf)
        # Keep buf alive until the job is done
        job._buf = buf


# ---------------------------------------------------------------------------
# QWebChannel bridge object — exposed to JavaScript as window.harness
# ---------------------------------------------------------------------------
class HarnessBridge(QObject):
    """Receives messages from JavaScript and sends them back to Python."""

    # Signal fired when JS calls harness.sendToEditor(text)
    editorContentReceived = pyqtSignal(str)

    @pyqtSlot(str)
    def sendToEditor(self, text: str):
        """Called by JS to pass editor content back to Python."""
        self.editorContentReceived.emit(text)


# ---------------------------------------------------------------------------
# Monaco HTML page
# ---------------------------------------------------------------------------
MONACO_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #1e1e1e; }
  #editor { width: 100vw; height: 100vh; }
  #status {
    position: fixed; bottom: 8px; right: 12px;
    color: #4ec9b0; font-family: monospace; font-size: 12px;
    background: rgba(0,0,0,0.7); padding: 4px 8px; border-radius: 4px;
    pointer-events: none;
  }
</style>
</head>
<body>
<div id="editor"></div>
<div id="status">Loading Monaco...</div>

<script src="app://harness/min/vs/loader.js"></script>
<script>
  // Step 1: configure AMD loader to find Monaco modules via app:// scheme
  require.config({ paths: { vs: 'app://harness/min/vs' } });

  // Step 2: wait for QWebChannel transport, THEN initialise Monaco
  // QWebChannel must be set up before monaco.editor.create() is called
  function initWithChannel(qt) {
    new QWebChannel(qt.webChannelTransport, function(channel) {
      var harness = channel.objects.harness;
      document.getElementById('status').textContent = 'QWebChannel OK — loading Monaco...';

      require(['vs/editor/editor.main'], function() {
        var editor = monaco.editor.create(document.getElementById('editor'), {
          value: '# Monaco POC placeholder\\n# Waiting for Python to inject content...',
          language: 'python',
          theme: 'vs-dark',
          fontSize: 14,
          minimap: { enabled: false },
          automaticLayout: true,
        });

        document.getElementById('status').textContent = 'Monaco OK — bridge ready';

        // Expose read-back function so Python can call it via runJavaScript
        window.getEditorValue = function() {
          return editor.getValue();
        };

        // Expose inject function so Python can push content in
        window.setEditorValue = function(text) {
          editor.setValue(text);
          // Send the new value back to Python via the bridge
          harness.sendToEditor(editor.getValue());
        };

        document.getElementById('status').textContent = 'READY';
      });
    });
  }

  // QWebChannel transport may already be available (synchronous setUrl case)
  // or it may arrive slightly after page load (race condition fix)
  if (typeof qt !== 'undefined') {
    initWithChannel(qt);
  } else {
    document.addEventListener('DOMContentLoaded', function() {
      if (typeof qt !== 'undefined') {
        initWithChannel(qt);
      }
    });
    // Final safety net — poll briefly
    var _poll = setInterval(function() {
      if (typeof qt !== 'undefined') {
        clearInterval(_poll);
        initWithChannel(qt);
      }
    }, 50);
    setTimeout(function() { clearInterval(_poll); }, 5000);
  }
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------
class PocWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voice Harness — Phase 0 Monaco POC")
        self.resize(1000, 700)

        self._result = None

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Status label (above editor)
        self._status_label = QLabel("Initialising...")
        self._status_label.setStyleSheet(
            "background:#252526; color:#ccc; font-family:monospace; font-size:12px; padding:6px 12px;"
        )
        layout.addWidget(self._status_label)

        # WebEngine view
        self._view = QWebEngineView()
        self._view.settings().setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptEnabled, True
        )
        self._view.settings().setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True
        )
        self._view.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False
        )
        layout.addWidget(self._view)

        # Register custom URL scheme handler on this page's profile
        self._handler = AppSchemeHandler()
        self._view.page().profile().installUrlSchemeHandler(b"app", self._handler)

        # Set up QWebChannel BEFORE setUrl (critical — prevents race condition)
        self._channel = QWebChannel()
        self._bridge = HarnessBridge()
        self._bridge.editorContentReceived.connect(self._on_editor_content)
        self._channel.registerObject("harness", self._bridge)
        self._view.page().setWebChannel(self._channel)

        # Load the Monaco HTML — served inline via setHtml with base URL set to app://harness/
        self._view.setHtml(MONACO_HTML, QUrl("app://harness/"))

        # Inject test content after Monaco has had time to load
        QTimer.singleShot(4000, self._inject_test_content)

        # Inject button for manual re-test
        btn = QPushButton("Re-run round-trip test")
        btn.setStyleSheet("background:#0e639c; color:#fff; font-family:monospace; padding:6px 12px; border:none;")
        btn.clicked.connect(self._inject_test_content)
        layout.addWidget(btn)

    def _inject_test_content(self):
        TEST_CONTENT = "def hello_harness():\n    return 'Phase 0 round-trip OK'"
        self._status_label.setText(f"Injecting: {TEST_CONTENT!r}")
        self._view.page().runJavaScript(
            f"window.setEditorValue !== undefined ? window.setEditorValue({json.dumps(TEST_CONTENT)}) : 'no setEditorValue yet'"
        )

    def _on_editor_content(self, text: str):
        expected = "def hello_harness():\n    return 'Phase 0 round-trip OK'"
        if text.strip() == expected.strip():
            result = "✓ PASS — ROUND-TRIP OK"
            colour = "#4ec9b0"
        else:
            result = f"✗ FAIL — got: {text!r}"
            colour = "#f44747"

        self._result = result
        self._status_label.setText(result)
        self._status_label.setStyleSheet(
            f"background:#252526; color:{colour}; font-family:monospace;"
            f" font-size:13px; font-weight:bold; padding:6px 12px;"
        )
        print(f"\n{'='*50}\n{result}\n{'='*50}\n")


def main():
    # Multiprocessing spawn guard — required for Windows
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Dark palette for surrounding chrome
    palette = app.palette()
    palette.setColor(palette.ColorRole.Window, QColor("#1e1e1e"))
    palette.setColor(palette.ColorRole.WindowText, QColor("#d4d4d4"))
    app.setPalette(palette)

    window = PocWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
