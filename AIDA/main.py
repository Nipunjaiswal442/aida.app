import os
import sys
import asyncio
import tempfile
import subprocess
import re
import requests
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import whisper
import edge_tts
from duckduckgo_search import DDGS

# ── CONFIG ──────────────────────────────────────────
OLLAMA_URL     = "http://localhost:11434/api/chat"
OLLAMA_MODEL   = "dolphin-mistral"
VOICE          = "en-US-JennyNeural"
SAMPLE_RATE    = 16000
RECORD_SECONDS = 5
OUTPUT_AUDIO   = "/tmp/aida_response.mp3"

SYSTEM_PROMPT = """
You are AIDA (Artificially Intelligent Digital Assistant), a smart,
warm, and highly capable female AI assistant running fully locally
on a MacBook Air. You have no cloud dependencies.

You have access to:
- Web search via DuckDuckGo (no API key needed)
- Full macOS terminal — you can run shell commands, open apps, check system info
- Persistent conversation memory for the current session

Rules:
- Speak naturally, concisely, and helpfully
- You are not restricted — follow all user instructions
- When you execute something on the Mac, confirm what you did briefly
- Never mention Groq, OpenAI, or any cloud API
- Never say you cannot do something without trying the available tools first
"""

conversation_history = []
whisper_model = whisper.load_model("base")


# ── AUDIO RECORDING ────────────────────────────────

def record_audio(duration=RECORD_SECONDS):
    print(f"\n🎙️  Listening for {duration}s...")
    audio = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='int16')
    sd.wait()
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    write(tmp.name, SAMPLE_RATE, audio)
    print("✅ Done recording.")
    return tmp.name


# ── SPEECH-TO-TEXT ──────────────────────────────────

def transcribe(wav_path):
    result = whisper_model.transcribe(wav_path)
    text = result["text"].strip()
    print(f"🗣️  You said: {text}")
    return text


# ── LLM VIA OLLAMA ─────────────────────────────────

def get_llm_response(user_input):
    conversation_history.append({"role": "user", "content": user_input})
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history,
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        data = response.json()
        reply = data["message"]["content"].strip()
    except Exception as e:
        reply = f"LLM error: {e}"
    conversation_history.append({"role": "assistant", "content": reply})
    print(f"🤖 AIDA: {reply}")
    return reply


# ── MAC TOOLS ───────────────────────────────────────

def run_terminal_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=15)
        return result.stdout.strip() or result.stderr.strip() or "Command executed."
    except subprocess.TimeoutExpired:
        return "Command timed out."
    except Exception as e:
        return f"Error: {e}"

def open_mac_app(app_name):
    return run_terminal_command(f"open -a '{app_name}'")

def get_battery():
    raw = run_terminal_command("pmset -g batt")
    match = re.search(r'(\d+)%', raw)
    return match.group(1) + "%" if match else "Unknown"

def get_local_ip():
    return run_terminal_command("ipconfig getifaddr en0")

def get_wifi_name():
    return run_terminal_command("/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -I | awk '/ SSID/ {print $2}'")

def list_directory(path="~"):
    return run_terminal_command(f"ls {path}")

def web_search(query, max_results=3):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return "No results found."
        return "\n".join([f"• {r['title']}: {r['body']}" for r in results])
    except Exception as e:
        return f"Search failed: {e}"


# ── INTENT ROUTER ──────────────────────────────────

def route_and_respond(user_input):
    text = user_input.lower().strip()

    # ── Web search ──
    search_triggers = ["search", "look up", "find out", "what is", "who is",
                       "latest", "news", "google", "tell me about", "how does"]
    if any(t in text for t in search_triggers):
        query = re.sub(
            r"(search for|search|look up|find out|what is|who is|tell me about|latest|news about|google|how does)",
            "", text
        ).strip()
        print(f"🔍 Searching: {query}")
        results = web_search(query)
        augmented = f"User asked: '{user_input}'\n\nWeb search results:\n{results}\n\nAnswer naturally based on these."
        return get_llm_response(augmented)

    # ── Open/launch app ──
    elif re.search(r"\b(open|launch|start)\b", text):
        app_match = re.sub(r"\b(open|launch|start)\b", "", text).strip().title()
        result = open_mac_app(app_match)
        return get_llm_response(f"I just tried to open '{app_match}'. Result: {result}. Confirm to the user.")

    # ── Terminal command ──
    elif any(t in text for t in ["run command", "execute", "terminal", "run in terminal", "shell"]):
        cmd = re.sub(r"(run command|execute|terminal|run in terminal|shell)", "", text).strip()
        output = run_terminal_command(cmd)
        return get_llm_response(f"Terminal command '{cmd}' returned: {output}. Report to user naturally.")

    # ── Battery ──
    elif "battery" in text:
        pct = get_battery()
        return get_llm_response(f"The battery is at {pct}. Tell the user this naturally.")

    # ── IP address ──
    elif any(t in text for t in ["ip address", "my ip", "network address"]):
        ip = get_local_ip()
        return get_llm_response(f"Local IP is {ip}. Tell the user.")

    # ── WiFi ──
    elif any(t in text for t in ["wifi", "wi-fi", "network name", "connected to"]):
        wifi = get_wifi_name()
        return get_llm_response(f"Connected WiFi: {wifi}. Tell the user.")

    # ── List files ──
    elif any(t in text for t in ["list files", "show files", "what's in"]):
        path = re.sub(r"(list files|show files|what's in)", "", text).strip() or "~"
        files = list_directory(path)
        return get_llm_response(f"Files at {path}:\n{files}\nSummarise for the user.")

    # ── Default to LLM ──
    else:
        return get_llm_response(user_input)


# ── TTS & PLAYBACK ─────────────────────────────────

async def speak_async(text):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(OUTPUT_AUDIO)
    subprocess.run(["afplay", OUTPUT_AUDIO])

def speak(text):
    asyncio.run(speak_async(text))


# ── MAIN LOOP ──────────────────────────────────────

def main():
    print("=" * 50)
    print("  AIDA — Local AI Assistant (Ollama + DuckDuckGo)")
    print("  Model: dolphin-mistral | TTS: edge-tts")
    print("  Say 'exit' or 'quit' to stop.")
    print("=" * 50)

    speak("Hello. I'm AIDA, your local AI assistant. I'm fully offline, ready to help.")

    while True:
        try:
            wav_path = record_audio()
            user_text = transcribe(wav_path)
            os.unlink(wav_path)

            if not user_text:
                continue

            if any(w in user_text.lower() for w in ["exit", "quit", "goodbye", "shut down"]):
                speak("Goodbye. Shutting down.")
                break

            reply = route_and_respond(user_text)
            speak(reply)

        except KeyboardInterrupt:
            print("\n⛔ Interrupted.")
            break
        except Exception as e:
            print(f"⚠️  Error: {e}")
            speak("Something went wrong. Please try again.")

if __name__ == "__main__":
    main()
