from __future__ import annotations

import ctypes
import os
import subprocess
from datetime import datetime


class SystemActions:

    # ------------------------------------------------------------------
    # Hora
    # ------------------------------------------------------------------

    def get_current_time(self) -> str:
        now = datetime.now()
        hour = now.strftime("%H:%M")
        return f"Son las {hour}."

    # ------------------------------------------------------------------
    # Apagado / reinicio / bloqueo
    # ------------------------------------------------------------------

    def shutdown_pc(self) -> str:
        subprocess.Popen(["shutdown", "/s", "/t", "30"])
        return "Apagando el equipo en 30 segundos. Para cancelar diga: cancela el apagado."

    def restart_pc(self) -> str:
        subprocess.Popen(["shutdown", "/r", "/t", "30"])
        return "Reiniciando el equipo en 30 segundos."

    def lock_pc(self) -> str:
        ctypes.windll.user32.LockWorkStation()
        return "Equipo bloqueado."

    def cancel_shutdown(self) -> str:
        subprocess.Popen(["shutdown", "/a"])
        return "Apagado cancelado."

    # ------------------------------------------------------------------
    # Volumen del sistema (usa pycaw)
    # ------------------------------------------------------------------

    def _get_volume_interface(self):
        from pycaw.pycaw import AudioUtilities
        device = AudioUtilities.GetSpeakers()
        return device.EndpointVolume

    def set_volume(self, level: int) -> str:
        """Ajusta el volumen a un porcentaje (0-100)."""
        try:
            level = max(0, min(100, level))
            vol = self._get_volume_interface()
            vol.SetMasterVolumeLevelScalar(level / 100.0, None)
            return f"Volumen ajustado al {level} por ciento."
        except Exception as e:
            return f"No pude ajustar el volumen: {e}"

    def volume_up(self, step: int = 10) -> str:
        try:
            vol = self._get_volume_interface()
            current = int(vol.GetMasterVolumeLevelScalar() * 100)
            new = min(100, current + step)
            vol.SetMasterVolumeLevelScalar(new / 100.0, None)
            return f"Volumen subido al {new} por ciento."
        except Exception as e:
            return f"No pude subir el volumen: {e}"

    def volume_down(self, step: int = 10) -> str:
        try:
            vol = self._get_volume_interface()
            current = int(vol.GetMasterVolumeLevelScalar() * 100)
            new = max(0, current - step)
            vol.SetMasterVolumeLevelScalar(new / 100.0, None)
            return f"Volumen bajado al {new} por ciento."
        except Exception as e:
            return f"No pude bajar el volumen: {e}"

    def mute(self) -> str:
        try:
            vol = self._get_volume_interface()
            vol.SetMute(1, None)
            return "Sistema silenciado."
        except Exception as e:
            return f"No pude silenciar: {e}"

    def unmute(self) -> str:
        try:
            vol = self._get_volume_interface()
            vol.SetMute(0, None)
            return "Sonido restaurado."
        except Exception as e:
            return f"No pude restaurar el sonido: {e}"

    def get_volume(self) -> str:
        try:
            vol = self._get_volume_interface()
            level = int(vol.GetMasterVolumeLevelScalar() * 100)
            muted = vol.GetMute()
            if muted:
                return "El sistema está silenciado."
            return f"El volumen actual es {level} por ciento."
        except Exception as e:
            return f"No pude leer el volumen: {e}"

    # ------------------------------------------------------------------
    # Batería y uso de sistema (psutil)
    # ------------------------------------------------------------------

    def get_battery(self) -> str:
        try:
            import psutil
            battery = psutil.sensors_battery()
            if battery is None:
                return "Este equipo no tiene batería o no está detectada."
            pct = int(battery.percent)
            charging = "cargando" if battery.power_plugged else "en descarga"
            return f"Batería al {pct} por ciento, {charging}."
        except Exception as e:
            return f"No pude leer la batería: {e}"

    def get_system_stats(self) -> str:
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.5)
            ram = psutil.virtual_memory()
            ram_used = round(ram.used / (1024 ** 3), 1)
            ram_total = round(ram.total / (1024 ** 3), 1)
            return (
                f"CPU al {cpu} por ciento. "
                f"RAM: {ram_used} de {ram_total} gigabytes en uso."
            )
        except Exception as e:
            return f"No pude leer el estado del sistema: {e}"

    # ------------------------------------------------------------------
    # Brillo de pantalla
    # ------------------------------------------------------------------

    def set_brightness(self, level: int) -> str:
        try:
            import screen_brightness_control as sbc
            level = max(0, min(100, level))
            sbc.set_brightness(level)
            return f"Brillo ajustado al {level} por ciento."
        except Exception as e:
            return f"No pude ajustar el brillo: {e}"

    def brightness_up(self, step: int = 10) -> str:
        try:
            import screen_brightness_control as sbc
            current = sbc.get_brightness()[0]
            new = min(100, current + step)
            sbc.set_brightness(new)
            return f"Brillo subido al {new} por ciento."
        except Exception as e:
            return f"No pude subir el brillo: {e}"

    def brightness_down(self, step: int = 10) -> str:
        try:
            import screen_brightness_control as sbc
            current = sbc.get_brightness()[0]
            new = max(0, current - step)
            sbc.set_brightness(new)
            return f"Brillo bajado al {new} por ciento."
        except Exception as e:
            return f"No pude bajar el brillo: {e}"

    # ------------------------------------------------------------------
    # Dispatch universal
    # ------------------------------------------------------------------

    def execute(self, action_name: str, action_input: str = "") -> str:
        """Dispatcher central para todas las acciones de sistema."""
        # Acciones que necesitan un valor numérico
        if action_name == "set_volume":
            try:
                return self.set_volume(int(action_input))
            except ValueError:
                return "Necesito un nivel de volumen del 0 al 100."

        if action_name == "set_brightness":
            try:
                return self.set_brightness(int(action_input))
            except ValueError:
                return "Necesito un nivel de brillo del 0 al 100."

        actions = {
            "get_time": self.get_current_time,
            "shutdown_pc": self.shutdown_pc,
            "restart_pc": self.restart_pc,
            "lock_pc": self.lock_pc,
            "cancel_shutdown": self.cancel_shutdown,
            "volume_up": self.volume_up,
            "volume_down": self.volume_down,
            "mute": self.mute,
            "unmute": self.unmute,
            "get_volume": self.get_volume,
            "get_battery": self.get_battery,
            "get_system_stats": self.get_system_stats,
            "brightness_up": self.brightness_up,
            "brightness_down": self.brightness_down,
        }
        handler = actions.get(action_name)
        if handler:
            return handler()
        return "No reconozco esa acción de sistema."
