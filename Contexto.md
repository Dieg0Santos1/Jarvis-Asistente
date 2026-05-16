# JARVIS - AI Voice Assistant for Windows

## Project Overview

This project is a personal AI voice assistant inspired by Jarvis from Iron Man.

The goal is to create a local voice assistant for Windows that can:

- Listen continuously for a wake word ("Jarvis")
- Convert speech to text
- Understand commands and conversation using AI
- Execute real Windows/system actions
- Respond back with voice

The assistant should feel like a real personal operating system companion.

Example interactions:

User:
"Jarvis, open Visual Studio Code"

Assistant:
"Opening Visual Studio Code"

Action:
- Opens VS Code


User:
"Jarvis, tell me something interesting"

Assistant:
"Did you know the first computer virus appeared in 1971?"


User:
"Jarvis, activate study mode"

Actions:
- Open VS Code
- Open Chrome
- Open Spotify
- Open terminal


---

# Main Features

## 1. Wake Word Detection

The assistant must continuously listen for the wake word:

"Jarvis"

After detecting the wake word, begin recording the next speech input.

Recommended library:
- openWakeWord

Alternative:
- Picovoice Porcupine

Requirements:
- Low CPU usage
- Local/offline detection


---

## 2. Speech to Text

Convert recorded audio into text.

Recommended:
- OpenAI Whisper

Requirements:
- Spanish support
- High accuracy
- Local execution


Flow:

Audio:
"Jarvis, open Chrome"

Text:
"open chrome"


---

## 3. AI Brain

Use Gemini Pro API as the assistant brain.

Responsibilities:
- Understand natural language
- Detect intent
- Classify requests

Possible intents:

### Conversation
Examples:
- tell me something interesting
- explain recursion
- what do I have today

Output:
```json
{
  "intent": "chat"
}
```

### Action
Examples:
- open vscode
- open chrome
- shutdown pc

Output:

```json
{
  "intent": "action",
  "action": "open_vscode"
}
```


Use Gemini for:
- contextual conversation
- command parsing
- general knowledge responses


---

## 4. Action Execution

If intent == action, execute Windows/system commands.

Supported actions:

### App actions
- open vscode
- open chrome
- open spotify
- open terminal
- open file explorer

### Browser actions
- open websites
- search Google
- open GitHub

### System actions
- shutdown pc
- restart pc
- lock pc
- volume up/down
- brightness

Implementation:
- subprocess
- os
- webbrowser
- pyautogui


Examples:

```python
subprocess.Popen("code")
subprocess.Popen("chrome")
```


---

## 5. Text to Speech

Assistant must respond using voice.

Recommended initial library:
- pyttsx3

Future upgrade:
- ElevenLabs API

Requirements:
- Speak all responses
- Low latency


Example:

User:
"Jarvis, open Chrome"

Assistant voice:
"Opening Chrome"


---

## 6. Future Features

Not required for MVP.

### Wake on LAN
Ability to power on PC remotely.

Libraries:
- wakeonlan

Requirements:
- BIOS Wake on LAN enabled


### Smart Home
Control:
- lights
- smart plugs
- LED strips


### Calendar Integration
Connect:
- Google Calendar API

Commands:
- what do I have today
- next meeting


### Notion Integration
Read tasks and notes.


### Study Mode
Command:
"Jarvis, activate study mode"

Actions:
- open VS Code
- open Chrome docs
- open Spotify
- show tasks


---

# MVP Scope (Phase 1)

Build only these features first:

Must work:

1. Detect wake word "Jarvis"
2. Speech to text
3. AI response
4. Text to speech
5. Open Chrome
6. Open VS Code
7. Open Spotify
8. General conversation


Example MVP commands:

- Jarvis, open Chrome
- Jarvis, open Visual Studio Code
- Jarvis, open Spotify
- Jarvis, tell me something interesting
- Jarvis, what time is it


Do NOT implement advanced features yet.


---

# Tech Stack

## Language
Python 3.11+

## IDE
Visual Studio Code

## AI
Gemini Pro API

## Voice
- openWakeWord
- Whisper
- pyttsx3

## Automation
- subprocess
- os
- pyautogui
- webbrowser

## Future
- wakeonlan
- Google Calendar API
- Notion API


---

# Project Structure

```bash
jarvis/
│
├── main.py
│
├── wakeword/
│   └── listener.py
│
├── speech/
│   ├── speech_to_text.py
│   └── text_to_speech.py
│
├── brain/
│   └── gemini_brain.py
│
├── actions/
│   ├── app_actions.py
│   ├── browser_actions.py
│   └── system_actions.py
│
├── integrations/
│   ├── calendar.py
│   └── notion.py
│
├── utils/
│   └── helpers.py
│
├── config.py
└── requirements.txt
```


---

# Main Flow

```text
Listen continuously
↓
Detect wake word "Jarvis"
↓
Record user speech
↓
Speech to text (Whisper)
↓
Gemini analyzes intent
↓
If chat:
    generate response
If action:
    execute command
↓
Speak response
```


---

# Development Rules

- Write clean modular code
- Keep files small and focused
- Use classes when useful
- Add comments
- Handle errors gracefully
- Make code easy to extend


Examples:
- easy to add new commands
- easy to add integrations


---

# Priority

Build in this order:

1. Wake word
2. Speech to text
3. Text to speech
4. Gemini brain
5. Open Chrome command
6. Open VS Code command
7. Open Spotify command


After MVP works, continue expanding.


---

# Goal

Final goal is a fully functional personal AI assistant for Windows with:

- voice activation
- AI conversation
- system automation
- productivity features
- smart home integration


Assistant should feel like:

"Jarvis for Windows powered by Gemini"