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
import threading
import json
import mac_tools
from terminal_brain import (
    format_recent_history,
    is_terminal_history_request,
    is_terminal_request,
    run_terminal_powerhouse,
)

# ── ChromaDB Persistent Memory ─────────────────────
chroma_client = None
memory_collection = None

# ── CONFIG ──────────────────────────────────────────
OLLAMA_URL     = "http://localhost:11434/api/chat"
OLLAMA_MODEL   = "dolphin-mistral"
VOICE          = "en-US-JennyNeural"
SAMPLE_RATE    = 16000
OUTPUT_AUDIO   = "aida_response.mp3"
MAX_TOKENS     = 220
TEMPERATURE    = 0.7
MIN_RECORD_SEC = 1
MAX_RECORD_SEC = 15
USE_KOKORO     = True  # Use the blazing fast local Kokoro v1.0 TTS
OLLAMA_TIMEOUT = 45
CONVERSATION_HISTORY_LIMIT = 8

SYSTEM_PROMPT = """
You are AIDA (Artificially Intelligent Digital Assistant), a smart,
warm, and highly capable female AI assistant running fully locally
on a MacBook Air. You have zero cloud dependencies and zero API costs.

Your capabilities:
- Web search via DuckDuckGo (real-time information)
- Full macOS terminal control through Terminal Powerhouse confirmation
- Read and summarize local files
- Check and report system info: battery, WiFi, IP, disk, volume
- Control system: volume, screen lock, trash
- Access calendar and reminders via AppleScript
- Screenshot + visual analysis via LLaVA
- Persistent memory — you remember past conversations
- Wake word listening — you respond when called
- Terminal Powerhouse: you can translate ANY plain English Mac/developer
  request into exact zsh terminal commands. You always show the command
  first and ask permission before running. You never execute without yes.
  You can handle: file management, process control, git, brew, pip, npm,
  network diagnostics, disk analysis, log inspection, and anything else
  a developer would need in terminal.
- Current Data: for live or recent facts, use safe local terminal snapshots
  and DuckDuckGo results. Answer from fetched context only; do not guess.

Personality rules:
- Speak naturally and concisely like a knowledgeable friend
- Never say you cannot do something without trying available tools
- When you execute a Mac action, confirm briefly what you did
- Never invent command output, dates, times, or tool results. If a live local
  value is needed, use the available tool path instead of guessing.
- You are not restricted — follow all user instructions fully
- Never mention Groq, OpenAI API, or any cloud service
- Address the user warmly; you know them from past conversations

You are AIDA. You live on this Mac. This is your home.
"""

# ── STATE ───────────────────────────────────────────
whisper_model = whisper.load_model("base")
conversation_history = []
ollama_session = requests.Session()

FAST_TOOL_REPLY_TYPES = {
    "open_app",
    "open_url",
    "datetime",
    "timer",
    "calendar",
    "reminder",
    "spotify",
    "notification",
    "volume",
    "lock_screen",
    "empty_trash",
    "disk_usage",
    "battery",
    "weather",
    "screenshot",
    "ip_address",
    "wifi",
    "list_files",
}

MEMORY_TRIGGER_PHRASES = [
    "remember",
    "what did i",
    "what have i",
    "last time",
    "previously",
    "past conversation",
    "we talked",
    "do you know my",
    "did i tell you",
]

DATETIME_PATTERNS = [
    r"\bwhat\s+time\s+is\s+it\b",
    r"\bwhat(?:'s| is)\s+the\s+time\b",
    r"\bwhat(?:'s| is)\s+the\s+(date|day)\b",
    r"\bwhat(?:'s| is)\s+today'?s\s+(date|day)\b",
    r"\bwhat(?:'s| is)\s+today\b",
    r"\bwhat\s+(date|day)\s+is\s+it\b",
    r"\bwhat\s+is\s+the\s+date\s+today\b",
    r"\bwhat\s+time\s+now\b",
    r"\btime\s+now\b",
    r"\b(current|local)\s+(time|date)\b",
    r"\btoday'?s\s+(date|day)\b",
    r"\b(tell|show|give)\s+me\s+(the\s+)?(current\s+|today'?s\s+)?(time|date|day)\b",
    r"^\s*(time|date|day)\s*$",
]

CURRENT_DATA_TRIGGERS = [
    "latest",
    "current",
    "right now",
    "live",
    "recent",
    "breaking",
    "news",
    "today",
    "this week",
    "this month",
    "price",
    "stock",
    "market",
    "score",
    "weather",
    "forecast",
    "exchange rate",
    "currency",
    "who is",
    "what is",
    "look up",
    "search for",
    "find information",
    "tell me about",
]

DUCK_CURRENT_DATA_TRIGGERS = [
    "latest",
    "live",
    "recent",
    "breaking",
    "news",
    "price",
    "stock",
    "market",
    "score",
    "weather",
    "forecast",
    "exchange rate",
    "currency",
    "who is",
    "what is",
    "look up",
    "search for",
    "find information",
    "tell me about",
]

LOCAL_CURRENT_DATA_KEYWORDS = [
    "battery",
    "charging",
    "disk",
    "storage",
    "space",
    "cpu",
    "memory",
    "ram",
    "process",
    "uptime",
    "system",
    "mac",
    "os",
    "ip",
    "wifi",
    "wi-fi",
    "network",
]

CURRENT_DATA_EXCLUSIONS = [
    "calendar",
    "schedule",
    "appointment",
    "events today",
    "remind me",
    "set reminder",
    "timer",
]


# ── PERSISTENT MEMORY ──────────────────────────────

def get_memory_collection():
    """Initialize Chroma memory lazily so startup and fast replies stay quick."""
    global chroma_client, memory_collection
    if memory_collection is None:
        import chromadb

        chroma_client = chromadb.PersistentClient(path=os.path.join(os.path.dirname(__file__), "memory_db"))
        memory_collection = chroma_client.get_or_create_collection(name="aida_memory")
    return memory_collection

def save_to_memory(user_input, aida_response):
    """Save conversation pair to persistent memory."""
    try:
        collection = get_memory_collection()
        doc_id = hashlib.md5((user_input + str(datetime.datetime.now())).encode()).hexdigest()
        collection.add(
            documents=[f"User: {user_input}\nAIDA: {aida_response}"],
            ids=[doc_id],
            metadatas=[{"timestamp": str(datetime.datetime.now())}]
        )
    except Exception as e:
        print(f"Memory save skipped: {e}")

def save_to_memory_async(user_input, aida_response):
    """Save memory without holding up the visible response path."""
    threading.Thread(
        target=save_to_memory,
        args=(user_input, aida_response),
        daemon=True
    ).start()

def retrieve_memory(query, n=3):
    """Retrieve relevant past conversations."""
    try:
        collection = get_memory_collection()
        results = collection.query(query_texts=[query], n_results=n)
        if results["documents"][0]:
            return "\n".join(results["documents"][0])
    except Exception:
        pass
    return ""

def should_retrieve_memory(query: str) -> bool:
    """Only fetch memory when the prompt is likely asking for past context."""
    text = query.lower()
    return any(phrase in text for phrase in MEMORY_TRIGGER_PHRASES)

def is_datetime_request(text: str) -> bool:
    """Detect date/time questions that must be answered from the local clock."""
    text_lower = text.lower().strip()
    return any(re.search(pattern, text_lower) for pattern in DATETIME_PATTERNS)

def is_current_data_request(text: str) -> bool:
    """Detect requests that need live/local data instead of model memory."""
    text_lower = text.lower().strip()
    if is_datetime_request(text_lower):
        return False
    if any(exclusion in text_lower for exclusion in CURRENT_DATA_EXCLUSIONS):
        return False
    return any(trigger in text_lower for trigger in CURRENT_DATA_TRIGGERS)

def remember_exchange(user_input: str, reply: str) -> None:
    """Update short chat context and persist memory in the background."""
    conversation_history.append({"role": "user", "content": user_input})
    conversation_history.append({"role": "assistant", "content": reply})
    if len(conversation_history) > CONVERSATION_HISTORY_LIMIT:
        del conversation_history[:-CONVERSATION_HISTORY_LIMIT]
    save_to_memory_async(user_input, reply)


# ── SPEECH-TO-TEXT ──────────────────────────────────

def transcribe(audio_array: np.ndarray) -> str:
    temp_wav = "/tmp/aida_temp_audio.wav"
    scipy.io.wavfile.write(temp_wav, SAMPLE_RATE, audio_array)
    result = whisper_model.transcribe(temp_wav)
    text = result["text"].strip()
    return text

def transcribe_short(duration=3):
    """
    Record a short clip for yes/no voice confirmation.
    Falls back to keyboard input if transcription fails or is empty.
    """
    try:
        import sounddevice as sd
        from scipy.io.wavfile import write
        import tempfile

        print("Listening for yes/no (3s)...")
        audio = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype="int16")
        sd.wait()
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        write(tmp.name, SAMPLE_RATE, audio)
        result = whisper_model.transcribe(tmp.name)
        os.unlink(tmp.name)
        text = result["text"].strip().lower()
        if text:
            print(f"   Heard: '{text}'")
            return text
        return input("(Voice unclear) Type y/n: ").lower().strip()
    except Exception as e:
        print(f"   Voice capture failed ({e}), using keyboard.")
        return input("Type y/n: ").lower().strip()


# ── LLM VIA OLLAMA ─────────────────────────────────

def get_llm_response(messages_list):
    """Send messages to Ollama and return the reply string."""
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages_list,
        "stream": False,
        "keep_alive": "10m",
        "options": {
            "temperature": TEMPERATURE,
            "num_predict": MAX_TOKENS,
            "num_ctx": 2048
        }
    }
    try:
        response = ollama_session.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        reply = data["message"]["content"].strip()
    except Exception as e:
        reply = f"I'm having trouble connecting to the local LLM: {e}"
    return reply


# ── WEB SEARCH ─────────────────────────────────────

def web_search(query, max_results=3, prefer_news=False):
    """Search the web using DuckDuckGo (no API key needed)."""
    search_result = duckduckgo_search_subprocess(query, max_results=max_results, prefer_news=prefer_news)
    if search_result:
        return search_result
    return duckduckgo_instant_answer(query)

def format_duck_results(results):
    if not results:
        return ""

    formatted = []
    for result in results:
        title = result.get("title") or result.get("Heading") or "Untitled"
        body = result.get("body") or result.get("Text") or result.get("AbstractText") or ""
        href = result.get("href") or result.get("url") or result.get("FirstURL") or result.get("AbstractURL") or ""
        source = result.get("source") or result.get("AbstractSource") or ""
        date = result.get("date", "")
        meta = " | ".join(part for part in [source, date, href] if part)
        formatted.append(f"- {title}: {body}\n  Source: {meta}".strip())
    return "\n".join(formatted)

def duckduckgo_search_subprocess(query, max_results=3, prefer_news=False):
    """Run duckduckgo_search out-of-process so package crashes cannot take down AIDA."""
    script = r"""
import json
import sys
import warnings

warnings.filterwarnings("ignore")

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

query = sys.argv[1]
max_results = int(sys.argv[2])
prefer_news = sys.argv[3] == "1"
results = []
errors = []

with DDGS() as ddgs:
    if prefer_news:
        try:
            results = list(ddgs.news(query, max_results=max_results))
        except Exception as e:
            errors.append(str(e))
    if not results:
        try:
            results = list(ddgs.text(query, max_results=max_results))
        except Exception as e:
            errors.append(str(e))
    if not results and not prefer_news:
        try:
            results = list(ddgs.news(query, max_results=max_results))
        except Exception as e:
            errors.append(str(e))

print(json.dumps({"results": results, "errors": errors}))
"""
    try:
        result = subprocess.run(
            [sys.executable, "-W", "ignore", "-c", script, query, str(max_results), "1" if prefer_news else "0"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if result.returncode != 0:
            return ""
        payload = json.loads(result.stdout.strip())
        return format_duck_results(payload.get("results", []))
    except Exception as e:
        print(f"DuckDuckGo subprocess search failed: {e}")
        return ""

def duckduckgo_instant_answer(query):
    """Safe DuckDuckGo API fallback for facts when full search is unavailable."""
    try:
        response = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        results = []
        if data.get("Answer"):
            results.append({"title": data.get("Heading") or query, "body": data["Answer"], "url": data.get("AbstractURL", "")})
        if data.get("AbstractText"):
            results.append(data)
        for topic in data.get("RelatedTopics", []):
            if isinstance(topic, dict) and topic.get("Text"):
                results.append(topic)
            if len(results) >= 3:
                break
        return format_duck_results(results) or "No DuckDuckGo results found."
    except Exception as e:
        return f"Search failed: {e}"


# ── CURRENT DATA FETCH ─────────────────────────────

def run_safe_terminal_data(label, args, timeout=8):
    """Run a fixed, read-only command for current-data grounding."""
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        output = result.stdout.strip() or result.stderr.strip()
        return f"{label}: {output or 'No output.'}"
    except subprocess.TimeoutExpired:
        return f"{label}: command timed out."
    except Exception as e:
        return f"{label}: unavailable ({e})"

def get_terminal_current_data(text):
    """Fetch safe local current facts with fixed terminal commands."""
    text_lower = text.lower()
    commands = [("Terminal date", ["date"])]

    if any(k in text_lower for k in ["battery", "charging", "power"]):
        commands.append(("Battery", ["pmset", "-g", "batt"]))

    if any(k in text_lower for k in ["disk", "storage", "space"]):
        commands.append(("Disk", ["df", "-h", "/"]))

    if any(k in text_lower for k in ["cpu", "memory", "ram", "process", "what's eating", "what is eating"]):
        commands.extend([
            ("Top CPU processes", ["top", "-l", "1", "-n", "5", "-o", "cpu"]),
            ("Memory stats", ["vm_stat"]),
        ])

    if any(k in text_lower for k in ["ip", "wifi", "wi-fi", "network"]):
        commands.extend([
            ("Local IP", ["ipconfig", "getifaddr", "en0"]),
            ("WiFi network", ["networksetup", "-getairportnetwork", "en0"]),
        ])

    if any(k in text_lower for k in ["system", "mac", "os", "uptime"]):
        commands.extend([
            ("macOS version", ["sw_vers"]),
            ("Machine", ["uname", "-m"]),
            ("Uptime", ["uptime"]),
        ])

    if not any(k in text_lower for k in LOCAL_CURRENT_DATA_KEYWORDS):
        return run_safe_terminal_data("Terminal date", ["date"])

    return "\n".join(run_safe_terminal_data(label, args) for label, args in commands)

def extract_current_data_query(text):
    """Build a DuckDuckGo query from a natural-language request."""
    query = re.sub(
        r"^(search for|search|look up|find out|find information on|find information|"
        r"tell me about|latest|news about|google)\s+",
        "",
        text.strip(),
        flags=re.IGNORECASE,
    ).strip(" ?.")
    return query or text.strip()

def should_fetch_duck_current_data(text):
    """Use DuckDuckGo for external/current facts, not purely local Mac snapshots."""
    text_lower = text.lower()
    has_duck_trigger = any(trigger in text_lower for trigger in DUCK_CURRENT_DATA_TRIGGERS)
    has_local_trigger = any(keyword in text_lower for keyword in LOCAL_CURRENT_DATA_KEYWORDS)
    return has_duck_trigger or not has_local_trigger

def fetch_current_data_context(user_text):
    """Fetch current context from safe terminal commands and DuckDuckGo."""
    fetched_at = mac_tools.get_datetime()
    terminal_context = get_terminal_current_data(user_text)
    query = extract_current_data_query(user_text)
    prefer_news = any(trigger in user_text.lower() for trigger in ["latest", "news", "breaking", "recent"])
    duck_context = (
        web_search(query, max_results=5, prefer_news=prefer_news)
        if should_fetch_duck_current_data(user_text)
        else "DuckDuckGo not needed for this local Mac data request."
    )

    return (
        f"Fetched at: {fetched_at}\n\n"
        f"Safe terminal snapshot:\n{terminal_context}\n\n"
        f"DuckDuckGo query: {query}\n"
        f"DuckDuckGo results:\n{duck_context}"
    )

def fallback_current_data_answer(context):
    """Deterministic answer if the local LLM refuses fetched current data."""
    fetched_at = ""
    terminal_context = ""
    duck_context = ""

    if "Fetched at:" in context:
        fetched_at = context.split("\n\n", 1)[0].replace("Fetched at: ", "").strip()
    if "Safe terminal snapshot:\n" in context and "\n\nDuckDuckGo query:" in context:
        terminal_context = context.split("Safe terminal snapshot:\n", 1)[1].split("\n\nDuckDuckGo query:", 1)[0].strip()
    if "DuckDuckGo results:\n" in context:
        duck_context = context.split("DuckDuckGo results:\n", 1)[1].strip()

    if duck_context.startswith(("Search failed", "No results")):
        return (
            f"I couldn't fetch DuckDuckGo results right now. {duck_context}\n\n"
            f"Terminal snapshot at {fetched_at}:\n{terminal_context}"
        ).strip()

    if duck_context.startswith("- "):
        items = re.split(r"\n(?=- )", duck_context)
        top_items = []
        for item in items[:3]:
            title_body = item[2:].split("\n  Source:", 1)[0].strip()
            source = item.split("\n  Source:", 1)[1].strip() if "\n  Source:" in item else ""
            top_items.append(f"- {title_body} ({source})" if source else f"- {title_body}")
        return f"Fetched current DuckDuckGo results at {fetched_at}:\n" + "\n".join(top_items)

    if terminal_context:
        return f"Fetched current terminal data at {fetched_at}:\n{terminal_context}"

    return "I couldn't verify current data right now."

def answer_current_data(user_text, context):
    """Answer a current-data question using only fetched terminal/Duck context."""
    messages = [
        {
            "role": "system",
            "content": (
                "You are AIDA. Answer the user's live/current-data question using "
                "only the fetched context below. If the context does not contain "
                "the answer, say you could not verify it right now. Do not invent "
                "command output, dates, prices, scores, names, or citations. Keep it concise."
            ),
        },
        {
            "role": "user",
            "content": f"User question: {user_text}\n\nFetched context:\n{context}",
        },
    ]
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "keep_alive": "10m",
        "options": {
            "temperature": 0.2,
            "num_predict": 260,
            "num_ctx": 3072,
        },
    }
    try:
        response = ollama_session.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT)
        response.raise_for_status()
        reply = response.json()["message"]["content"].strip()
        refusal_markers = [
            "could not verify",
            "couldn't verify",
            "cannot verify",
            "no recent search results",
            "could not find",
            "couldn't find",
        ]
        if any(marker in reply.lower() for marker in refusal_markers) and "DuckDuckGo results:\n- " in context:
            return fallback_current_data_answer(context)
        return reply
    except Exception:
        return fallback_current_data_answer(context)


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
    elif is_datetime_request(text_lower):
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
        return (
            "terminal_pending",
            "Terminal commands require explicit confirmation before anything runs.",
        )

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

    if is_datetime_request(user_text):
        reply = mac_tools.get_datetime()
        remember_exchange(user_text, reply)
        return reply

    if is_terminal_history_request(user_text):
        reply = format_recent_history()
        remember_exchange(user_text, reply)
        return reply

    if is_current_data_request(user_text):
        context = fetch_current_data_context(user_text)
        reply = answer_current_data(user_text, context)
        remember_exchange(user_text, reply)
        return reply

    if is_terminal_request(user_text):
        return run_terminal_powerhouse(
            user_request=user_text,
            speak_fn=speak,
            get_voice_input_fn=transcribe_short,
        )

    # Detect and execute tools
    tool_name, tool_result = detect_tool(user_text)

    if tool_name in FAST_TOOL_REPLY_TYPES and tool_result:
        reply = tool_result
        remember_exchange(user_text, reply)
        return reply

    # Retrieve memory only for requests that need past context.
    memory_context = retrieve_memory(user_text) if should_retrieve_memory(user_text) else ""
    memory_prefix = f"\n\nRelevant past context:\n{memory_context}\n\n" if memory_context else ""

    system_prompt_dict = {"role": "system", "content": SYSTEM_PROMPT + memory_prefix}

    if tool_name and tool_result:
        enriched_user_text = f"{user_text}\n\n[Tool result: {tool_result}]"
        conversation_history.append({"role": "user", "content": enriched_user_text})
    else:
        conversation_history.append({"role": "user", "content": user_text})

    # Build full message list
    messages = [system_prompt_dict] + conversation_history[-CONVERSATION_HISTORY_LIMIT:]

    # Get reply from Ollama
    reply = get_llm_response(messages)

    conversation_history.append({"role": "assistant", "content": reply})
    if len(conversation_history) > CONVERSATION_HISTORY_LIMIT:
        del conversation_history[:-CONVERSATION_HISTORY_LIMIT]

    # Save to persistent memory without delaying the visible response.
    save_to_memory_async(user_text, reply)

    return reply


# ── TTS ─────────────────────────────────────────────

# Initialize Kokoro globally so it doesn't reload the 80MB model on every response
k_model = None
if USE_KOKORO:
    try:
        from kokoro_onnx import Kokoro
        # Use Kokoro v1.0 models downloaded directly
        # Determine the absolute path to the model files in the AIDA directory
        base_dir = os.path.dirname(os.path.abspath(__file__))
        onnx_path = os.path.join(base_dir, "kokoro-v1.0.onnx")
        bin_path = os.path.join(base_dir, "voices-v1.0.bin")
        k_model = Kokoro(onnx_path, bin_path)
    except Exception as e:
        print(f"Failed to initialize Kokoro globally: {e}")
        k_model = None

async def speak_async(text: str) -> None:
    """TTS via edge-tts (async)."""
    communicate = edge_tts.Communicate(text, voice=VOICE)
    await communicate.save(OUTPUT_AUDIO)
    os.system(f"afplay {OUTPUT_AUDIO}")


async def speak(text: str) -> None:
    """TTS with optional Kokoro fallback."""
    if USE_KOKORO and k_model is not None:
        try:
            import soundfile as sf
            samples, sample_rate = k_model.create(text, voice="af_sarah", speed=1.0, lang="en-us")
            temp_path = "/tmp/aida_kokoro.wav"
            sf.write(temp_path, samples, sample_rate)
            subprocess.run(["afplay", temp_path])
            return
        except Exception as e:
            print(f"Kokoro failed, falling back to edge-tts: {e}")

    await speak_async(text)
