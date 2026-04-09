import os
import sys
import time
import asyncio
import tempfile
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import whisper
import edge_tts
from groq import Groq

from config import (
    VOICE,
    SAMPLE_RATE,
    RECORD_SECONDS,
    OUTPUT_AUDIO,
    WHISPER_MODEL,
    GROQ_MODEL,
    MAX_TOKENS,
    TEMPERATURE,
    ASSISTANT_NAME,
)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
SYSTEM_PROMPT = """
You are AIDA (Artificially Intelligent Digital Assistant), a smart, warm, and helpful female AI assistant.
You speak in a natural, conversational tone — like a knowledgeable friend, not a robot.
Keep responses concise unless the user asks you to elaborate.
You address the user by name if they tell you it.
You are running on a macOS laptop and are powered by LLaMA 3.1 via Groq.
"""
EXIT_COMMANDS = ["goodbye", "exit", "quit", "bye", "shut down", "stop"]

whisper_model = None
client = None
conversation_history: list[dict[str, str]] = []


def record_audio(duration=RECORD_SECONDS) -> np.ndarray:
    try:
        total_frames = int(duration * SAMPLE_RATE)
        audio_data = sd.rec(
            total_frames,
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
        )
        for remaining in range(int(duration), 0, -1):
            print(
                f"\r🎙  Listening for {remaining} seconds... (speak now)",
                end="",
                flush=True,
            )
            time.sleep(1)
        sd.wait()
        print()
        print("✅  Done recording.")
        return audio_data
    except Exception as exc:
        print(f"❌  Error: Unable to access the microphone. {exc}")
        print("❌  Allow microphone access in System Settings > Privacy & Security > Microphone > Terminal")
        sys.exit(1)


def transcribe(audio_data: np.ndarray) -> str:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
        temp_path = temp_audio.name

    try:
        write(temp_path, SAMPLE_RATE, audio_data)
        result = whisper_model.transcribe(temp_path)
        text = result["text"].strip()
        print(f"🗣  You said: {text}")
        return text
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def ask_aida(user_input: str) -> str:
    conversation_history.append({"role": "user", "content": user_input})

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *conversation_history,
            ],
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
        )
        reply = response.choices[0].message.content.strip()
        conversation_history.append({"role": "assistant", "content": reply})
        print(f"🤖  {ASSISTANT_NAME}: {reply}")
        return reply
    except Exception as exc:
        conversation_history.pop()
        print(f"❌  Error: API call failed — retrying... ({exc})")
        return ""


async def speak(text: str) -> None:
    try:
        communicate = edge_tts.Communicate(text, voice=VOICE)
        await communicate.save(OUTPUT_AUDIO)
        os.system(f"afplay {OUTPUT_AUDIO}")
    except Exception as exc:
        print(f"❌  Error: Voice synthesis failed — continuing without audio. ({exc})")


def main() -> None:
    global GROQ_API_KEY, whisper_model, client, conversation_history

    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    if not GROQ_API_KEY:
        print("❌  Error: GROQ_API_KEY is not set. Export it in ~/.zshrc and try again.")
        sys.exit(1)

    print("=============================================")
    print(f"👋  {ASSISTANT_NAME} is Online. How can I help?")
    print("(say 'goodbye' or 'exit' to quit)")
    print("=============================================")

    try:
        whisper_model = whisper.load_model(WHISPER_MODEL)
    except Exception as exc:
        print(f"❌  Error: Unable to load Whisper model '{WHISPER_MODEL}'. Check your internet connection for the first download. ({exc})")
        sys.exit(1)

    client = Groq(api_key=GROQ_API_KEY)
    conversation_history = []

    greeting = "Hello! I am AIDA. How can I help you today?"
    asyncio.run(speak(greeting))

    try:
        while True:
            try:
                audio_data = record_audio()
                user_text = transcribe(audio_data)

                if not user_text.strip():
                    print("❌  Error: No speech detected — listening again...")
                    continue

                if any(word in user_text.lower() for word in EXIT_COMMANDS):
                    farewell = "Goodbye! It was a pleasure assisting you."
                    asyncio.run(speak(farewell))
                    sys.exit(0)

                reply = ask_aida(user_text)
                if reply:
                    asyncio.run(speak(reply))
            except Exception as exc:
                print(f"❌  Error: {exc} — continuing...")
                continue
    except KeyboardInterrupt:
        print("\n⛔  AIDA shut down manually.")
        sys.exit(0)


if __name__ == "__main__":
    main()
