# 🤖 AIDA

A voice-activated AI assistant for macOS that listens, transcribes locally, thinks with Groq, and speaks back in a natural voice.

## Features

- Voice-first assistant loop in the terminal
- Local speech-to-text using OpenAI Whisper
- Fast LLaMA 3.1 responses through the Groq API
- Natural female voice responses with `edge-tts`
- Session-based conversation memory for follow-up questions
- Graceful voice shutdown with commands like `goodbye` and `exit`
- Customizable voice, model, and timing through `config.py`

## Tech Stack

| Component | Tool | Purpose | Cost |
| --- | --- | --- | --- |
| LLM (Brain) | Groq API (`llama-3.1-8b-instant`) | AI understanding and responses | Free |
| Speech-to-Text | OpenAI Whisper (`base`) | Microphone audio to text | Free |
| Text-to-Speech | `edge-tts` | Response text to natural female voice | Free |
| Audio Recording | `sounddevice` | Capture microphone input | Free |
| Audio Playback | `afplay` | Play generated `.mp3` audio on macOS | Free |
| Audio File I/O | `scipy` | Save `.wav` files for transcription | Free |
| Array Processing | `numpy` | Handle audio buffers | Free |

## Prerequisites

- macOS
- Python 3.9+
- Free Groq API key

## Installation

1. Install system dependencies.

```bash
brew install portaudio ffmpeg
```

2. Create and activate a virtual environment.

```bash
cd AIDA
python3 -m venv venv
source venv/bin/activate
```

3. Install Python packages.

```bash
pip install -r requirements.txt
```

## API Key Setup

Add your Groq API key to `~/.zshrc`:

```bash
echo 'export GROQ_API_KEY="paste_your_key_here"' >> ~/.zshrc
source ~/.zshrc
echo $GROQ_API_KEY
```

## Running AIDA

```bash
python aida.py
```

## Voice Customization

| Voice ID | Accent | Tone | Best For |
| --- | --- | --- | --- |
| `en-US-JennyNeural` | American English | Warm, professional | Default general use |
| `en-US-AriaNeural` | American English | Clear, friendly | Conversational use |
| `en-GB-SoniaNeural` | British English | Formal, articulate | Professional contexts |
| `en-IN-NeerjaNeural` | Indian English | Natural, warm | India-localized feel |

## Configuration

All user-configurable values live in `config.py`. You can change the voice, recording duration, Whisper model, Groq model, output audio file name, response length, and assistant name without editing `aida.py`.

## Troubleshooting

1. Microphone access fails.
   Fix: Open `System Settings > Privacy & Security > Microphone > Terminal` and enable access.
2. Whisper does not load on first run.
   Fix: Check your internet connection once so Whisper can download the `base` model cache.
3. AIDA starts but Groq replies fail.
   Fix: Verify `echo $GROQ_API_KEY` prints your key and restart the terminal session.

## Roadmap

- [ ] Wake word support like "Hey AIDA"
- [ ] Web search for current information
- [ ] Voice-based app control on macOS
- [ ] Session memory across restarts
- [ ] GUI with waveform and chat history
- [ ] Context trimming for long conversations

## Author

- GitHub: [Nipun Jaiswal](https://github.com/Nipunjaiswal442)
- LinkedIn: [Nipun Jaiswal](https://www.linkedin.com/)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
