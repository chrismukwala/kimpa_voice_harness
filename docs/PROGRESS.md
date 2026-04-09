# Progress Tracker

> **Living document** — update this file after completing any work on the project.

## Phase Summary

| Phase | Status | Description |
|---|---|---|
| Phase 0 | **DONE** | Monaco ↔ QWebChannel POC gate — PASSED |
| Pre-work | **DONE** | Install wizard (`setup/install.py`) |
| Phase 1 | **DONE** | Core voice loop + 3-panel UI + coordinator pipeline |
| Phase 2a | Not started | IDE shell — file tree → editor → LLM context |
| Phase 2b | Not started | Monaco upgrade (gated on Phase 0 PASS ✓) |
| Phase 3a | Not started | SEARCH/REPLACE editing flow + diff view + git auto-commit |
| Phase 3b | Not started | Tree-sitter repo map context enhancement |
| Phase 4 | Not started | TTS UX polish + custom wake word training |

## Detailed Log

### Phase 0: Monaco POC Gate — DONE (2025-04-08)

- Created `phase0_poc/monaco_poc.py`
- Went through ~5 rewrites due to GPU and content delivery issues
- **Failed approaches**: `app://` custom URL scheme (QBuffer GC), `file://` (Web Worker block), multiple `--disable-gpu` flag combos
- **Working solution**: Localhost HTTP server (daemon thread) + `setHtml()` with localhost base URL + `--in-process-gpu` Chromium flag
- Windows Graphics Settings: Python.exe pinned to "High Performance (NVIDIA)"
- Round-trip confirmed: Python → JS inject → Monaco setValue → JS readback → Python signal match
- Result: **PASS — ROUND-TRIP OK**

### Pre-work: Install Wizard — DONE (2025-04-08)

- Created `setup/install.py` — 7-step wizard
- Steps: assert Python 3.11 → check system deps → create venv → CUDA PyTorch first → pin ctranslate2 → requirements.txt → Ollama model pull → validation suite
- External review: replaced `curl` subprocess with `urllib.request.urlopen`

### Phase 1: Core Voice Loop — DONE (2025-04-09)

Files created:
- `main.py` — entry point with env var setup and `if __name__ == '__main__'` guard
- `harness/voice_input.py` — thin RealtimeSTT adapter
- `harness/code_llm.py` — Ollama client + SEARCH/REPLACE parser + prose extractor
- `harness/tts.py` — Kokoro wrapper: `speak()` → sentence-split WAV chunks
- `harness/coordinator.py` — queue pipeline with stub context_assembler and response_splitter
- `ui/main_window.py` — 3-panel layout (file tree | editor | AI panel)
- `ui/editor_panel.py` — QPlainTextEdit placeholder
- `ui/ai_panel.py` — voice status, response log, manual input, pause button

Architecture stubs wired: coordinator message format `{"query", "context", "repo_map"}`, TTS returns `List[Tuple[str, bytes]]`, voice_input is only RealtimeSTT importer.

### Phase 2a: IDE Shell — NOT STARTED

Goal: Open files from tree, load into editor + LLM context. This phase is the permanent fallback if Monaco fails.

Planned work:
- Enhance file tree root to open a project directory
- Click file → load into QPlainTextEdit + coordinator `set_file_context()`
- Full file → LLM context path validated with real code

### Phase 2b: Monaco Upgrade — NOT STARTED

Goal: Replace QPlainTextEdit with Monaco via QWebEngineView.

Planned work:
- New `editor_panel.py` using localhost HTTP server + QWebChannel (same pattern as POC)
- Python → Monaco: send file content
- Monaco → Python: change events
- Automatic syntax highlighting via Monaco language detection

### Phase 3a: Core Editing Flow — NOT STARTED

Goal: AI suggests edits → user accepts/rejects via diff view.

Planned work:
- Activate response_splitter stub (route prose to TTS, edit blocks to diff)
- Monaco Diff Editor for accept/reject UI
- SEARCH/REPLACE parser: lenient regex + fuzzy fallback (difflib ~0.85) + ast.parse syntax gate
- Security gates: path traversal check, deny list, suspicious code scan
- Git auto-commit: gitpython, stage specific file only, secret scanner

### Phase 3b: Context Enhancements — NOT STARTED

Goal: Richer LLM context.

Planned work:
- Tree-sitter repo map: index project → compact symbol list
- Inject into `repo_map` slot (coordinator format already supports it)
- File type allowlist: `.py`, `.js`, `.ts`, `.go`, `.rs`, `.c`, `.cpp`, `.java` only

### Phase 4: TTS UX + Polish — NOT STARTED

Goal: Full TTS UX, custom wake word, dark theme polish.

Planned work:
- Arrow key TTS navigation over `List[Tuple[str, bytes]]`
- Variable speed re-synthesis
- Code explanation vs. summarization modes
- Custom "hey harness" wake word (OpenWakeWord + Piper TTS synthetic corpus + user recordings)
- Dark theme, icons, keyboard shortcuts

## Blockers

- **Python 3.11 not installed** — only Python 3.12.10 available on system. Must download from https://www.python.org/downloads/release/python-31111/ before Phase 1 can actually run.
