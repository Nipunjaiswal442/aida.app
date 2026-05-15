# AIDA — Artificially Intelligent Digital Assistant

> A fully local, voice-controlled AI assistant for macOS — no cloud, no API keys, no cost.

![AIDA Banner](assets/demo.gif)

---

## What AIDA Can Do

| Capability | Detail |
|---|---|
| 🎙️ Voice Input | Whisper (base model, runs on Metal) |
| 🧠 AI Brain | Dolphin Mistral via Ollama — 100% local |
| 🔊 Voice Output | edge-tts (natural female voice, Jenny Neural) |
| 🔍 Web Search | DuckDuckGo — no API key needed |
| 💻 Mac Control | Open apps, run terminal commands, check battery/WiFi/IP |
| 💬 Memory | Full conversation history within a session |
| 🔒 Privacy | Zero data sent to any cloud service |

---

## Tech Stack

- **LLM:** [Ollama](https://ollama.com) + `dolphin-mistral` (local inference)
- **STT:** [OpenAI Whisper](https://github.com/openai/whisper) (base model, local)
- **TTS:** [edge-tts](https://github.com/rany2/edge-tts) (Microsoft neural voices, free)
- **Search:** [duckduckgo-search](https://github.com/deedy5/duckduckgo_search) (no API key)
- **Audio:** sounddevice, numpy, scipy
- **Platform:** macOS (Apple Silicon + Intel), launched via Automator

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
git clone https://github.com/YOUR_USERNAME/AIDA.git
cd AIDA

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

## Automator App Setup (One-Click Launch)

1. Open **Automator** → New Document → **Application**
2. Add a **Run Shell Script** action
3. Paste:

```bash
open -a Ollama
sleep 4
cd /Users/YOUR_USERNAME/aida-assistant/AIDA
/Users/YOUR_USERNAME/aida-assistant/AIDA/venv/bin/python3.12 main.py
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
| "What is quantum entanglement?" | Answers directly from local LLM |

---

## Project Structure

```
AIDA/
├── main.py              # Core assistant logic
├── requirements.txt     # Python dependencies
├── .env.example         # No longer needed (no API keys required)
├── .gitignore
├── README.md
└── assets/
    └── demo.gif         # Demo recording (add your own)
```

---

## Built With

Built by **Nipun Jaiswal** using:
- [Ollama](https://ollama.com) for local LLM inference
- [Whisper](https://github.com/openai/whisper) for speech recognition
- [edge-tts](https://github.com/rany2/edge-tts) for natural voice output
- [duckduckgo-search](https://github.com/deedy5/duckduckgo_search) for live web search
- Scaffolded with [Claude](https://claude.ai) and [Antigravity](https://antigravity.dev)

---

## Roadmap

- [ ] Wake word detection (openWakeWord)
- [ ] Local memory with ChromaDB (persistent across sessions)
- [ ] Calendar integration via AppleScript
- [ ] File summarization (read and explain documents)
- [ ] Screenshot + vision (LLaVA model via Ollama)
- [ ] Faster TTS with Kokoro or Piper (offline)

---

## License

MIT License — free to use, modify, and distribute.
