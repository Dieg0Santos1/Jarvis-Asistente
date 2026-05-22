from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import sounddevice as sd
import whisper
from scipy.io.wavfile import write


class SpeechToTextService:
    def __init__(self, model_name: str | None = None, language: str | None = None, prompt: str | None = None) -> None:
        from config import settings
        self.model_name = model_name or settings.whisper_model
        self.language = language or settings.language
        self.prompt = (prompt or settings.whisper_prompt).strip()
        self._model = None

    def record_to_file(self, output_path: str, duration_seconds: int = 5, sample_rate: int = 16_000) -> str:
        """Record microphone audio into a WAV file."""
        audio = sd.rec(
            int(duration_seconds * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
        )
        sd.wait()
        write(output_path, sample_rate, audio)
        return output_path

    def record_until_silence(
        self,
        output_path: str,
        max_duration_seconds: float = 8.0,
        silence_duration_seconds: float = 1.2,
        min_speech_seconds: float = 0.5,
        energy_threshold: float = 0.015,
        sample_rate: int = 16_000,
        frame_duration_ms: int = 100,
    ) -> str:
        """Record until speech is followed by enough silence."""
        frame_samples = int(sample_rate * frame_duration_ms / 1000)
        max_frames = max(1, int(max_duration_seconds * 1000 / frame_duration_ms))
        silence_frames_needed = max(1, int(silence_duration_seconds * 1000 / frame_duration_ms))
        min_speech_frames = max(1, int(min_speech_seconds * 1000 / frame_duration_ms))

        collected_frames: list[np.ndarray] = []
        speech_detected = False
        speech_frames = 0
        trailing_silence_frames = 0

        with sd.InputStream(
            samplerate=sample_rate,
            blocksize=frame_samples,
            channels=1,
            dtype="float32",
        ) as stream:
            for _ in range(max_frames):
                frame, _ = stream.read(frame_samples)
                frame_mono = np.squeeze(frame, axis=1)
                collected_frames.append(frame_mono.copy())

                energy = float(np.sqrt(np.mean(np.square(frame_mono)))) if len(frame_mono) else 0.0
                is_speech = energy >= energy_threshold

                if is_speech:
                    speech_detected = True
                    speech_frames += 1
                    trailing_silence_frames = 0
                elif speech_detected:
                    trailing_silence_frames += 1

                if speech_detected and speech_frames >= min_speech_frames and trailing_silence_frames >= silence_frames_needed:
                    break

        if not collected_frames:
            raise RuntimeError("No se pudo capturar audio del microfono.")

        audio = np.concatenate(collected_frames)
        audio_int16 = np.clip(audio * 32767, -32768, 32767).astype(np.int16)
        write(output_path, sample_rate, audio_int16)
        return output_path

    def transcribe_file(self, audio_path: str) -> str:
        """Transcribe a recorded audio file with Whisper."""
        if shutil.which("ffmpeg") is None:
            raise RuntimeError(
                "Whisper necesita ffmpeg instalado y disponible en el PATH de Windows."
            )

        model = self._load_model()
        result = model.transcribe(
            str(Path(audio_path)),
            language=self.language,
            task="transcribe",
            initial_prompt=self.prompt or None,
            temperature=0.0,
            beam_size=5,
            best_of=5,
            fp16=False,
            condition_on_previous_text=False,
        )
        return self._normalize_transcript(str(result.get("text", "")).strip())

    def _load_model(self):
        if self._model is None:
            self._model = whisper.load_model(self.model_name)
        return self._model

    def _normalize_transcript(self, text: str) -> str:
        cleaned = " ".join(text.split())
        if self._looks_like_silence_hallucination(cleaned):
            return ""

        replacements = {
            "visual estudio code": "visual studio code",
            "visual estudio": "visual studio",
            "espotify": "spotify",
            "spotyfi": "spotify",
            "gijad": "github",
            "git jab": "github",
            "cromo": "chrome",
            "crohm": "chrome",
            "vat bani": "bad bunny",
            "bad boni": "bad bunny",
            "bad bani": "bad bunny",
            "bat bani": "bad bunny",
        }
        lowered = cleaned.lower()
        for source, target in replacements.items():
            lowered = lowered.replace(source, target)
        return lowered

    def _looks_like_silence_hallucination(self, text: str) -> bool:
        lowered = text.lower().strip(" .,!¡¿?")
        hallucinations = {
            "suscribete",
            "suscríbete",
            "subtitulos realizados por la comunidad de amara.org",
            "gracias por ver el video",
            "gracias por ver",
            "thank you for watching",
            "subscribe",
        }
        return lowered in hallucinations or (lowered.startswith("suscr") and len(lowered) <= 24)
