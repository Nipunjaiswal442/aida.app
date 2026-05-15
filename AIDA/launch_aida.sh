#!/bin/bash
# Start Ollama if not already running
open -a Ollama
sleep 4

# Launch AIDA
cd /Users/apple/aida-assistant/AIDA
/Users/apple/aida-assistant/AIDA/venv/bin/python3.12 main.py
