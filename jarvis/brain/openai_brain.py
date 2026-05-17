from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from openai import OpenAI

from jarvis.memory.storage import MemoryManager


class OpenAIBrain:
    def __init__(self, api_key: str, model_name: str = "gpt-4o-mini") -> None:
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name
        self.memory = MemoryManager()
        self.history = []

    def analyze(self, text: str) -> dict[str, Any]:
        """
        Envía el texto del usuario al LLM junto con el prompt del sistema.
        Retorna un dict con la intención, acción y respuesta según el CerebroJarvis.md
        """
        try:
            prompt_path = Path("CerebroJarvis.md")
            if prompt_path.exists():
                base_prompt = prompt_path.read_text(encoding="utf-8")
            else:
                base_prompt = "Eres Jarvis, un asistente de escritorio. Clasifica la entrada y responde solo JSON valido."
            
            # Inyectar memoria a largo plazo
            known_memory = self.memory.get_all()
            if known_memory:
                memory_str = json.dumps(known_memory, indent=2, ensure_ascii=False)
                base_prompt += f"\n\n==================================================\nCURRENT LONG-TERM MEMORY:\n{memory_str}\n=================================================="

            messages = [{"role": "system", "content": base_prompt}]
            messages.extend(self.history)
            messages.append({"role": "user", "content": text})

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                response_format={"type": "json_object"}
            )
            
            response_text = response.choices[0].message.content or "{}"
            parsed = self._parse_response(response_text)

            # Actualizar memoria a corto plazo
            self.history.append({"role": "user", "content": text})
            assistant_reply = parsed.get("response", "")
            self.history.append({"role": "assistant", "content": f"Jarvis: {assistant_reply}"})
            
            # Limitar historial (ultimos 10 mensajes = 5 interacciones)
            if len(self.history) > 10:
                self.history = self.history[-10:]

            # Actualizar memoria a largo plazo si lo pide el JSON
            save_memory = parsed.get("save_memory")
            if isinstance(save_memory, dict):
                self.memory.update_dict(save_memory)
                print(f"Jarvis> [Memoria Actualizada]: {save_memory}")

            return parsed
        except Exception as e:
            print(f"Jarvis> [Debug OpenAI] Error: {e}")
            return self._fallback_analysis(text)

    def _parse_response(self, response_text: str) -> dict[str, Any]:
        """Intenta parsear el JSON de la respuesta."""
        try:
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            parsed = json.loads(cleaned)
            return parsed
        except json.JSONDecodeError:
            return {
                "intent": "chat",
                "response": "Lo siento, mi respuesta fue confusa internamente."
            }

    def _fallback_analysis(self, text: str) -> dict[str, Any]:
        lowered = text.lower()

        if any(phrase in lowered for phrase in ["que hora es", "qué hora es", "dime la hora", "hora actual"]):
            return {"intent": "action", "action": "get_time"}
        if "chrome" in lowered:
            return {"intent": "action", "action": "open_chrome"}
        if "visual studio code" in lowered or "vscode" in lowered or "vs code" in lowered:
            return {"intent": "action", "action": "open_vscode"}
        if "spotify" in lowered:
            return {"intent": "action", "action": "open_spotify"}
        if "github" in lowered:
            return {"intent": "action", "action": "open_github"}
        if "terminal" in lowered:
            return {"intent": "action", "action": "open_terminal"}
        if "explorador" in lowered or "archivos" in lowered:
            return {"intent": "action", "action": "open_files"}

        return {
            "intent": "chat",
            "response": "Todavia no tengo conexion a OpenAI. Puedo seguir con acciones basicas locales."
        }
