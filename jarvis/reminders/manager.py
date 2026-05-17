from __future__ import annotations

import threading
import uuid
from datetime import datetime, timedelta
from typing import Callable


class ReminderManager:
    """
    Gestiona recordatorios y alarmas.
    Corre un hilo en segundo plano que verifica cada 20 segundos.
    Cuando un recordatorio se dispara, llama al callback de voz de Jarvis.
    """

    def __init__(self, speak_callback: Callable[[str], None]) -> None:
        self._speak = speak_callback
        self._reminders: list[dict] = []
        self._lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Arranca el hilo de verificación en background."""
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def add(self, minutes: int, message: str) -> str:
        """Agrega un recordatorio relativo (dentro de N minutos)."""
        trigger_at = datetime.now() + timedelta(minutes=minutes)
        return self._register(trigger_at, message)

    def add_alarm(self, hour: int, minute: int, message: str) -> str:
        """Agrega una alarma a una hora específica del día."""
        now = datetime.now()
        trigger_at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        # Si la hora ya pasó, programarla para mañana
        if trigger_at <= now:
            trigger_at += timedelta(days=1)
        return self._register(trigger_at, message)

    def list_pending(self) -> list[dict]:
        with self._lock:
            return [r for r in self._reminders if not r["fired"]]

    def cancel_all(self) -> str:
        with self._lock:
            count = sum(1 for r in self._reminders if not r["fired"])
            self._reminders.clear()
        return f"{count} recordatorio(s) cancelado(s)." if count else "No había recordatorios pendientes."

    def _register(self, trigger_at: datetime, message: str) -> str:
        reminder = {
            "id": str(uuid.uuid4())[:8],
            "trigger_at": trigger_at,
            "message": message,
            "fired": False,
        }
        with self._lock:
            self._reminders.append(reminder)
        time_str = trigger_at.strftime("%H:%M")
        return f"Recordatorio registrado para las {time_str}: \"{message}\"."

    def _loop(self) -> None:
        """Bucle en background: verifica recordatorios cada 20 segundos."""
        import time
        while self._running:
            self._check()
            time.sleep(20)

    def _check(self) -> None:
        now = datetime.now()
        to_fire = []
        with self._lock:
            for r in self._reminders:
                if not r["fired"] and r["trigger_at"] <= now:
                    r["fired"] = True
                    to_fire.append(r)

        for r in to_fire:
            msg = f"Señor, este es su recordatorio: {r['message']}."
            print(f"\nJarvis> [RECORDATORIO] {msg}")
            try:
                self._speak(msg)
            except Exception as e:
                print(f"Jarvis> [Error recordatorio TTS]: {e}")
