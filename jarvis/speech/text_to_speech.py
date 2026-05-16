from __future__ import annotations

import sys
import numpy as np
import sounddevice as sd

try:
    from elevenlabs.client import ElevenLabs
except ImportError:
    ElevenLabs = None

import pyttsx3
import win32com.client


class TextToSpeechService:
    def __init__(
        self,
        language: str = "es",
        rate: int = 175,
        voice_hint: str = "",
        elevenlabs_api_key: str = "",
        elevenlabs_voice_id: str = "",
    ) -> None:
        self.language = language.lower()
        self.rate = rate
        self.voice_hint = voice_hint.lower().strip()
        self.elevenlabs_api_key = elevenlabs_api_key
        self.elevenlabs_voice_id = elevenlabs_voice_id

        self.elevenlabs_client = None
        if self.elevenlabs_api_key and ElevenLabs is not None:
            self.elevenlabs_client = ElevenLabs(api_key=self.elevenlabs_api_key)

        self._is_windows = sys.platform.startswith("win")

        if self._is_windows:
            self.engine = win32com.client.Dispatch("SAPI.SpVoice")
            self._configure_windows_voice()
        else:
            self.engine = pyttsx3.init()
            self._configure_voice()

    def speak(self, text: str) -> None:
        if not text:
            return

        if self.elevenlabs_client is not None:
            try:
                # "JBFqnCBsd6RMkjVDRZzb" is George (British), good Jarvis alternative if custom not provided
                voice_id = self.elevenlabs_voice_id if self.elevenlabs_voice_id else "JBFqnCBsd6RMkjVDRZzb"
                audio_generator = self.elevenlabs_client.text_to_speech.convert(
                    text=text,
                    voice_id=voice_id,
                    model_id="eleven_multilingual_v2",
                    output_format="pcm_16000",
                )
                
                audio_bytes = b"".join(audio_generator)
                audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
                
                sd.play(audio_array, samplerate=16000)
                sd.wait()
                return
            except Exception as exc:
                print(f"Jarvis> Error en ElevenLabs: {exc}. Usando voz local de respaldo.")

        try:
            if self._is_windows:
                self.engine.Speak(text)
            else:
                self.engine.say(text)
                self.engine.runAndWait()
        except Exception:
            pass

    def _configure_voice(self) -> None:
        self.engine.setProperty("rate", self.rate)
        voices = self.engine.getProperty("voices")
        selected_voice_id = None

        if self.voice_hint:
            for voice in voices:
                voice_blob = " ".join(
                    [
                        str(getattr(voice, "id", "")),
                        str(getattr(voice, "name", "")),
                        " ".join(str(item) for item in getattr(voice, "languages", [])),
                    ]
                ).lower()
                if self.voice_hint in voice_blob:
                    selected_voice_id = voice.id
                    break

        if selected_voice_id is None and self.language.startswith("es"):
            for voice in voices:
                voice_blob = " ".join(
                    [
                        str(getattr(voice, "id", "")),
                        str(getattr(voice, "name", "")),
                        " ".join(str(item) for item in getattr(voice, "languages", [])),
                    ]
                ).lower()
                if "es-" in voice_blob or "spanish" in voice_blob:
                    selected_voice_id = voice.id
                    break

        if selected_voice_id is not None:
            self.engine.setProperty("voice", selected_voice_id)

    def _configure_windows_voice(self) -> None:
        try:
            voices = self.engine.GetVoices()
            selected_voice = None

            for index in range(voices.Count):
                voice = voices.Item(index)
                description = voice.GetDescription().lower()
                voice_id = str(getattr(voice, "Id", "")).lower()
                blob = f"{description} {voice_id}"

                if self.voice_hint and self.voice_hint in blob:
                    selected_voice = voice
                    break

            if selected_voice is None and self.language.startswith("es"):
                for index in range(voices.Count):
                    voice = voices.Item(index)
                    description = voice.GetDescription().lower()
                    voice_id = str(getattr(voice, "Id", "")).lower()
                    blob = f"{description} {voice_id}"
                    if "spanish" in blob or "es-es" in blob or "helena" in blob:
                        selected_voice = voice
                        break

            if selected_voice is not None:
                self.engine.Voice = selected_voice

            self.engine.Rate = self._to_sapi_rate(self.rate)
        except Exception:
            pass

    def _to_sapi_rate(self, value: int) -> int:
        if value <= 140:
            return -2
        if value <= 160:
            return -1
        if value <= 185:
            return 0
        if value <= 210:
            return 1
        return 2
