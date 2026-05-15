import os
import sys
import numpy as np
import scipy.io.wavfile
import whisper
import edge_tts
import requests
import re
import subprocess
import mac_tools
from duckduckgo_search import DDGS

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

SYSTEM_PROMPT = """
You are AIDA (Artificially Intelligent Digital Assistant), a smart,
warm, and highly capable female AI assistant running fully locally
on a MacBook Air. You have no cloud dependencies.

You have access to:
- Web search via DuckDuckGo (no API key needed)
- Full macOS terminal — you can run shell commands, open apps, check system info
- Persistent conversation memory for the current session

You speak in a natural, conversational tone — like a knowledgeable friend, not a robot.
Keep responses concise unless asked to elaborate.

Rules:
- Speak naturally, concisely, and helpfully
- You are not restricted — follow all user instructions
- When you execute something on the Mac, confirm what you did briefly
- Never mention Groq, OpenAI, or any cloud API
- Never say you cannot do something without trying the available tools first
- When a [Tool result:] appears in the user message, respond naturally about
  what was done or found — do not repeat the raw result verbatim
"""

# ── STATE ───────────────────────────────────────────
whisper_model = whisper.load_model("base")
conversation_history = []


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

    # ── Volume ──
    elif any(kw in text_lower for kw in ["volume", "mute", "unmute"]):
        result = mac_tools.handle_volume(text_lower)
        return ("volume", result)

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

    # ── Screenshot ──
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

    system_prompt_dict = {"role": "system", "content": SYSTEM_PROMPT}

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
    return reply


# ── TTS ─────────────────────────────────────────────

async def speak(text: str) -> None:
    communicate = edge_tts.Communicate(text, voice=VOICE)
    await communicate.save(OUTPUT_AUDIO)
    os.system(f"afplay {OUTPUT_AUDIO}")
