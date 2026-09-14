# AIDA — application source

This directory holds the AIDA desktop app: a local-first, voice-driven macOS
assistant built on Ollama, Whisper, Kokoro and PyQt6.

**Setup, usage, configuration and troubleshooting live in the [root README](../README.md).**
This file is only a map of the source so the two documents cannot drift apart.

## Entry point

```bash
source venv/bin/activate
python3 main.py
```

`main.py` patches the Homebrew paths onto `PATH` (so `ffmpeg` resolves when launched
from Automator) and opens `ui/main_window.py`.

## Modules

| File | Responsibility |
|---|---|
| `main.py` | Boots `QApplication`, shows the main window, triggers the startup greeting |
| `aida_core.py` | Intent routing, Ollama calls, Whisper STT, Kokoro/edge-tts TTS, ChromaDB memory, DuckDuckGo search, LLaVA vision, file reading |
| `terminal_brain.py` | English → `zsh` translation, blacklist, confirm-before-run, clipboard copy, `terminal_history.json` logging |
| `mac_tools.py` | AppleScript and `subprocess` tools — apps, volume, battery, disk, calendar, reminders, Spotify, notifications, screenshots |
| `ui/` | `main_window.py`, plus the orb, waveform, HUD status and chat log widgets |
| `workers/` | `QThread` workers so audio, transcription, generation, speech and shell work never block the UI |

## Generated at runtime

`memory_db/` (ChromaDB store), `terminal_history.json` (command log) and
`aida_response.mp3` (TTS scratch file) are created on first use and are git-ignored.

## Model files

`kokoro-v1.0.onnx` is committed here. Its companion `voices-v1.0.bin` is **not** — download
it as described in the root README, or AIDA falls back to network-based `edge-tts`.
