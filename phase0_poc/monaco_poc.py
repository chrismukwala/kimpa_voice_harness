"""
Phase 0 — Monaco POC Gate
=========================
Binary pass/fail test. Run this BEFORE writing any voice/LLM code.

Tests:
  1. QWebEngineView loads Monaco from localhost HTTP server
  2. QWebChannel bridge round-trips: Python injects text → reads it back
  3. Monaco AMD loader works (Web Workers OK on http:// origin)
  4. QWebChannel js object available before monaco.editor.create()

Pass: "PASS — ROUND-TRIP OK" printed to console + shown in window.
Fail: timeout / JS error / empty round-trip result.

Usage:
    python phase0_poc/monaco_poc.py
"""

import os
import sys
import json
import pathlib
import threading
import http.server
import functools
import socket

# Razer Blade Optimus fix — must be set before any Qt imports.
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--in-process-gpu"
os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import QObject, pyqtSlot, pyqtSignal, QTimer, QUrl
from PyQt6.QtGui import QColor


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ASSETS_ROOT = pathlib.Path(__file__).parent.parent / "assets" / "monaco"


# ---------------------------------------------------------------------------
# Monaco HTML page (uses localhost:{port} for sub-resources)
# ---------------------------------------------------------------------------
def get_monaco_html(port: int) -> str:
    return f"""\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html, body {{ width: 100%; height: 100%; background: #1e1e1e; overflow: hidden; }}
  #editor {{ position: absolute; top: 32px; left: 0; right: 0; bottom: 0; }}
  #status {{
    position: absolute; top: 0; left: 0; right: 0; height: 32px;
    color: #9cdcfe; background: #252526;
    font-family: Consolas, monospace; font-size: 12px;
    line-height: 32px; padding: 0 12px;
  }}
</style>
</head>
<body>
<div id="status">Loading...</div>
<div id="editor"></div>

<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<script src="http://localhost:{port}/min/vs/loader.js"></script>
<script>
  var _status = document.getElementById('status');
  function setStatus(msg) {{ _status.textContent = msg; console.log('[poc] ' + msg); }}

  setStatus('Scripts loaded — waiting for qt.webChannelTransport...');

  function startApp(qt) {{
    setStatus('qt object found — opening QWebChannel...');
    new QWebChannel(qt.webChannelTransport, function(channel) {{
      var harness = channel.objects.harness;
      setStatus('QWebChannel OK — loading Monaco editor...');

      require.config({{ paths: {{ vs: 'http://localhost:{port}/min/vs' }} }});
      require(['vs/editor/editor.main'], function() {{
        setStatus('Monaco loaded — creating editor instance...');
        var editor = monaco.editor.create(document.getElementById('editor'), {{
          value: '# Monaco loaded successfully\\n# Waiting for round-trip test...',
          language: 'python',
          theme: 'vs-dark',
          fontSize: 14,
          minimap: {{ enabled: false }},
          automaticLayout: true,
        }});

        window.setEditorValue = function(text) {{
          editor.setValue(text);
          harness.sendToEditor(editor.getValue());
        }};
        window.getEditorValue = function() {{ return editor.getValue(); }};

        setStatus('READY — editor created, bridge wired, waiting for round-trip inject...');
      }});
    }});
  }}

  var _attempts = 0;
  var _poll = setInterval(function() {{
    _attempts++;
    if (typeof qt !== 'undefined' && qt.webChannelTransport) {{
      clearInterval(_poll);
      startApp(qt);
    }} else if (_attempts > 200) {{
      clearInterval(_poll);
      setStatus('TIMEOUT — qt.webChannelTransport never appeared after 10s');
    }}
  }}, 50);
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Local HTTP server — serves assets/monaco/ on localhost
# ---------------------------------------------------------------------------
def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_asset_server(port: int) -> http.server.HTTPServer:
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler,
        directory=str(ASSETS_ROOT),
    )
    server = http.server.HTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


# ---------------------------------------------------------------------------
# QWebChannel bridge object
# ---------------------------------------------------------------------------
class HarnessBridge(QObject):
    editorContentReceived = pyqtSignal(str)

    @pyqtSlot(str)
    def sendToEditor(self, text: str):
        self.editorContentReceived.emit(text)


# ---------------------------------------------------------------------------
# Debug page — captures JS console.log → Python stdout
# ---------------------------------------------------------------------------
class DebugPage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, line, source):
        print(f"  [JS] {message}")


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------
class PocWindow(QMainWindow):
    def __init__(self, port: int):
        super().__init__()
        self.setWindowTitle("Voice Harness — Phase 0 Monaco POC")
        self.resize(1000, 700)
        self._port = port

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._status_label = QLabel(f"Starting on localhost:{port}...")
        self._status_label.setStyleSheet(
            "background:#252526; color:#9cdcfe; font-family:Consolas,monospace;"
            " font-size:12px; padding:6px 12px;"
        )
        layout.addWidget(self._status_label)

        # Web view
        self._view = QWebEngineView()
        page = DebugPage(self._view.page().profile(), self._view)
        self._view.setPage(page)
        self._view.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        self._view.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)
        layout.addWidget(self._view)

        # QWebChannel — set BEFORE loading the page
        self._channel = QWebChannel()
        self._bridge = HarnessBridge()
        self._bridge.editorContentReceived.connect(self._on_editor_content)
        self._channel.registerObject("harness", self._bridge)
        self._view.page().setWebChannel(self._channel)

        # Load via setHtml with the localhost base URL
        html = get_monaco_html(port)
        self._view.setHtml(html, QUrl(f"http://localhost:{port}/"))
        self._status_label.setText(f"Page loaded — Monaco initialising (localhost:{port})...")

        # Auto-inject round-trip test after 10s
        QTimer.singleShot(10000, self._inject_test_content)

        btn = QPushButton("Re-run round-trip test")
        btn.setStyleSheet(
            "background:#0e639c; color:#fff; font-family:Consolas,monospace;"
            " padding:6px 12px; border:none; font-size:12px;"
        )
        btn.clicked.connect(self._inject_test_content)
        layout.addWidget(btn)

    def _inject_test_content(self):
        TEST_CONTENT = "def hello_harness():\n    return 'Phase 0 round-trip OK'"
        self._status_label.setText("Injecting test content...")
        js = (
            f"typeof window.setEditorValue === 'function'"
            f" ? (window.setEditorValue({json.dumps(TEST_CONTENT)}), 'injected')"
            f" : 'setEditorValue not ready'"
        )
        self._view.page().runJavaScript(js, self._on_inject_result)

    def _on_inject_result(self, result):
        if result == "injected":
            self._status_label.setText("Injected — waiting for bridge callback...")
        else:
            self._status_label.setText(f"Not ready yet: {result} — click button to retry")

    def _on_editor_content(self, text: str):
        expected = "def hello_harness():\n    return 'Phase 0 round-trip OK'"
        if text.strip() == expected.strip():
            result = "PASS — ROUND-TRIP OK"
            colour = "#4ec9b0"
        else:
            result = f"FAIL — got: {text!r}"
            colour = "#f44747"

        self._status_label.setText(result)
        self._status_label.setStyleSheet(
            f"background:#252526; color:{colour}; font-family:Consolas,monospace;"
            f" font-size:13px; font-weight:bold; padding:6px 12px;"
        )
        print(f"\n{'='*50}")
        print(result)
        print(f"{'='*50}\n")


def main():
    port = find_free_port()
    print(f"Starting Monaco asset server on http://localhost:{port}/")
    server = start_asset_server(port)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    palette = app.palette()
    palette.setColor(palette.ColorRole.Window, QColor("#1e1e1e"))
    palette.setColor(palette.ColorRole.WindowText, QColor("#d4d4d4"))
    app.setPalette(palette)

    window = PocWindow(port)
    window.show()

    ret = app.exec()
    server.shutdown()
    sys.exit(ret)


if __name__ == "__main__":
    main()
