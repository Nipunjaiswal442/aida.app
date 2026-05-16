import datetime
import inspect
import json
import os
import re
import subprocess
import warnings

import pyperclip
import requests

warnings.filterwarnings("ignore")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(BASE_DIR, "terminal_history.json")

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "dolphin-mistral"

# These patterns are never executed, regardless of user confirmation.
BLACKLISTED_PATTERNS = [
    r"\brm\s+(-[^\s]*r[^\s]*f|-[^\s]*f[^\s]*r)\s+/(?!\w)",
    r"\b(?:sudo\s+)?rm\s+[^;\n]*(-[^\s]*r[^\s]*f|-[^\s]*f[^\s]*r)[^;\n]*(?:--\s+)?/(?!\w)",
    r"\brm\s+(-[^\s]*r[^\s]*f|-[^\s]*f[^\s]*r)\s+~",
    r"\b(?:sudo\s+)?rm\s+[^;\n]*(-[^\s]*r[^\s]*f|-[^\s]*f[^\s]*r)[^;\n]*(?:--\s+)?~",
    r"\bsudo\s+rm\s+(-[^\s]*r[^\s]*f|-[^\s]*f[^\s]*r)\s+/(?!\w)",
    r"\bmkfs\b",
    r"\bdd\s+if=.*of=/dev/(disk|rdisk|sd|nvme)",
    r"\bchmod\s+-R\s+777\s+/(?!\w)",
    r":\(\)\s*\{\s*:\|:\s*&\s*\}\s*;:",
    r">\s*/dev/(disk|rdisk|sd|nvme)",
    r"\bdiskutil\s+(eraseDisk|partitionDisk|secureErase)\b",
]

TERMINAL_SYSTEM_PROMPT = """
You are AIDA's Terminal Intelligence engine running on macOS (Apple Silicon, macOS Sonoma+).

Your ONLY job is to translate plain English into ONE correct, safe macOS terminal command.

Rules:
- Output ONLY the raw terminal command. Nothing else.
- No explanation, no markdown, no backticks, no preamble.
- No multi-line scripts unless the user explicitly asks for a script.
- Use macOS-native commands (zsh, brew, osascript, defaults, launchctl etc.)
- Prefer safe, non-destructive commands.
- If the request is ambiguous, produce the most conservative interpretation.
- If the request cannot be translated to a single safe command, output exactly:
  UNSAFE: <brief reason>

Examples:
User: show me what's eating my CPU
Command: top -l 1 -n 10 -o cpu

User: how much space do I have left
Command: df -h /

User: list all running processes with their memory usage
Command: ps aux -m | head -20

User: install tree using homebrew
Command: brew install tree

User: show me my public IP address
Command: curl -s ifconfig.me

User: find all files larger than 1GB in my downloads folder
Command: find ~/Downloads -size +1G -type f

User: show me which ports are open on my mac
Command: sudo lsof -iTCP -sTCP:LISTEN -n -P

User: compress the folder projects into a zip file
Command: zip -r projects.zip ~/projects

User: show me the last 50 lines of the system log
Command: log show --last 1h --style compact | tail -50

User: check if git is installed
Command: git --version

User: make a new folder called experiments on my desktop
Command: mkdir ~/Desktop/experiments

User: delete all .DS_Store files in the current directory recursively
Command: find . -name '.DS_Store' -type f -delete
"""

EXPLICIT_TERMINAL_TRIGGERS = [
    "terminal",
    "run command",
    "execute",
    "shell command",
    "in terminal",
    "command line",
    "via terminal",
    "using terminal",
    "run this",
    "run that",
    "run a command",
]

IMPLICIT_TERMINAL_TRIGGERS = [
    "what's eating",
    "what is eating",
    "what's using",
    "what is using",
    "cpu usage",
    "memory usage",
    "ram usage",
    "disk space",
    "how much space",
    "storage left",
    "running processes",
    "active processes",
    "which processes",
    "ports open",
    "listening ports",
    "network connections",
    "system info",
    "mac info",
    "os version",
    "uptime",
    "find all files",
    "find files",
    "find folders",
    "search for files",
    "delete all",
    "remove all",
    "clean up",
    "compress",
    "zip",
    "unzip",
    "extract",
    "move files",
    "copy files",
    "rename files",
    "create folder",
    "make folder",
    "make directory",
    "new folder",
    "file permissions",
    "change permissions",
    "install",
    "uninstall",
    "brew install",
    "pip install",
    "npm install",
    "git status",
    "git log",
    "git pull",
    "git push",
    "git clone",
    "check if installed",
    "which version",
    "python version",
    "node version",
    "check version",
    "start server",
    "stop server",
    "kill process",
    "kill port",
    "my ip",
    "public ip",
    "ping",
    "check internet",
    "network speed",
    "wifi info",
    "dns lookup",
    "trace route",
    "show log",
    "system log",
    "error log",
    "crash log",
    "last 50 lines",
    "tail log",
    "monitor",
    "environment variable",
    "export variable",
    "path variable",
    "cron job",
    "schedule task",
    "launch agent",
    "update brew",
    "brew update",
    "brew upgrade",
    "brew list",
    "homebrew",
]

TERMINAL_HISTORY_TRIGGERS = [
    "command history",
    "what commands have i run",
    "show history",
    "terminal history",
    "past commands",
]


def is_terminal_history_request(text):
    text_lower = text.lower()
    return any(trigger in text_lower for trigger in TERMINAL_HISTORY_TRIGGERS)


def is_terminal_request(text):
    """Return True when a request implies a system or terminal action."""
    text_lower = text.lower()
    triggers = EXPLICIT_TERMINAL_TRIGGERS + IMPLICIT_TERMINAL_TRIGGERS
    return any(trigger in text_lower for trigger in triggers)


def is_blacklisted(command):
    """Check a command against the hard safety blacklist."""
    for pattern in BLACKLISTED_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return True
    return False


def translate_to_command(user_request):
    """Use Ollama to translate plain English into one terminal command."""
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": TERMINAL_SYSTEM_PROMPT},
            {"role": "user", "content": user_request},
        ],
        "stream": False,
        "keep_alive": "10m",
        "options": {
            "temperature": 0.1,
            "num_predict": 120,
        },
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)
        response.raise_for_status()
        command = response.json()["message"]["content"].strip()
        return command.replace("`", "").strip()
    except Exception as e:
        return f"ERROR: Could not generate command - {e}"


def summarize_output(output, original_request):
    """Summarize long terminal output for speech."""
    if len(output) < 400:
        return output

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are AIDA. Summarize terminal output in 2-3 natural "
                    "spoken sentences. Be specific about key numbers or findings. No markdown."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Original request: {original_request}\n\n"
                    f"Terminal output:\n{output[:3000]}\n\nSummarize for the user."
                ),
            },
        ],
        "stream": False,
        "keep_alive": "10m",
        "options": {
            "temperature": 0.2,
            "num_predict": 120,
        },
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()["message"]["content"].strip()
    except Exception:
        return output[:400] + "... (output truncated)"


def execute_command(command, timeout=30):
    """Execute a confirmed command in zsh and return stdout/stderr."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            executable="/bin/zsh",
        )
        output = result.stdout.strip()
        error = result.stderr.strip()
        if output and error:
            return output + "\n" + error
        return output or error or "Command completed with no output."
    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout} seconds."
    except Exception as e:
        return f"Execution error: {e}"


def copy_command(command):
    """Copy a generated command to the clipboard when possible."""
    try:
        pyperclip.copy(command)
        return True
    except Exception:
        return False


def log_command(request, command, output="", confirmed=False):
    """Log generated terminal commands to a local JSON history file."""
    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "request": request,
        "command": command,
        "confirmed": confirmed,
        "output": output[:500] if output else "",
    }

    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []

    history.append(entry)
    history = history[-200:]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)


def get_recent_history(limit=5):
    """Return the most recent terminal history entries."""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
        return history[-limit:]
    except Exception:
        return []


def format_recent_history(limit=5):
    """Return a concise natural-language history summary."""
    history = get_recent_history(limit)
    if not history:
        return "No terminal history found yet."

    lines = []
    for item in history:
        date = item.get("timestamp", "")[:10] or "unknown date"
        command = item.get("command", "")
        status = "ran" if item.get("confirmed") else "cancelled"
        lines.append(f"- {command} ({status}, {date})")
    return "Here are your recent terminal commands:\n" + "\n".join(lines)


def _speak(speak_fn, text):
    if not speak_fn:
        return
    result = speak_fn(text)
    if inspect.isawaitable(result):
        try:
            import asyncio

            asyncio.run(result)
        except RuntimeError:
            pass


def _confirmation_matches(confirmation, words):
    confirmation = confirmation.lower().strip()
    return any(re.search(rf"\b{re.escape(word)}\b", confirmation) for word in words)


def run_terminal_powerhouse(user_request, speak_fn, get_voice_input_fn=None, gui_confirm_fn=None):
    """
    Translate a plain-English request into a terminal command, ask for explicit
    confirmation, execute only after yes, and return the final display text.
    """
    print("\n" + "-" * 55)
    print("TERMINAL POWERHOUSE")
    print("-" * 55)

    print(f"Translating: '{user_request}'")
    _speak(speak_fn, "Generating the terminal command...")
    command = translate_to_command(user_request)

    if command.startswith("UNSAFE:"):
        reason = command.replace("UNSAFE:", "").strip()
        log_command(user_request, command, output=reason, confirmed=False)
        msg = f"I can't generate that command safely. {reason}"
        _speak(speak_fn, msg)
        print(f"BLOCKED: {msg}")
        return msg

    if command.startswith("ERROR:"):
        log_command(user_request, command, output="", confirmed=False)
        _speak(speak_fn, "Sorry, I couldn't generate the command. Is Ollama running?")
        return command

    if is_blacklisted(command):
        log_command(user_request, command, output="Blacklisted command.", confirmed=False)
        msg = "That command is on my permanent safety blacklist. I won't run it even if asked."
        _speak(speak_fn, msg)
        print(f"BLACKLISTED: {command}")
        return msg

    print(f"\nGenerated Command:\n\n   {command}\n")
    if copy_command(command):
        print("   (copied to clipboard)")

    _speak(speak_fn, f"Here is the command I'll run: {command}")
    _speak(speak_fn, "Should I run this? Say yes or no.")
    print("-" * 55)

    confirmation = ""
    if gui_confirm_fn:
        confirmation = gui_confirm_fn(command)
    elif get_voice_input_fn:
        try:
            confirmation = get_voice_input_fn().lower().strip()
            print(confirmation)
        except Exception:
            confirmation = input("Run this command? (y/n): ").lower().strip()
    else:
        confirmation = input("Run this command? (y/n): ").lower().strip()

    yes_words = ["yes", "y", "yeah", "yep", "sure", "go ahead", "do it", "run it", "proceed", "confirm", "ok", "okay", "affirmative"]
    no_words = ["no", "n", "nope", "cancel", "stop", "abort", "don't", "negative", "nevermind", "skip"]

    confirmed = _confirmation_matches(confirmation, yes_words)
    denied = _confirmation_matches(confirmation, no_words)

    if denied or not confirmed:
        log_command(user_request, command, output="", confirmed=False)
        msg = "Got it. Command cancelled." if denied else "Didn't catch a clear yes, so I cancelled it."
        _speak(speak_fn, msg)
        print(f"CANCELLED: {msg}")
        return msg

    print("\nExecuting...")
    _speak(speak_fn, "Running it now.")
    output = execute_command(command)
    log_command(user_request, command, output=output, confirmed=True)

    print(f"\nOutput:\n{output}\n")
    print("-" * 55)

    summary = summarize_output(output, user_request)
    _speak(speak_fn, summary)
    return f"Command: {command}\n\nOutput:\n{output}"
