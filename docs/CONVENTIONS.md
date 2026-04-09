# Coding Conventions

## Language & Style

- Python 3.11 — use 3.11 features but nothing 3.12+
- Follow PEP 8 with 100-char line limit
- Use double quotes for strings (except where single quotes avoid escaping)
- Type hints on public function signatures; skip on internal/obvious locals
- Docstrings on modules and public classes/functions only — keep them short (1-3 lines)

## File Structure

- One class per file when the class is substantial (>50 lines)
- Use `__init__.py` to mark packages — keep them empty unless re-exporting
- Imports: stdlib → third-party → local, separated by blank lines
- Lazy imports for heavy libraries (e.g., `from RealtimeSTT import AudioToTextRecorder` inside the method that needs it, not at module top level) to keep startup fast

## Naming

- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions/methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private/internal: prefix with `_`

## Git

- Commit messages: `type: short description` — types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`
- Stage specific files — never `git add .` or `git add -A`
- No `--force` pushes
- LF line endings enforced (`.gitattributes`: `* text=auto eol=lf`)

## Architecture Patterns

### Thin Adapter Pattern
External libraries are wrapped in a single adapter file with a minimal public API. The rest of the codebase never imports the library directly. This makes swapping libraries a single-file change.

Current adapters:
- `harness/voice_input.py` wraps RealtimeSTT

### Queue Pipeline
The coordinator uses a queue with dict messages. New pipeline stages are added as methods, not new threads. Signals connect the pipeline to the UI.

### Coordinator Message Format
Always: `{"query": str, "context": str | None, "repo_map": str | None}`. Never pass plain strings through the pipeline.

### TTS Return Type
`speak()` always returns `List[Tuple[str, bytes]]` — a list of (sentence, WAV data) pairs. Even if only one sentence, return a list. Phase 4 navigation depends on this.

## Error Handling

- Catch specific exceptions, not bare `except:`
- Pipeline errors emit `error_occurred` signal — never crash silently
- External tool failures (Ollama down, mic unavailable) degrade gracefully with user-visible message
- Do NOT add error handling for scenarios that can't happen at the current phase

## Security

- Ollama: always `OLLAMA_HOST=127.0.0.1`, never `0.0.0.0`
- SEARCH/REPLACE apply: `os.path.realpath()` check — target must resolve inside project root
- Never auto-edit `.env`, `*.pem`, `*.key`, `id_rsa*`, `.ssh/`, `.aws/`
- Scan added lines for `subprocess`, `eval`, `exec`, `os.system`, `__import__` — warn, don't block
- Git auto-commit: stage specific file only, run secret scanner before commit

## UI

- Dark theme: background `#1e1e1e`, text `#d4d4d4`, accent `#0e639c`
- Font: Consolas, monospace, 12px for editor, 11px for panels
- Status colors: idle=`#608b4e`, listening=`#4ec9b0`, processing=`#dcdcaa`, speaking=`#ce9178`

## Documentation

- Update `docs/PROGRESS.md` after completing any phase or significant work
- Keep `AGENTS.md` accurate if project layout or constraints change
- No change-log prose in code comments — that's what git history is for
