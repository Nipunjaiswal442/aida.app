# config.py — AIDA Configuration
# Edit these values to customize your assistant

VOICE = "en-US-JennyNeural"        # Female voice for AIDA
SAMPLE_RATE = 16000                # Audio sample rate (Hz)
RECORD_SECONDS = 5                 # How long to listen per turn
OUTPUT_AUDIO = "aida_response.mp3" # Temp file for TTS output
WHISPER_MODEL = "base"             # Whisper model size
GROQ_MODEL = "llama-3.1-8b-instant" # Groq model ID
MAX_TOKENS = 300                   # Max tokens in LLM response
TEMPERATURE = 0.7                  # LLM creativity (0=factual, 1=creative)
ASSISTANT_NAME = "AIDA"            # Name shown in terminal output

# Available female voices:
# en-US-JennyNeural   — warm, professional (default)
# en-US-AriaNeural    — clear, friendly
# en-GB-SoniaNeural   — British accent
# en-IN-NeerjaNeural  — Indian English

# Available Groq models (all free tier):
# llama-3.1-8b-instant    — fastest (default)
# llama-3.1-70b-versatile — smarter, slightly slower
# mixtral-8x7b-32768      — longer context window
