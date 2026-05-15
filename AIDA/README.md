# 🤖 AIDA — Artificially Intelligent Digital Assistant

> Fully local, voice-controlled AI assistant for macOS.
> Zero cloud. Zero API keys. Zero cost. Runs entirely on your Mac.

---

## What AIDA Can Do

| Capability | Detail |
|---|---|
| 🎙️ Wake Word | Say "Hey AIDA" to activate (openWakeWord) |
| 🧠 AI Brain | Dolphin Mistral via Ollama — 100% local |
| 👁️ Vision | Screenshot analysis via LLaVA (local) |
| 🔍 Web Search | DuckDuckGo — no API key needed |
| 🗓️ Calendar | Read today's events, add reminders via AppleScript |
| 💻 Mac Control | Open apps, terminal commands, volume, lock screen, trash |
| 📁 File Reading | Read and summarize any file on disk |
| 🧠 Persistent Memory | Remembers past conversations via ChromaDB |
| 🔒 Privacy | Zero data leaves your machine — ever |

---

## Tech Stack

| Component | Tool | Cost |
|---|---|---|
| LLM | Ollama + dolphin-mistral | Free |
| Vision LLM | Ollama + LLaVA | Free |
| Wake Word | openWakeWord (hey_jarvis model) | Free |
| STT | OpenAI Whisper base (local) | Free |
| TTS | edge-tts / Kokoro ONNX | Free |
| Search | duckduckgo-search | Free |
| Memory | ChromaDB (local persistent) | Free |
| Mac Control | AppleScript + subprocess | Free |
| Launch | macOS Automator | Free |

---

## Setup

### Prerequisites

```bash
brew install portaudio ffmpeg
brew install ollama
ollama pull dolphin-mistral
ollama pull llava
```

### Install

```bash
git clone https://github.com/Nipunjaiswal442/aida.app.git
cd aida.app/AIDA
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run

```bash
# Ollama starts silently in background automatically via Automator
# Or manually:
ollama serve &>/dev/null &
sleep 3
python3 main.py
```

---

## Automator Setup (One-Click Launch, No Ollama Window)

1. Open Automator → New → Application
2. Add Run Shell Script action
3. Paste:

```bash
#!/bin/bash
/usr/local/bin/ollama serve &>/dev/null &
sleep 5
cd /Users/apple/aida-assistant/AIDA
source venv/bin/activate
python3 main.py
```

4. Save as AIDA.app → add to Dock

---

## Example Commands

| You say | AIDA does |
|---|---|
| "Hey AIDA" | Wakes up, says "Yes?" |
| "Search for latest AI news" | DuckDuckGo → summarizes results |
| "What's on my screen?" | Screenshots → LLaVA describes it |
| "What's on my calendar today?" | Reads Calendar.app via AppleScript |
| "Remind me to call mom" | Adds to Reminders.app |
| "Set volume to 40" | Sets system volume |
| "Read file ~/Documents/notes.txt" | Reads and summarizes the file |
| "Open Spotify" | Launches the app |
| "Lock my screen" | Runs displaysleepnow |
| "What's my disk usage?" | Reports storage stats |
| "Run command git status" | Executes in shell, speaks output |

---

## Project Structure

```
AIDA/
├── main.py              # Entry point — launches PyQt6 GUI
├── aida_core.py         # LLM, STT, TTS, memory, tools, routing
├── mac_tools.py         # macOS system tools (volume, calendar, etc.)
├── ui/                  # PyQt6 GUI components
│   ├── main_window.py   # Main window with wake word integration
│   ├── orb_widget.py    # Animated orb visualization
│   ├── waveform_widget.py # Audio waveform display
│   ├── hud_status_widget.py # Status HUD
│   └── chat_log_widget.py   # Chat history
├── workers/             # QThread background workers
│   ├── listen_worker.py     # Audio recording
│   ├── transcribe_worker.py # Whisper STT
│   ├── llm_worker.py        # Ollama LLM calls
│   ├── speak_worker.py      # TTS playback
│   └── wakeword_worker.py   # Wake word detection
├── requirements.txt     # Python dependencies
├── launch_aida.sh       # Silent Ollama + AIDA launcher
├── memory_db/           # ChromaDB persistent memory (auto-created)
└── README.md
```

---

## Built By

**Nipun Jaiswal** — VIT-AP University, CSE
- GitHub: [@Nipunjaiswal442](https://github.com/Nipunjaiswal442)

Scaffolded with [Claude](https://claude.ai) and [Antigravity](https://antigravity.dev).

---

## Roadmap

- [x] Local LLM via Ollama
- [x] Web search (DuckDuckGo)
- [x] Mac terminal control
- [x] Wake word detection
- [x] Persistent memory (ChromaDB)
- [x] Screenshot + vision (LLaVA)
- [x] Calendar + reminders
- [x] System control (volume, lock, trash)
- [ ] Spotify / music control via AppleScript
- [ ] Custom wake word training
- [ ] Faster TTS with Kokoro ONNX
- [ ] Notification center integration

---

MIT License
