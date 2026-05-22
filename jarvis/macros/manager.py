from __future__ import annotations

import re
from typing import Any

from jarvis.memory.storage import MemoryManager


class MacroManager:
    """Persists and retrieves user-defined action sequences."""

    MEMORY_KEY = "custom_macros"

    def __init__(self, memory: MemoryManager) -> None:
        self.memory = memory

    def save(self, name: str, steps: list[dict[str, Any]]) -> str:
        macro_name = self._normalize_name(name)
        if not macro_name:
            return "Necesito un nombre para guardar la rutina."
        if not steps:
            return "No puedo guardar una rutina sin acciones."

        macros = self._get_macros()
        macros[macro_name] = {"name": macro_name, "steps": self._clean_steps(steps)}
        self.memory.set(self.MEMORY_KEY, macros)
        return f"Rutina '{macro_name}' guardada."

    def add_steps(self, name: str, steps: list[dict[str, Any]]) -> str:
        macro_name = self._normalize_name(name)
        cleaned_steps = self._clean_steps(steps)
        if not cleaned_steps:
            return "No pude identificar que accion desea agregar a la rutina."

        macros = self._get_macros()
        macro = macros.get(macro_name)
        if not isinstance(macro, dict):
            return f"No encontre una rutina llamada '{macro_name}'."

        current_steps = macro.get("steps")
        if not isinstance(current_steps, list):
            current_steps = []

        added_steps: list[dict[str, str]] = []
        skipped_steps: list[dict[str, str]] = []
        for step in cleaned_steps:
            if self._step_exists(current_steps, step):
                skipped_steps.append(step)
                continue
            current_steps.append(step)
            added_steps.append(step)

        if not added_steps:
            return f"Esa accion ya forma parte de la rutina '{macro_name}'."

        macro["steps"] = current_steps
        macros[macro_name] = macro
        self.memory.set(self.MEMORY_KEY, macros)

        added_names = self._format_action_names(added_steps)
        if skipped_steps:
            return f"Rutina '{macro_name}' actualizada. Agregue {added_names}; lo demas ya estaba incluido."
        return f"Rutina '{macro_name}' actualizada. Agregue {added_names}."

    def remove_steps(self, name: str, steps: list[dict[str, Any]]) -> str:
        macro_name = self._normalize_name(name)
        cleaned_steps = self._clean_steps(steps)
        if not cleaned_steps:
            return "No pude identificar que accion desea quitar de la rutina."

        macros = self._get_macros()
        macro = macros.get(macro_name)
        if not isinstance(macro, dict):
            return f"No encontre una rutina llamada '{macro_name}'."

        current_steps = macro.get("steps")
        if not isinstance(current_steps, list) or not current_steps:
            return f"La rutina '{macro_name}' no tiene acciones guardadas."

        actions_to_remove = {step["action"] for step in cleaned_steps}
        before_count = len(current_steps)
        remaining_steps = [
            step for step in current_steps
            if not isinstance(step, dict) or str(step.get("action", "")).strip() not in actions_to_remove
        ]
        removed_count = before_count - len(remaining_steps)
        if removed_count == 0:
            requested_names = self._format_action_names(cleaned_steps)
            return f"{requested_names} no estaba en la rutina '{macro_name}'."

        macro["steps"] = remaining_steps
        macros[macro_name] = macro
        self.memory.set(self.MEMORY_KEY, macros)

        removed_names = self._format_action_names(cleaned_steps)
        return f"Rutina '{macro_name}' actualizada. Quite {removed_names}."

    def get(self, name: str) -> list[dict[str, Any]] | None:
        macro_name = self._normalize_name(name)
        macro = self._get_macros().get(macro_name)
        if not isinstance(macro, dict):
            return None

        steps = macro.get("steps")
        return steps if isinstance(steps, list) else None

    def list_names(self) -> list[str]:
        return sorted(self._get_macros().keys())

    def delete(self, name: str) -> str:
        macro_name = self._normalize_name(name)
        macros = self._get_macros()
        if macro_name not in macros:
            return f"No encontre una rutina llamada '{macro_name}'."

        del macros[macro_name]
        self.memory.set(self.MEMORY_KEY, macros)
        return f"Rutina '{macro_name}' eliminada."

    def match_in_text(self, text: str) -> str | None:
        lowered = text.lower()
        for name in self.list_names():
            if re.search(rf"\b{re.escape(name)}\b", lowered):
                return name
        return None

    def _get_macros(self) -> dict[str, Any]:
        macros = self.memory.get(self.MEMORY_KEY, {})
        return macros if isinstance(macros, dict) else {}

    def _clean_steps(self, steps: list[dict[str, Any]]) -> list[dict[str, str]]:
        cleaned_steps: list[dict[str, str]] = []
        for step in steps:
            if not isinstance(step, dict):
                continue

            action = str(step.get("action", "")).strip()
            if not action:
                continue

            cleaned_step = {"action": action}
            action_input = str(step.get("action_input", "")).strip()
            if action_input:
                cleaned_step["action_input"] = action_input
            cleaned_steps.append(cleaned_step)

        return cleaned_steps

    def _step_exists(self, steps: list[Any], new_step: dict[str, str]) -> bool:
        for step in steps:
            if not isinstance(step, dict):
                continue
            if str(step.get("action", "")).strip() != new_step.get("action"):
                continue
            current_input = str(step.get("action_input", "")).strip()
            new_input = str(new_step.get("action_input", "")).strip()
            if current_input == new_input:
                return True
        return False

    def _format_action_names(self, steps: list[dict[str, str]]) -> str:
        labels = [self._action_label(step.get("action", "")) for step in steps]
        labels = [label for label in labels if label]
        if not labels:
            return "la accion indicada"
        if len(labels) == 1:
            return labels[0]
        return ", ".join(labels[:-1]) + f" y {labels[-1]}"

    def _action_label(self, action: str) -> str:
        labels = {
            "open_chrome": "Chrome",
            "open_vscode": "Visual Studio Code",
            "open_spotify": "Spotify",
            "open_terminal": "la terminal",
            "open_explorer": "el Explorador de archivos",
            "open_github": "GitHub",
            "close_chrome": "cerrar Chrome",
            "close_vscode": "cerrar Visual Studio Code",
            "close_spotify": "cerrar Spotify",
            "close_terminal": "cerrar la terminal",
            "set_volume": "ajustar el volumen",
            "mute": "silenciar el sistema",
            "unmute": "restaurar el sonido",
            "volume_up": "subir el volumen",
            "volume_down": "bajar el volumen",
            "brightness_up": "subir el brillo",
            "brightness_down": "bajar el brillo",
            "set_brightness": "ajustar el brillo",
            "web_search": "una busqueda web",
            "search_google": "una busqueda en Google",
        }
        return labels.get(action, action)

    def _normalize_name(self, name: str) -> str:
        return " ".join(str(name).lower().strip().split())
