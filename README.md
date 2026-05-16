# Jarvis

Jarvis is a local AI voice assistant for Windows powered by Python, Whisper, Gemini, and a floating overlay UI.

## Initial scope

- Wake word detection
- Speech to text
- Gemini-based intent analysis
- Text to speech
- Floating overlay UI
- Basic desktop actions

## Quick start

1. Create a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Optionally install `pip install -r requirements-ui.txt` for the PyWebview overlay on compatible Python versions.
4. Copy `.env.example` to `.env` and set your `GEMINI_API_KEY`.
5. Run `python main.py`.

On Python 3.14, the project falls back to a lightweight `tkinter` overlay because `pywebview` dependencies may fail to build on Windows.

The current project state is a scaffolded MVP foundation ready for feature implementation.
