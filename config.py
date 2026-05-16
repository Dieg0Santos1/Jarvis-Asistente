from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(slots=True)
class Settings:
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    language: str = os.getenv("JARVIS_LANGUAGE", "es")
    whisper_model: str = os.getenv("WHISPER_MODEL", "small")
    whisper_prompt: str = os.getenv(
        "WHISPER_PROMPT",
        (
            "Asistente de voz en espanol. Comandos comunes: abre Chrome, abre Google Chrome, "
            "abre Visual Studio Code, abre VS Code, abre Spotify, abre GitHub, abre la terminal, "
            "abre el explorador de archivos, busca Bad Bunny en Google, que hora es."
        ),
    )
    voice_max_seconds: float = float(os.getenv("VOICE_MAX_SECONDS", "8"))
    voice_silence_seconds: float = float(os.getenv("VOICE_SILENCE_SECONDS", "1.2"))
    voice_min_speech_seconds: float = float(os.getenv("VOICE_MIN_SPEECH_SECONDS", "0.5"))
    voice_energy_threshold: float = float(os.getenv("VOICE_ENERGY_THRESHOLD", "0.015"))
    wake_word: str = os.getenv("WAKE_WORD", "jarvis")
    wake_word_model: str = os.getenv("WAKE_WORD_MODEL", "hey_jarvis")
    wake_word_threshold: float = float(os.getenv("WAKE_WORD_THRESHOLD", "0.18"))
    wake_word_debug: bool = os.getenv("WAKE_WORD_DEBUG", "false").lower() in {"1", "true", "yes", "on"}
    tts_rate: int = int(os.getenv("TTS_RATE", "175"))
    tts_voice_hint: str = os.getenv("TTS_VOICE_HINT", "")


settings = Settings()
