import os
import subprocess
import datetime
import threading
import requests
import json
import re

timer_callback = None

def register_timer_callback(fn):
    global timer_callback
    timer_callback = fn

def open_app(app_name: str) -> str:
    # Common mappings
    mappings = {
        "spotify": "Spotify",
        "vs code": "Visual Studio Code",
        "vscode": "Visual Studio Code",
        "chrome": "Google Chrome",
        "safari": "Safari",
        "terminal": "Terminal",
        "notes": "Notes",
        "calculator": "Calculator",
        "finder": "Finder",
        "music": "Music",
        "messages": "Messages",
        "whatsapp": "WhatsApp",
        "notion": "Notion",
        "figma": "Figma"
    }
    
    app_name_lower = app_name.lower()
    normalized_name = mappings.get(app_name_lower, app_name.title())
    
    try:
        res = subprocess.run(["open", "-a", normalized_name], capture_output=True, text=True)
        if res.returncode == 0:
            return f"Opened {normalized_name} successfully."
        else:
            return f"Could not find app: {normalized_name}."
    except Exception as e:
        return f"Could not find app: {normalized_name}. Error: {str(e)}"

def get_datetime() -> str:
    now = datetime.datetime.now().astimezone()
    timezone = now.tzname() or now.strftime("%z")
    return f"Current date and time: {now.strftime('%A, %d %B %Y, %I:%M %p')} {timezone}"

def set_timer(seconds: int) -> str:
    def fire():
        os.system("afplay /System/Library/Sounds/Glass.aiff")
        if timer_callback:
            # Let's send a neat message based on the duration
            if seconds >= 3600:
                amount = seconds // 3600
                unit = "hour" if amount == 1 else "hours"
            elif seconds >= 60:
                amount = seconds // 60
                unit = "minute" if amount == 1 else "minutes"
            else:
                amount = seconds
                unit = "second" if amount == 1 else "seconds"
            timer_callback(f"Timer complete! Your {amount} {unit} timer is done.")
            
    threading.Timer(seconds, fire).start()
    return f"Timer set for {seconds} seconds."

def handle_volume(text: str) -> str:
    text_lower = text.lower()
    if "mute" in text_lower and "unmute" not in text_lower:
        subprocess.run(["osascript", "-e", "set volume output muted true"])
        return "System volume muted."
    elif "unmute" in text_lower:
        subprocess.run(["osascript", "-e", "set volume output muted false"])
        return "System volume unmuted."
    elif "turn volume up" in text_lower or "turn up" in text_lower:
        res = subprocess.run(["osascript", "-e", "output volume of (get volume settings)"], capture_output=True, text=True)
        try:
            current = int(res.stdout.strip())
            new_vol = min(100, current + 20)
            return set_volume(new_vol)
        except:
            return "Could not adjust volume."
    elif "turn volume down" in text_lower or "turn down" in text_lower:
        res = subprocess.run(["osascript", "-e", "output volume of (get volume settings)"], capture_output=True, text=True)
        try:
            current = int(res.stdout.strip())
            new_vol = max(0, current - 20)
            return set_volume(new_vol)
        except:
            return "Could not adjust volume."
    else:
        # Extract number if "set volume to [N]"
        match = re.search(r'\b(\d+)\b', text_lower)
        if match:
            level = int(match.group(1))
            return set_volume(level)
        return "Could not determine volume level."

def set_volume(level: int) -> str:
    subprocess.run(["osascript", "-e", f"set volume output volume {level}"])
    return f"System volume set to {level}%."

def check_battery() -> str:
    res = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True)
    out = res.stdout
    match_pct = re.search(r'(\d+)%', out)
    pct = match_pct.group(1) if match_pct else "unknown"
    if "AC Power" in out or "charging" in out:
        status = "currently charging"
    else:
        status = "not plugged in"
    return f"Battery is at {pct}%, {status}."

def open_url(url: str) -> str:
    mappings = {
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
        "github": "https://www.github.com",
        "gmail": "https://mail.google.com",
        "twitter": "https://www.twitter.com",
        "reddit": "https://www.reddit.com",
        "netflix": "https://www.netflix.com"
    }
    target = mappings.get(url.lower(), url if url.startswith("http") else f"https://{url}")
    try:
        subprocess.run(["open", target])
        return f"Opened {url} in your browser."
    except Exception as e:
        return f"Failed to open url {url}."

def get_weather(city: str) -> str:
    target_city = city if city else ""
    try:
        res = requests.get(f"https://wttr.in/{target_city}?format=3", timeout=5)
        if res.status_code == 200:
            return f"Weather{(' in ' + city.title()) if city else ''}: {res.text.strip()}"
        return f"Could not fetch weather for {city or 'your location'} right now."
    except:
        return f"Could not fetch weather for {city or 'your location'} right now."

def take_screenshot() -> str:
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = f"AIDA_screenshot_{timestamp}.png"
    filepath = os.path.expanduser(f"~/Desktop/{filename}")
    try:
        subprocess.run(["screencapture", "-x", filepath])
        return f"Screenshot saved to your Desktop as {filename}"
    except Exception as e:
        return "Failed to take screenshot."


# ── Calendar & Reminders (AppleScript) ─────────────

def get_todays_events():
    """Fetch today's calendar events via AppleScript."""
    script = '''
    tell application "Calendar"
        set today to current date
        set startOfDay to today - (time of today)
        set endOfDay to startOfDay + 86399
        set eventList to ""
        repeat with c in every calendar
            repeat with e in every event of c
                if start date of e >= startOfDay and start date of e <= endOfDay then
                    set eventList to eventList & summary of e & " at " & (start date of e as string) & linefeed
                end if
            end repeat
        end repeat
        if eventList is "" then
            return "No events today."
        else
            return eventList
        end if
    end tell
    '''
    try:
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=10)
        return result.stdout.strip() or "Could not read calendar."
    except Exception:
        return "Could not read calendar."

def add_reminder(title, notes=""):
    """Add a reminder via AppleScript."""
    # Escape quotes in title/notes for AppleScript safety
    safe_title = title.replace('"', '\\"')
    safe_notes = notes.replace('"', '\\"')
    script = f'''
    tell application "Reminders"
        make new reminder with properties {{name:"{safe_title}", body:"{safe_notes}"}}
    end tell
    '''
    try:
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=10)
        return f"Reminder '{title}' added."
    except Exception:
        return f"Could not add reminder '{title}'."


# ── System Controls ────────────────────────────────

def lock_screen():
    """Lock the screen (display sleep)."""
    subprocess.run(["pmset", "displaysleepnow"])
    return "Screen locked."

def empty_trash():
    """Empty the Trash via AppleScript."""
    try:
        subprocess.run(["osascript", "-e", 'tell application "Finder" to empty trash'],
                        capture_output=True, timeout=10)
        return "Trash emptied."
    except Exception:
        return "Could not empty trash."

def get_disk_usage():
    """Get disk usage for the main volume."""
    try:
        result = subprocess.run(
            "df -h / | tail -1 | awk '{print \"Used: \"$3\" / \"$2\" (\"$5\")\"}'",
            shell=True, capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip() or "Could not determine disk usage."
    except Exception:
        return "Could not determine disk usage."


def web_search(query: str) -> str:
    try:
        res = requests.get(f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1", timeout=5)
        if res.status_code == 200:
            data = res.json()
            abstract = data.get("AbstractText", "")
            if abstract:
                return abstract
            related = data.get("RelatedTopics", [])
            if related and "Text" in related[0]:
                return related[0]["Text"]
        return "I couldn't find a quick answer for that. Try asking me something more specific."
    except:
        return "I couldn't find a quick answer for that. Try asking me something more specific."


# ── Spotify / Music Control ────────────────────────

def control_spotify(command: str) -> str:
    """Control Spotify playback via AppleScript."""
    valid_commands = ["play", "pause", "next track", "previous track"]
    if command not in valid_commands:
        return f"Unknown Spotify command: {command}"
        
    script = f'''
    tell application "Spotify"
        {command}
    end tell
    '''
    try:
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
        return f"Spotify: {command} executed."
    except Exception:
        return "Could not control Spotify. Make sure the app is running."


# ── Notification Center ────────────────────────────

def send_notification(message: str, title: str = "AIDA") -> str:
    """Send a native macOS notification."""
    safe_title = title.replace('"', '\\"')
    safe_message = message.replace('"', '\\"')
    
    script = f'display notification "{safe_message}" with title "{safe_title}"'
    try:
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
        return "Notification sent."
    except Exception:
        return "Failed to send notification."
