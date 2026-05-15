# AIDA — Artificially Intelligent Digital Assistant

> A fully local, voice-controlled AI assistant for macOS with a cinematic HUD — no cloud, no API keys, no cost.

![AIDA Banner](assets/demo.gif)

---

## What AIDA Can Do

| Capability | Detail |
|---|---|
| 🎙️ Voice Input | Hold-to-talk with Whisper (base model, runs on Metal) |
| ⌨️ Text Input | Type messages directly in the HUD |
| 🧠 AI Brain | Dolphin Mistral via Ollama — 100% local |
| 🔊 Voice Output | edge-tts (natural female voice, Jenny Neural) |
| 🔍 Web Search | DuckDuckGo — no API key needed |
| 💻 Mac Control | Open apps, run terminal commands, check battery/WiFi/IP |
| 🎨 Cinematic HUD | Animated glowing orb, live waveform, dark theme |
| 💬 Memory | Full conversation history within a session |
| 🔒 Privacy | Zero data sent to any cloud service |

---

## Tech Stack

| Component | Technology |
|---|---|
| GUI Framework | PyQt6 (custom QPainter animations) |
| LLM | [Ollama](https://ollama.com) + `dolphin-mistral` (100% local) |
| Speech-to-Text | [OpenAI Whisper](https://github.com/openai/whisper) (base model, local) |
| Text-to-Speech | [edge-tts](https://github.com/rany2/edge-tts) (Microsoft neural voices) |
| Web Search | [duckduckgo-search](https://github.com/deedy5/duckduckgo_search) (no API key) |
| Audio Recording | sounddevice + numpy |
| Audio Playback | afplay (macOS native) |
| Audio File I/O | scipy (wavfile) |

---

## Setup Guide

### Prerequisites

```bash
# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install system dependencies
brew install portaudio ffmpeg

# Install Ollama
brew install ollama

# Pull the model
ollama pull dolphin-mistral
```

### Install AIDA

```bash
git clone https://github.com/Nipunjaiswal442/aida.app.git
cd aida.app/AIDA

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

### Run

```bash
# Make sure Ollama is running first
open -a Ollama

# Then launch AIDA
source venv/bin/activate
python3 main.py
```

Or use the **one-click Automator app** (see setup below).

---

## Keyboard Shortcuts

| Action | Key |
|---|---|
| Hold to talk | `Spacebar` (hold) |
| Stop talking | `Spacebar` (release) |
| Send text | `Enter` |
| Quit | `Cmd + Q` |

---

## Automator App Setup (One-Click Launch)

1. Open **Automator** → New Document → **Application**
2. Add a **Run Shell Script** action
3. Paste:

```bash
open -a Ollama
sleep 4
cd /Users/apple/aida-assistant/AIDA
/Users/apple/aida-assistant/AIDA/venv/bin/python3.12 main.py
```

4. Save as `AIDA.app` → drag to Dock

---

## Example Commands

| You say | What AIDA does |
|---|---|
| "Search for latest AI news" | DuckDuckGo search → LLM summarizes results |
| "Open Spotify" | Launches Spotify via macOS |
| "What's my battery level?" | Reads pmset output → speaks the percentage |
| "What WiFi am I on?" | Reads airport utility → speaks network name |
| "Run command ls ~/Downloads" | Executes in shell → speaks the result |
| "What time is it?" | Returns current date and time |
| "Set a timer for 5 minutes" | Sets countdown timer with alert sound |
| "Take a screenshot" | Captures screen to Desktop |
| "What is quantum entanglement?" | Answers directly from local LLM |

---

## Project Structure

```
AIDA/
├── main.py                    ← Entry point. Launches the PyQt6 app.
├── aida_core.py               ← All AI logic (Ollama + tools). Zero PyQt6 imports.
├── mac_tools.py               ← macOS system tools (apps, volume, battery, etc.)
├── ui/
│   ├── __init__.py
│   ├── main_window.py         ← QMainWindow. Assembles all panels + text input.
│   ├── orb_widget.py          ← Animated glowing orb (QPainter).
│   ├── waveform_widget.py     ← Animated waveform bars (QPainter).
│   ├── chat_log_widget.py     ← Scrollable conversation history.
│   └── hud_status_widget.py   ← Top bar: status text + session timer.
├── workers/
│   ├── __init__.py
│   ├── listen_worker.py       ← QThread: records mic audio.
│   ├── transcribe_worker.py   ← QThread: runs Whisper.
│   ├── llm_worker.py          ← QThread: calls Ollama API (local).
│   ├── speak_worker.py        ← QThread: runs edge-tts + afplay.
│   └── tools_worker.py        ← QThread: timer alerts.
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── assets/
    └── demo.gif               ← Demo recording (add your own)
```

---

## Voice Options

The default voice is `en-US-JennyNeural`. Change it in `aida_core.py`.

| Voice Code | Description |
|---|---|
| `en-US-JennyNeural` | Warm, professional |
| `en-US-AriaNeural` | Clear, friendly |
| `en-GB-SoniaNeural` | British accent |
| `en-IN-NeerjaNeural` | Indian English |

---

## Built With

Built by **Nipun Jaiswal** using:
- [Ollama](https://ollama.com) for local LLM inference
- [Whisper](https://github.com/openai/whisper) for speech recognition
- [edge-tts](https://github.com/rany2/edge-tts) for natural voice output
- [duckduckgo-search](https://github.com/deedy5/duckduckgo_search) for live web search
- [PyQt6](https://pypi.org/project/PyQt6/) for the cinematic HUD interface
- Scaffolded with [Claude](https://claude.ai) and [Antigravity](https://antigravity.dev)

---

## Roadmap

- [ ] Wake word detection (openWakeWord)
- [ ] Local memory with ChromaDB (persistent across sessions)
- [ ] Calendar integration via AppleScript
- [ ] File summarization (read and explain documents)
- [ ] Screenshot + vision (LLaVA model via Ollama)
- [ ] Faster TTS with Kokoro or Piper (offline)
- [ ] Settings panel in GUI

---

## License

MIT License — free to use, modify, and distribute.
