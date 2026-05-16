from __future__ import annotations

from dataclasses import dataclass
import time

import numpy as np
import sounddevice as sd
from openwakeword.model import Model
from openwakeword.utils import download_models


@dataclass(slots=True)
class WakeWordDetection:
    detected: bool
    score: float


class WakeWordListener:
    def __init__(
        self,
        wake_word: str,
        model_name: str = "hey_jarvis",
        threshold: float = 0.35,
        debug: bool = False,
    ) -> None:
        self.wake_word = wake_word
        self.model_name = model_name
        self.threshold = threshold
        self.debug = debug
        self.sample_rate = 16_000
        self.frame_size = 1_280
        download_models([model_name])
        self.model = Model(wakeword_models=[model_name], inference_framework="onnx")

    def wait_for_wake_word(self) -> WakeWordDetection:
        """Block until the configured wake word is detected."""
        threshold = {self.model_name: self.threshold}
        max_score = 0.0
        last_debug_print = time.monotonic()

        with sd.RawInputStream(
            samplerate=self.sample_rate,
            blocksize=self.frame_size,
            dtype="int16",
            channels=1,
        ) as stream:
            while True:
                audio_chunk, _ = stream.read(self.frame_size)
                audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
                predictions = self.model.predict(
                    audio_array,
                    threshold=threshold,
                    debounce_time=1.0,
                )
                score = float(predictions.get(self.model_name, 0.0))
                max_score = max(max_score, score)

                if self.debug and time.monotonic() - last_debug_print >= 1.0:
                    print(f"Jarvis> Wake score actual: {score:.2f} | max reciente: {max_score:.2f}")
                    last_debug_print = time.monotonic()
                    max_score = 0.0

                if score >= self.threshold:
                    return WakeWordDetection(detected=True, score=score)
