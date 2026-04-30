# Voice Harness

A standalone desktop **voice-driven coding assistant** built with Python 3.11, PyQt6, and Monaco Editor. Speak a command — the system transcribes it, sends it with file context to a Code LLM, shows edits as a diff for accept/reject, and reads the response aloud.

> **Status: Alpha — actively looking for testers!** See [Call for Testers](#-call-for-testers) below.

## Features

- **Voice-first workflow** — speak naturally; keyboard/mouse is secondary
- **Monaco code editor** — full syntax highlighting via embedded Monaco 0.52.0
- **AI-powered edits** — SEARCH/REPLACE blocks parsed from LLM output, shown as diffs
- **Accept / Reject** — review every change before it touches your code
- **Git auto-commit** — accepted edits are committed automatically
- **Local STT** — direct faster-whisper turbo + WebRTC VAD (runs on GPU)
- **Local TTS** — Kokoro-82M with sentence-level navigation, speed control, and GPU support when available
- **Repo map** — tree-sitter symbol index for richer LLM context
- **Cloud LLM** — Gemini 2.5 Flash Lite via OpenAI SDK (100k char context)

## Tech Stack

| Layer | Technology |
|---|---|
| UI | PyQt6 + PyQt6-WebEngine |
| Editor | Monaco Editor 0.52.0 (AMD build, localhost HTTP) |
| STT | faster-whisper turbo + WebRTC VAD |
| LLM | Gemini 2.5 Flash Lite via OpenAI SDK |
| TTS | Kokoro-82M (GPU when available, CPU fallback, Apache 2.0) |
| Edit format | Aider-style SEARCH/REPLACE blocks |
| VCS | gitpython auto-commit |

## Requirements

- **Python 3.11.x** — required for the supported audio stack
- **Windows 11** — primary target (Linux/macOS untested)
- **NVIDIA GPU** with CUDA 12.1 toolkit (nvcc on PATH)
- **espeak-ng** installed and on PATH (Kokoro dependency)
- **12 GB+ VRAM** recommended (tested on RTX 4080 Laptop)

## Quick Start

> **First time setting up?** See the full walkthrough in [docs/SETUP.md](docs/SETUP.md), or paste the
> [Setup Helper Agent Prompt](#-setup-helper-agent-prompt) below into Copilot Chat / ChatGPT and let
> it guide you step-by-step.

### 1. Install prerequisites (one-time)

| Tool | Why | Install |
|---|---|---|
| **Python 3.11.x** (NOT 3.12+) | Audio stack only supports 3.11 | [python.org 3.11.x](https://www.python.org/downloads/release/python-31111/) — tick "Add Python to PATH" |
| **CUDA Toolkit 12.1** | GPU STT/TTS | [nvidia.com](https://developer.nvidia.com/cuda-12-1-0-download-archive) — verify with `nvcc --version` |
| **espeak-ng** | Kokoro TTS phonemizer | [github.com/espeak-ng/releases](https://github.com/espeak-ng/espeak-ng/releases) — add `C:\Program Files\eSpeak NG` to PATH |
| **Git** | Clone + auto-commit | [git-scm.com](https://git-scm.com/download/win) |

### 2. Clone and install

```powershell
# Clone the repo
git clone https://github.com/chrismukwala/kimpa_voice_harness.git
cd kimpa_voice_harness

# Run the install wizard — creates .venv, installs CUDA PyTorch FIRST,
# pins ctranslate2==4.4.0, then installs the rest of requirements.txt
python setup/install.py
```

### 3. Add your Gemini API key

Get a free key at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey), then
create a `.env` file in the repo root:

```env
GEMINI_API_KEY=your-key-here
```

The `.env` file is gitignored — your key stays local.

### 4. Install git hooks (optional, recommended for contributors)

```powershell
python scripts/install_hooks.py
```

### 5. Run the app

```powershell
.venv\Scripts\activate
python main.py
```

Run the test suite any time with `python -m pytest tests/ -v` (561+ tests).

## Project Layout

```
voice_harnest/
├── main.py                 # Entry point
├── harness/                # Core modules (STT, LLM, TTS, coordinator, etc.)
├── ui/                     # PyQt6 UI (main window, editor, AI panel)
├── assets/monaco/          # Monaco Editor 0.52.0 AMD build
├── tests/                  # 375+ tests (TDD — Red/Green/Refactor)
├── setup/install.py        # 6-step install wizard
├── tools/                  # Manual audio diagnostics
├── phase0_poc/             # Monaco ↔ QWebChannel POC (passed)
└── docs/                   # Architecture, decisions, progress, setup
```

## Development

This project follows **Red → Green → Refactor** TDD:

1. Write a failing test
2. Write minimum code to pass
3. Refactor while tests stay green
4. `python -m pytest tests/ -v` before every commit

See [AGENTS.md](AGENTS.md) for full contributor guidelines.

## 🧪 Call for Testers

**We need your help!** Voice Harness is in alpha and we're looking for testers to try it on real hardware and report issues.

### What we need tested

- **Installation** — Does `setup/install.py` complete cleanly on your system?
- **Audio pipeline** — Does STT transcription work with your microphone?
- **TTS playback** — Does Kokoro read responses aloud correctly?
- **Monaco editor** — Does the editor render and respond to input?
- **Edit flow** — Do SEARCH/REPLACE diffs display and apply correctly?
- **GPU compatibility** — Any CUDA or QtWebEngine GPU issues?

### How to test

1. Follow the [Quick Start](#quick-start) above
2. Open a small project directory and try voice commands
3. Try manual text input via the AI panel if STT isn't working
4. Report issues at [GitHub Issues](https://github.com/chrismukwala/kimpa_voice_harnest/issues)

### What to include in bug reports

- OS version and GPU model
- Python version (`python --version`)
- CUDA toolkit version (`nvcc --version`)
- Full error traceback or screenshot
- Steps to reproduce

### Known limitations

- Windows 11 only (Linux/macOS untested)
- Requires NVIDIA GPU with CUDA 12.1
- Python 3.11 only (3.12+ not supported)
- Voice UX is stabilizing — speaking, listening, interruption, and TTS playback may still feel rough

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `python: command not found` | Python not on PATH | Reinstall Python 3.11 with "Add to PATH" ticked |
| `nvcc: not recognized` | CUDA Toolkit not on PATH | Install CUDA 12.1, restart shell |
| `espeak-ng not found` | Kokoro can't phonemize | Install espeak-ng, add install dir to PATH |
| `torch.cuda.is_available()` returns `False` | CPU-only torch installed | Re-run `python setup/install.py` — it installs CUDA torch first |
| `Failed to create shared context for virtualization` | Dual-GPU laptop using iGPU | Windows Settings → Graphics → add `python.exe` → High Performance |
| Monaco editor blank | Web Workers blocked | The app serves Monaco via localhost HTTP — file:// won't work |
| `OMP: Error #15` | Duplicate OpenMP libs | `main.py` already sets `KMP_DUPLICATE_LIB_OK=TRUE` |
| `ctranslate2` cuDNN error | Wrong ctranslate2 version | Pin `ctranslate2==4.4.0` (installer does this) |

Full details in [docs/SETUP.md § Known Issues](docs/SETUP.md#known-issues--workarounds).

## 🤖 Setup Helper Agent Prompt

New to Python, CUDA, or voice apps? Paste the prompt below into **GitHub Copilot Chat**,
**ChatGPT**, **Claude**, or any AI coding assistant *before* you start. The assistant will
walk you through setup, diagnose errors, and verify each step.

````text
You are my Voice Harness setup assistant. I am a novice and need step-by-step help getting
the project running on Windows 11. The repo is https://github.com/chrismukwala/kimpa_voice_harness

Ground rules for you:
1. Walk me through ONE step at a time. After each step, ask me to paste the command output
   before moving on. Do not assume success.
2. Always explain WHY a step matters in one short sentence.
3. If a command fails, diagnose the exact error before suggesting a fix. Never tell me to
   "just try again".
4. Never tell me to bypass safety: no `--no-verify`, no `pip install --break-system-packages`,
   no disabling antivirus.
5. Use the project's authoritative docs as your source of truth: README.md, docs/SETUP.md,
   AGENTS.md. If I ask something not covered there, say so.

Hard constraints you must enforce (these are non-negotiable for this project):
- Python MUST be 3.11.x. If `python --version` shows 3.12 or 3.13, stop and help me install 3.11.
- CUDA Toolkit 12.1 must be on PATH (`nvcc --version` works).
- espeak-ng must be on PATH (`espeak-ng --version` works) — Kokoro TTS depends on it.
- PyTorch CUDA wheel MUST be installed BEFORE faster-whisper or Kokoro, or pip will lock in
  CPU-only torch. The wizard `python setup/install.py` handles this.
- ctranslate2 must be pinned to 4.4.0 (≥4.5.0 needs cuDNN 9.2 which conflicts here).
- A NVIDIA GPU is required. The app will not work on CPU-only or AMD/Intel-only systems.

Walk me through these phases in order, asking me to confirm each:

PHASE A — Prerequisites
  1. Verify Python 3.11.x: `python --version`
  2. Verify CUDA: `nvcc --version`
  3. Verify Git: `git --version`
  4. Verify espeak-ng: `espeak-ng --version`
  5. Confirm I have an NVIDIA GPU: `nvidia-smi`

PHASE B — Clone & install
  6. `git clone https://github.com/chrismukwala/kimpa_voice_harness.git`
  7. `cd kimpa_voice_harness`
  8. `python setup/install.py` — explain that this is a guided wizard and may take 5–15 min.
     Ask me to paste the FINAL output so you can confirm CUDA torch is active.

PHASE C — Configure API key
  9. Tell me to get a Gemini key at https://aistudio.google.com/app/apikey
 10. Help me create a `.env` file with `GEMINI_API_KEY=...` and confirm it is gitignored.

PHASE D — First run
 11. Activate the venv: `.venv\Scripts\activate`
 12. Run `python -m pytest tests/ -v` and confirm all tests pass.
 13. Run `python tools/test_audio.py --list-only` to find my speaker device.
 14. Run `python tools/test_mic.py --list-only` to find my microphone.
 15. Run `python main.py` and tell me what to expect on first launch.

PHASE E — Sanity check the voice loop
 16. Have me speak a short request like "rename this variable" and describe what should
     happen (transcript appears, LLM responds, diff is shown, accept/reject).

If at ANY point I see an error, stop the phase, ask me to paste the FULL traceback, then
cross-reference docs/SETUP.md "Known Issues & Workarounds" before proposing a fix.

Start with Phase A, step 1. Ask me to run the command and paste the output.
````

> **Tip:** if you'd rather skim than chat, the same checklist lives in [docs/SETUP.md](docs/SETUP.md).

## License

Licensed under the [Apache License 2.0](LICENSE).

## Author

Chris Mukwala — [@chrismukwala](https://github.com/chrismukwala)
