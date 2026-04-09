import ssl
ssl._create_default_https_context = ssl._create_unverified_context
import os
import sys
import asyncio
import tempfile
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import whisper
import edge_tts
from groq import Groq

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
VOICE = "en-US-JennyNeural"          # Female voice for AIDA
SAMPLE_RATE = 16000
RECORD_SECONDS = 5                   # How long to listen each time
OUTPUT_AUDIO = "aida_response.mp3"

SYSTEM_PROMPT = """
You are AIDA (Artificially Intelligent Digital Assistant), a smart, 
warm, and helpful female AI assistant. You speak in a natural, 
conversational tone — like a knowledgeable friend, not a robot.
Keep responses concise unless asked to elaborate.
You address the user by name if they tell you it.
"""

# ─────────────────────────────────────────────
#  INIT
# ─────────────────────────────────────────────
client = Groq(api_key=GROQ_API_KEY)
whisper_model = whisper.load_model("base")   # Downloads ~140MB once
conversation_history = []

# ─────────────────────────────────────────────
#  STEP A: RECORD AUDIO FROM MIC
# ─────────────────────────────────────────────
def record_audio(duration=RECORD_SECONDS):
    print(f"\n🎙️  Listening for {duration} seconds... (speak now)")
    audio = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype='int16'
    )
    sd.wait()
    print("✅  Done recording.")
    return audio

# ─────────────────────────────────────────────
#  STEP B: TRANSCRIBE AUDIO → TEXT (Whisper)
# ─────────────────────────────────────────────
def transcribe(audio_data):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        write(f.name, SAMPLE_RATE, audio_data)
        result = whisper_model.transcribe(f.name)
    text = result["text"].strip()
    print(f"🗣️  You said: {text}")
    return text

# ─────────────────────────────────────────────
#  STEP C: GET RESPONSE FROM GROQ (LLM)
# ─────────────────────────────────────────────
def ask_aida(user_input):
    conversation_history.append({
        "role": "user",
        "content": user_input
    })

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",   # Fast + free on Groq
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            *conversation_history
        ],
        max_tokens=300,
        temperature=0.7
    )

    reply = response.choices[0].message.content.strip()

    conversation_history.append({
        "role": "assistant",
        "content": reply
    })

    print(f"🤖  AIDA: {reply}")
    return reply

# ─────────────────────────────────────────────
#  STEP D: SPEAK THE RESPONSE (edge-tts)
# ─────────────────────────────────────────────
async def speak(text):
    tts = edge_tts.Communicate(text, voice=VOICE)
    await tts.save(OUTPUT_AUDIO)
    os.system(f"afplay {OUTPUT_AUDIO}")   # afplay is built into macOS

# ─────────────────────────────────────────────
#  MAIN LOOP
# ─────────────────────────────────────────────
def main():
    print("=" * 45)
    print("       👋  AIDA is Online. How can I help?")
    print("       (say 'goodbye' or 'exit' to quit)")
    print("=" * 45)

    # Greet on startup
    greeting = "Hello! I'm AIDA, your personal assistant. I'm ready when you are."
    print(f"🤖  AIDA: {greeting}")
    asyncio.run(speak(greeting))

    while True:
        try:
            audio = record_audio()
            user_text = transcribe(audio)

            if not user_text:
                continue

            # Exit commands
            if any(word in user_text.lower() for word in ["goodbye", "exit", "quit", "bye"]):
                farewell = "Goodbye! It was a pleasure assisting you."
                print(f"🤖  AIDA: {farewell}")
                asyncio.run(speak(farewell))
                break

            response = ask_aida(user_text)
            asyncio.run(speak(response))

        except KeyboardInterrupt:
            print("\n\n⛔  AIDA shut down manually.")
            break
        except Exception as e:
            print(f"❌  Error: {e}")
            continue

if __name__ == "__main__":
    main()

