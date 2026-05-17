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

    def speak_streaming(self, sentence_generator) -> None:
        """
        Pipeline de streaming de alta calidad:
        - Productor: sintetiza audio para cada oración en un hilo separado
        - Consumidor (hilo principal): reproduce el audio en cuanto está listo
        Resultado: Jarvis empieza a hablar ~300ms después de generar la primera oración.
        """
        import queue as q_module
        import threading

        DONE = object()  # Centinela para señalar fin de cola
        audio_queue: q_module.Queue = q_module.Queue(maxsize=3)  # Prefetch máx. 3 oraciones
        voice_id = self.elevenlabs_voice_id if self.elevenlabs_voice_id else "JBFqnCBsd6RMkjVDRZzb"

        def producer(sentences: list[str]):
            """Sintetiza cada oración y las encola como bytes de audio."""
            for sentence in sentences:
                if not sentence.strip():
                    continue
                try:
                    audio_gen = self.elevenlabs_client.text_to_speech.convert(
                        text=sentence,
                        voice_id=voice_id,
                        model_id="eleven_turbo_v2_5",
                        output_format="pcm_16000",
                    )
                    audio_bytes = b"".join(audio_gen)
                    audio_queue.put(audio_bytes)
                except Exception as exc:
                    print(f"Jarvis> [TTS error]: {exc}")
                    # Fallback: sintetizar con SAPI local
                    audio_queue.put(("sapi", sentence))
            audio_queue.put(DONE)

        if self.elevenlabs_client is not None:
            # Recoger todas las oraciones del generador primero
            # (el generador de OpenAI es muy rápido, llega antes que ElevenLabs)
            collected: list[str] = []
            for sentence in sentence_generator:
                s = sentence.strip()
                if s:
                    collected.append(s)
                    print(f"Jarvis> {s}")

            if not collected:
                return

            # Arrancar productor en hilo paralelo
            t = threading.Thread(target=producer, args=(collected,), daemon=True)
            t.start()

            # Consumidor: reproducir en cuanto llega cada chunk de audio
            while True:
                item = audio_queue.get(timeout=30)
                if item is DONE:
                    break
                if isinstance(item, tuple) and item[0] == "sapi":
                    self.speak(item[1])
                elif isinstance(item, bytes) and item:
                    arr = np.frombuffer(item, dtype=np.int16)
                    sd.play(arr, samplerate=16000)
                    sd.wait()
            return

        # Fallback completo: sin ElevenLabs, SAPI por oración
        for sentence in sentence_generator:
            sentence = sentence.strip()
            if sentence:
                print(f"Jarvis> {sentence}")
                self.speak(sentence)


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
