# AIDA

AIDA is a local macOS voice and text assistant powered by Ollama.

## Example Commands

## Terminal Powerhouse

AIDA translates plain English into terminal commands - always showing
the command first and asking permission before executing.

| You say | AIDA generates and runs |
|---|---|
| "What's eating my CPU?" | `top -l 1 -n 10 -o cpu` |
| "How much disk space do I have?" | `df -h /` |
| "Find all files larger than 500MB" | `find ~ -size +500M -type f` |
| "Kill whatever is running on port 3000" | `kill $(lsof -t -i:3000)` |
| "Show me my git log for the last 10 commits" | `git log --oneline -10` |
| "Install httpie with brew" | `brew install httpie` |
| "Check if Node is installed" | `node --version` |
| "Compress my Desktop folder" | `zip -r Desktop_backup.zip ~/Desktop` |
| "Show all environment variables" | `env | sort` |
| "What's my public IP?" | `curl -s ifconfig.me` |
| "Show open network ports" | `sudo lsof -iTCP -sTCP:LISTEN -n -P` |
| "Clean up node_modules in current folder" | `find . -name 'node_modules' -type d -prune -exec rm -rf '{}' +` |
| "Show the last 100 lines of system log" | `log show --last 1h --style compact \| tail -100` |

Safety rules hardcoded into AIDA:
- Always shows command before running
- Always asks yes/no confirmation
- Automatically copies command to clipboard
- Logs every command to `terminal_history.json`
- Permanently blocks: `rm -rf /`, disk wipe, fork bombs, `chmod 777 /`

## Current Data

AIDA answers live questions by fetching fresh context first:
- Safe read-only terminal snapshots for local Mac facts like date, uptime, OS, disk, battery, CPU, memory, IP, and WiFi
- DuckDuckGo results for external facts like latest news, current prices, scores, people, companies, weather, and web lookups

Examples:
- "What's the latest AI news?"
- "What's Apple's stock price today?"
- "Current disk space on my Mac"
- "Who is the CEO of OpenAI right now?"
