# JARVIS - AI Voice Assistant for Windows

## Project Overview

Jarvis is a personal AI voice assistant for Windows inspired by Iron Man's Jarvis.

The assistant must:

- Listen continuously for the wake word "Jarvis"
- Convert speech to text
- Understand natural language with AI
- Execute Windows/system actions
- Respond with voice
- Display a floating visual interface overlay

The goal is to create a futuristic desktop assistant with voice interaction, automation, and UI feedback.

---

# Core Features

## 1. Wake Word Detection

Continuously listen for:

"Jarvis"

After detection:
- activate listening mode
- record user voice command

Recommended:
- openWakeWord

Alternative:
- Picovoice Porcupine


Requirements:
- low CPU usage
- local/offline


---

## 2. Speech to Text

Convert recorded audio to text.

Recommended:
- OpenAI Whisper

Requirements:
- local processing
- Spanish support
- accurate transcription


Example:

Audio:
"Jarvis, open Chrome"

Text:
"open chrome"


---

## 3. AI Brain

Use Gemini Pro API.

Responsibilities:
- understand commands
- general conversation
- classify intent


Possible intents:

### Chat

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


Gemini should be used for:
- command understanding
- conversational responses
- contextual memory


---

## 4. Action Execution

Execute Windows/system actions.

### App Actions
- open vscode
- open chrome
- open spotify
- open terminal
- open explorer


### Browser Actions
- open websites
- search Google
- open GitHub


### System Actions
- shutdown pc
- restart pc
- lock pc
- volume control
- brightness


Implementation:
- subprocess
- os
- webbrowser
- pyautogui


Example:

```python
subprocess.Popen("code")
```


---

## 5. Text to Speech

Assistant must speak responses.

Initial:
- pyttsx3

Future upgrade:
- ElevenLabs API


Example:

User:
"Jarvis, open Chrome"

Assistant:
"Opening Chrome"


---

# Floating Visual Interface (Overlay UI)

Jarvis must have a floating desktop visual overlay.

This is a small always-on-top transparent assistant UI.

Purpose:
- show assistant state
- improve user experience
- feel like real Jarvis


---

## Overlay Requirements

Window must be:

- frameless
- transparent background
- always on top
- draggable
- lightweight


Recommended:
- PyWebview


Alternative:
- Electron


For this project use:
- PyWebview


---

## UI States

Jarvis UI must react visually based on assistant state.

States:

### 1. Idle

Default state.

Appearance:
- small floating circle/orb

Animation:
- soft breathing glow
- slow pulse


Example:
```text
○
```


State name:
```python
idle
```


---

### 2. Listening

Activated after wake word detection.

Appearance:
- larger glowing orb

Animation:
- pulsing circle
- active glow


Example:
```text
◉
```


State:
```python
listening
```


Triggered when:
- wake word detected
- recording command


---

### 3. Thinking

Activated while Gemini processes request.

Appearance:
- rotating orb or circular animation

Animation:
- spin
- orbiting particles


Example:
```text
◌
```


State:
```python
thinking
```


Triggered when:
- AI processing


---

### 4. Speaking

Activated while assistant responds.

Appearance:
- animated audio bars


Example:
```text
▁▃▆▂▇▅▂
```


Animation:
- waveform bars


State:
```python
speaking
```


Triggered when:
- text-to-speech active


---

## UI Optional Elements

Future additions:

### Transcript text
Display recognized speech:

Listening...
"open visual studio code"


### Response text
Jarvis:
"Opening Visual Studio Code"


### Clock
Display current time


### Weather
Display current weather


### Upcoming tasks
Display:
- meetings
- tasks
- reminders


---

## UI Position

Default:
- bottom right

Alternative:
- bottom center


Must be configurable.


---

## State Management

Python backend controls UI state.

Examples:

```python
ui.set_state("idle")
ui.set_state("listening")
ui.set_state("thinking")
ui.set_state("speaking")
```


Flow:

Wake word detected:
```python
ui.set_state("listening")
```

AI processing:
```python
ui.set_state("thinking")
```

Speaking:
```python
ui.set_state("speaking")
```

Done:
```python
ui.set_state("idle")
```


---

# Future Features

Not required for MVP.

## Wake on LAN
Power on PC remotely.

Library:
- wakeonlan


## Smart Home
Control:
- lights
- plugs
- LED strips


## Calendar Integration
Google Calendar API


Commands:
- what do I have today


## Notion Integration
Read tasks and notes.


## Study Mode

Command:
"Jarvis, activate study mode"

Actions:
- open VS Code
- open Chrome
- open Spotify
- open terminal


---

# MVP Scope (Phase 1)

Build only:

1. Wake word detection
2. Speech to text
3. Gemini integration
4. Text to speech
5. Floating overlay UI
6. Open Chrome
7. Open VS Code
8. Open Spotify
9. Basic conversation


Commands:

- Jarvis, open Chrome
- Jarvis, open Visual Studio Code
- Jarvis, open Spotify
- Jarvis, tell me something interesting


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
- pyautogui
- webbrowser
- os


## UI
- PyWebview
- HTML
- CSS
- JavaScript


Future:
- wakeonlan
- Google Calendar API
- Notion API
- ElevenLabs


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
├── ui/
│   ├── overlay.py
│   ├── index.html
│   ├── style.css
│   └── script.js
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
UI state = listening
↓
Record user audio
↓
Speech to text
↓
UI state = thinking
↓
Gemini analyzes intent
↓
If chat:
    generate response
If action:
    execute command
↓
UI state = speaking
↓
Speak response
↓
UI state = idle
```


---

# Development Rules

- modular architecture
- clean code
- reusable functions
- easy to add commands
- easy to add integrations
- handle exceptions gracefully


---

# Build Order

1. Wake word
2. Speech to text
3. Text to speech
4. Overlay UI
5. Gemini
6. Chrome command
7. VS Code command
8. Spotify command


---

# Final Goal

A futuristic personal AI desktop assistant with:

- wake word
- conversation
- automation
- floating interface
- voice responses
- productivity tools


Final experience should feel like:

"Jarvis running natively on Windows powered by Gemini"