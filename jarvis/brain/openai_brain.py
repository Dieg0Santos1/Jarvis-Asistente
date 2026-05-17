from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from queue import Empty, Queue
from typing import Any, Generator

from openai import OpenAI

from jarvis.memory.storage import MemoryManager


class OpenAIBrain:
    def __init__(self, api_key: str, model_name: str = "gpt-4o-mini") -> None:
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name
        self.memory = MemoryManager()
        self.history: list[dict] = []
        self._base_prompt: str = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        """Carga el CerebroJarvis.md una sola vez al arrancar. Nunca se vuelve a leer del disco."""
        prompt_path = Path("CerebroJarvis.md")
        if prompt_path.exists():
            prompt = prompt_path.read_text(encoding="utf-8")
            print(f"Jarvis> [Cerebro cargado: {len(prompt)} caracteres]")
            return prompt
        print("Jarvis> [Advertencia: CerebroJarvis.md no encontrado. Usando prompt base.]")
        return "Eres Jarvis, un asistente de escritorio. Clasifica la entrada y responde solo JSON valido."

    def analyze(self, text: str) -> dict[str, Any]:
        """
        Envía el texto del usuario al LLM junto con el prompt del sistema.
        Retorna un dict con la intención, acción y respuesta según el CerebroJarvis.md
        """
        try:
            messages = self._build_messages(text)

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

    def _build_messages(self, text: str) -> list[dict]:
        """Construye la lista de mensajes inyectando la memoria a largo plazo al prompt ya cacheado."""
        prompt = self._base_prompt

        known_memory = self.memory.get_all()
        if known_memory:
            memory_str = json.dumps(known_memory, indent=2, ensure_ascii=False)
            prompt += f"\n\n==================================================\nCURRENT LONG-TERM MEMORY:\n{memory_str}\n=================================================="

        messages = [{"role": "system", "content": prompt}]
        messages.extend(self.history)
        messages.append({"role": "user", "content": text})
        return messages

    def stream_chat(self, text: str) -> Generator[str, None, None]:
        """
        Streaming de respuesta de chat por oraciones completas.
        Yield: una oración a la vez, tan pronto como termina de formarse.
        Para respuestas de tipo 'chat' SOLAMENTE.
        """
        SENTENCE_END = re.compile(r'(?<=[.!?…])\s+|(?<=[,;:])\s+(?=\S{4,})')
        buffer = ""
        full_response = ""

        try:
            messages = self._build_messages(text)
            # Usamos texto plano en streaming (no json_object, no compatible con stream)
            messages[0]["content"] += (
                "\n\nIMPORTANT FOR THIS REQUEST: Respond in plain text only (no JSON). "
                "Give a concise, natural spoken answer in Spanish. No markdown, no lists."
            )

            with self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                stream=True,
            ) as stream:
                for chunk in stream:
                    delta = chunk.choices[0].delta.content or ""
                    buffer += delta
                    full_response += delta

                    # Detectar fin de oración para emitir
                    parts = SENTENCE_END.split(buffer)
                    if len(parts) > 1:
                        for sentence in parts[:-1]:
                            sentence = sentence.strip()
                            if sentence:
                                yield sentence
                        buffer = parts[-1]

            # Emitir lo que quede en el buffer
            remaining = buffer.strip()
            if remaining:
                yield remaining

            # Actualizar historial con la respuesta completa
            self.history.append({"role": "user", "content": text})
            self.history.append({"role": "assistant", "content": full_response})
            if len(self.history) > 10:
                self.history = self.history[-10:]

        except Exception as e:
            print(f"Jarvis> [Debug Streaming] Error: {e}")
            yield "Disculpe, hubo un error al procesar mi respuesta."

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
