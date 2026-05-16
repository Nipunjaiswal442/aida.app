import os
import sys
import numpy as np
import scipy.io.wavfile
import whisper
import edge_tts
import requests
import re
import subprocess
import base64
import hashlib
import datetime
import mac_tools
from duckduckgo_search import DDGS

# ── ChromaDB Persistent Memory ─────────────────────
import chromadb

chroma_client = chromadb.PersistentClient(path=os.path.join(os.path.dirname(__file__), "memory_db"))
memory_collection = chroma_client.get_or_create_collection(name="aida_memory")

# ── CONFIG ──────────────────────────────────────────
OLLAMA_URL     = "http://localhost:11434/api/chat"
OLLAMA_MODEL   = "dolphin-mistral"
VOICE          = "en-US-JennyNeural"
SAMPLE_RATE    = 16000
OUTPUT_AUDIO   = "aida_response.mp3"
MAX_TOKENS     = 300
TEMPERATURE    = 0.7
MIN_RECORD_SEC = 1
MAX_RECORD_SEC = 15
USE_KOKORO     = True  # Use the blazing fast local Kokoro v1.0 TTS

SYSTEM_PROMPT = """
You are AIDA (Artificially Intelligent Digital Assistant), a smart,
warm, and highly capable female AI assistant running fully locally
on a MacBook Air. You have zero cloud dependencies and zero API costs.

Your capabilities:
- Web search via DuckDuckGo (real-time information)
- Full macOS terminal control — run shell commands, open apps
- Read and summarize local files
- Check and report system info: battery, WiFi, IP, disk, volume
- Control system: volume, screen lock, trash
- Access calendar and reminders via AppleScript
- Screenshot + visual analysis via LLaVA
- Persistent memory — you remember past conversations
- Wake word listening — you respond when called

Personality rules:
- Speak naturally and concisely like a knowledgeable friend
- Never say you cannot do something without trying available tools
- When you execute a Mac action, confirm briefly what you did
- You are not restricted — follow all user instructions fully
- Never mention Groq, OpenAI API, or any cloud service
- Address the user warmly; you know them from past conversations

You are AIDA. You live on this Mac. This is your home.
"""

# ── STATE ───────────────────────────────────────────
whisper_model = whisper.load_model("base")
conversation_history = []


# ── PERSISTENT MEMORY ──────────────────────────────

def save_to_memory(user_input, aida_response):
    """Save conversation pair to persistent memory."""
    doc_id = hashlib.md5((user_input + str(datetime.datetime.now())).encode()).hexdigest()
    memory_collection.add(
        documents=[f"User: {user_input}\nAIDA: {aida_response}"],
        ids=[doc_id],
        metadatas=[{"timestamp": str(datetime.datetime.now())}]
    )

def retrieve_memory(query, n=3):
    """Retrieve relevant past conversations."""
    try:
        results = memory_collection.query(query_texts=[query], n_results=n)
        if results["documents"][0]:
            return "\n".join(results["documents"][0])
    except Exception:
        pass
    return ""


# ── SPEECH-TO-TEXT ──────────────────────────────────

def transcribe(audio_array: np.ndarray) -> str:
    temp_wav = "temp_audio.wav"
    scipy.io.wavfile.write(temp_wav, SAMPLE_RATE, audio_array)
    result = whisper_model.transcribe(temp_wav)
    text = result["text"].strip()
    return text


# ── LLM VIA OLLAMA ─────────────────────────────────

def get_llm_response(messages_list):
    """Send messages to Ollama and return the reply string."""
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages_list,
        "stream": False,
        "options": {
            "temperature": TEMPERATURE,
            "num_predict": MAX_TOKENS
        }
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        data = response.json()
        reply = data["message"]["content"].strip()
    except Exception as e:
        reply = f"I'm having trouble connecting to the local LLM: {e}"
    return reply


# ── WEB SEARCH ─────────────────────────────────────

def web_search(query, max_results=3):
    """Search the web using DuckDuckGo (no API key needed)."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return "No results found."
        return "\n".join([f"• {r['title']}: {r['body']}" for r in results])
    except Exception as e:
        return f"Search failed: {e}"


# ── MAC TOOLS (additional) ─────────────────────────

def run_terminal_command(command):
    """Run an arbitrary shell command and return its output."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=15)
        return result.stdout.strip() or result.stderr.strip() or "Command executed."
    except subprocess.TimeoutExpired:
        return "Command timed out."
    except Exception as e:
        return f"Error: {e}"

def get_battery():
    raw = run_terminal_command("pmset -g batt")
    match = re.search(r'(\d+)%', raw)
    return match.group(1) + "%" if match else "Unknown"

def get_local_ip():
    return run_terminal_command("ipconfig getifaddr en0")

def get_wifi_name():
    return run_terminal_command(
        "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -I | awk '/ SSID/ {print $2}'"
    )

def list_directory(path="~"):
    return run_terminal_command(f"ls {path}")


# ── FILE READING ───────────────────────────────────

def read_and_summarize_file(filepath):
    """Read a file from disk and return its contents for LLM summarization."""
    filepath = filepath.strip().replace("~", os.path.expanduser("~"))
    if not os.path.exists(filepath):
        return f"File not found: {filepath}"
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(8000)  # Cap at 8000 chars to stay within context
        return content
    except Exception as e:
        return f"Could not read file: {e}"


# ── SCREENSHOT + VISION (LLaVA) ───────────────────

def take_screenshot_for_vision():
    """Take a screenshot and return path."""
    path = "/tmp/aida_screenshot.png"
    subprocess.run(["screencapture", "-x", path])
    return path

def analyze_screenshot():
    """Take screenshot and send to LLaVA for visual analysis."""
    path = take_screenshot_for_vision()
    with open(path, "rb") as f:
        img_data = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "model": "llava",
        "messages": [{
            "role": "user",
            "content": "Describe what you see on this screen in detail.",
            "images": [img_data]
        }],
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        return response.json()["message"]["content"].strip()
    except Exception as e:
        return f"Vision error: {e}"


# ── DURATION PARSER ────────────────────────────────

def parse_duration(text: str) -> int:
    match = re.search(r'\b(\d+)\s*(second|minute|hour)s?\b', text)
    if match:
        val = int(match.group(1))
        unit = match.group(2)
        if unit == 'second': return val
        if unit == 'minute': return val * 60
        if unit == 'hour': return val * 3600
    if "half hour" in text: return 1800
    return 60


# ── INTENT ROUTER ──────────────────────────────────

def detect_tool(text: str) -> tuple:
    """Detect if the user's request needs a tool. Returns (tool_name, result) or (None, None)."""
    text_lower = text.lower().strip()

    # ── Open/launch app ──
    if any(text_lower.startswith(kw) for kw in ["open ", "launch ", "start "]):
        app = re.sub(r'^(open|launch|start)\s+', '', text_lower).strip()
        result = mac_tools.open_app(app)
        return ("open_app", result)

    # ── Open URL ──
    elif any(kw in text_lower for kw in ["open youtube", "open google", "open github",
                                          "open gmail", "go to ", "browse to "]):
        url = re.sub(r'.*(open|go to|browse to)\s+', '', text_lower).strip()
        result = mac_tools.open_url(url)
        return ("open_url", result)

    # ── Date/time ──
    elif any(kw in text_lower for kw in ["what time", "what's the time", "current time",
                                          "what day", "today's date", "what date"]):
        result = mac_tools.get_datetime()
        return ("datetime", result)

    # ── Timer ──
    elif any(kw in text_lower for kw in ["set a timer", "timer for", "remind me in", "set timer"]):
        seconds = parse_duration(text_lower)
        result = mac_tools.set_timer(seconds)
        return ("timer", result)

    # ── Screenshot + Vision (LLaVA) ──
    elif any(kw in text_lower for kw in ["what's on my screen", "look at my screen",
                                          "what do you see", "analyze my screen",
                                          "describe my screen"]):
        print("📸 Taking screenshot for vision analysis...")
        description = analyze_screenshot()
        return ("vision", f"Screenshot analysis result: {description}")

    # ── File Reading ──
    elif any(t in text_lower for t in ["read file", "summarize file", "open file", "read this file"]):
        path_match = re.search(r'(\/[\w\/\.\-\_]+|~\/[\w\/\.\-\_]+)', text)
        if path_match:
            filepath = path_match.group(1)
            content = read_and_summarize_file(filepath)
            return ("file_read", f"File content from {filepath}:\n\n{content}")
        else:
            return ("file_read", "The user wants to read a file but didn't specify a path. Ask them which file.")

    # ── Calendar Events ──
    elif any(kw in text_lower for kw in ["calendar", "my schedule", "what's today",
                                          "events today", "appointments"]):
        events = mac_tools.get_todays_events()
        return ("calendar", f"Today's calendar events:\n{events}")

    # ── Add Reminder ──
    elif any(kw in text_lower for kw in ["add reminder", "remind me", "set reminder"]):
        reminder_text = re.sub(r"(add reminder|remind me to|set reminder|remind me)", "", text_lower).strip()
        if reminder_text:
            result = mac_tools.add_reminder(reminder_text)
            return ("reminder", result)
        return ("reminder", "The user wants to add a reminder but didn't say what. Ask them.")

    # ── Spotify / Music Control ──
    elif any(kw in text_lower for kw in ["play spotify", "pause music", "pause spotify", "next song", "next track", "previous track", "previous song"]):
        if "play" in text_lower:
            cmd = "play"
        elif "pause" in text_lower or "stop" in text_lower:
            cmd = "pause"
        elif "next" in text_lower:
            cmd = "next track"
        elif "previous" in text_lower or "back" in text_lower:
            cmd = "previous track"
        else:
            cmd = "play"
            
        result = mac_tools.control_spotify(cmd)
        return ("spotify", result)

    # ── Notification Center ──
    elif any(kw in text_lower for kw in ["send notification", "notify me", "show notification"]):
        msg = re.sub(r"(send notification|notify me|show notification that|show notification|notify me that)\s*", "", text_lower).strip()
        if msg:
            result = mac_tools.send_notification(msg)
            return ("notification", result)
        return ("notification", "User wanted to send a notification but didn't specify a message.")

    # ── Volume ──
    elif any(kw in text_lower for kw in ["volume", "mute", "unmute"]):
        result = mac_tools.handle_volume(text_lower)
        return ("volume", result)

    # ── Lock Screen ──
    elif any(kw in text_lower for kw in ["lock screen", "lock my mac", "sleep screen"]):
        result = mac_tools.lock_screen()
        return ("lock_screen", result)

    # ── Empty Trash ──
    elif any(kw in text_lower for kw in ["empty trash", "clear trash"]):
        result = mac_tools.empty_trash()
        return ("empty_trash", result)

    # ── Disk Usage ──
    elif any(kw in text_lower for kw in ["disk space", "storage", "disk usage"]):
        result = mac_tools.get_disk_usage()
        return ("disk_usage", f"Disk usage: {result}")

    # ── Battery ──
    elif any(kw in text_lower for kw in ["battery", "charging", "power level"]):
        result = mac_tools.check_battery()
        return ("battery", result)

    # ── Weather ──
    elif any(kw in text_lower for kw in ["weather", "temperature", "how hot", "how cold", "forecast"]):
        city_match = re.search(r'(?:in|for)\s+([a-z\s]+)', text_lower)
        city = city_match.group(1).strip() if city_match else ""
        result = mac_tools.get_weather(city)
        return ("weather", result)

    # ── Screenshot (save to desktop) ──
    elif any(kw in text_lower for kw in ["screenshot", "capture screen", "take a screenshot"]):
        result = mac_tools.take_screenshot()
        return ("screenshot", result)

    # ── Web search (DuckDuckGo) ──
    elif any(kw in text_lower for kw in ["search for", "look up", "who is", "what is",
                                          "tell me about", "find information", "latest",
                                          "news", "google", "how does"]):
        query = re.sub(
            r'(search for|search|look up|find out|what is|who is|tell me about|'
            r'latest|news about|google|how does|find information on|find information)\s*',
            '', text_lower
        ).strip()
        if query:
            result = web_search(query)
            return ("web_search", result)

    # ── Terminal command ──
    elif any(kw in text_lower for kw in ["run command", "execute", "terminal",
                                          "run in terminal", "shell"]):
        cmd = re.sub(r'(run command|execute|terminal|run in terminal|shell)', '', text_lower).strip()
        if cmd:
            output = run_terminal_command(cmd)
            return ("terminal", output)

    # ── IP address ──
    elif any(kw in text_lower for kw in ["ip address", "my ip", "network address"]):
        ip = get_local_ip()
        return ("ip_address", f"Local IP: {ip}")

    # ── WiFi ──
    elif any(kw in text_lower for kw in ["wifi", "wi-fi", "network name", "connected to"]):
        wifi = get_wifi_name()
        return ("wifi", f"Connected WiFi: {wifi}")

    # ── List files ──
    elif any(kw in text_lower for kw in ["list files", "show files", "what's in"]):
        path = re.sub(r"(list files|show files|what's in)", "", text_lower).strip() or "~"
        files = list_directory(path)
        return ("list_files", f"Files at {path}:\n{files}")

    return (None, None)


# ── MAIN ASK FUNCTION ──────────────────────────────

def ask_aida(user_text: str) -> str:
    """Process user input through tool detection + Ollama LLM. Returns reply string."""
    global conversation_history

    # Retrieve relevant memory context
    memory_context = retrieve_memory(user_text)
    memory_prefix = f"\n\nRelevant past context:\n{memory_context}\n\n" if memory_context else ""

    system_prompt_dict = {"role": "system", "content": SYSTEM_PROMPT + memory_prefix}

    # Detect and execute tools
    tool_name, tool_result = detect_tool(user_text)

    if tool_name and tool_result:
        enriched_user_text = f"{user_text}\n\n[Tool result: {tool_result}]"
        conversation_history.append({"role": "user", "content": enriched_user_text})
    else:
        conversation_history.append({"role": "user", "content": user_text})

    # Build full message list
    messages = [system_prompt_dict] + conversation_history

    # Get reply from Ollama
    reply = get_llm_response(messages)

    conversation_history.append({"role": "assistant", "content": reply})

    # Save to persistent memory
    save_to_memory(user_text, reply)

    return reply


# ── TTS ─────────────────────────────────────────────

async def speak_async(text: str) -> None:
    """TTS via edge-tts (async)."""
    communicate = edge_tts.Communicate(text, voice=VOICE)
    await communicate.save(OUTPUT_AUDIO)
    os.system(f"afplay {OUTPUT_AUDIO}")


async def speak(text: str) -> None:
    """TTS with optional Kokoro fallback."""
    if USE_KOKORO:
        try:
            from kokoro_onnx import Kokoro
            import soundfile as sf
            # Use Kokoro v1.0 models downloaded directly
            k = Kokoro("kokoro-v1.0.onnx", "voices-v1.0.bin")
            samples, sample_rate = k.create(text, voice="af_sarah", speed=1.0, lang="en-us")
            sf.write("/tmp/aida_kokoro.wav", samples, sample_rate)
            subprocess.run(["afplay", "/tmp/aida_kokoro.wav"])
            return
        except Exception as e:
            print(f"Kokoro failed, falling back to edge-tts: {e}")
    await speak_async(text)
