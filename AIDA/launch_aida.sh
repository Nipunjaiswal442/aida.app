#!/bin/bash
# Start Ollama silently as background daemon (no app window or menu bar icon)
/usr/local/bin/ollama serve &>/dev/null &
sleep 5

# Launch AIDA
cd /Users/apple/aida-assistant/AIDA
source venv/bin/activate
python3 main.py
