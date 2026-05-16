from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from google import genai


class GeminiBrain:
    def __init__(self, api_key: str, model_name: str) -> None:
        self.api_key = api_key
        self.model_name = model_name
        self.client = genai.Client(api_key=api_key) if api_key else None

    def analyze(self, text: str) -> dict[str, Any]:
        """Classify user input into a basic intent payload."""
        if not text.strip():
            return {"intent": "chat", "response": "No entendi ningun comando."}

        fallback = self._fallback_analysis(text)

        if self.client is None:
            return fallback

        if fallback.get("intent") == "action":
            return fallback

        try:
            prompt_path = Path("CerebroJarvis.md")
            if prompt_path.exists():
                base_prompt = prompt_path.read_text(encoding="utf-8")
            else:
                base_prompt = "Eres Jarvis, un asistente de escritorio. Clasifica la entrada y responde solo JSON valido."
            
            prompt = f"{base_prompt}\n\nEntrada del usuario: {text}"

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            return self._parse_response(response.text or "")
        except Exception:
            return self._fallback_analysis(text)

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
        if "terminal" in lowered or "powershell" in lowered or "consola" in lowered:
            return {"intent": "action", "action": "open_terminal"}
        if "explorador" in lowered or "explorer" in lowered or "archivos" in lowered:
            return {"intent": "action", "action": "open_explorer"}
        if "github" in lowered and any(word in lowered for word in ["abre", "abrir", "open"]):
            return {"intent": "action", "action": "open_github"}

        google_match = re.search(r"(?:busca|buscar|buscame|búscame|googlea)\s+(.*)", lowered)
        if google_match and google_match.group(1).strip():
            return {
                "intent": "action",
                "action": "search_google",
                "action_input": google_match.group(1).strip(),
            }

        return {
            "intent": "chat",
            "response": "Todavia no tengo conexion a Gemini. Puedo seguir con acciones basicas locales.",
        }

    def _parse_response(self, raw_text: str) -> dict[str, Any]:
        cleaned = raw_text.strip()
        if not cleaned:
            return self._fallback_analysis("")

        fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
        if fenced_match:
            cleaned = fenced_match.group(1)
        else:
            json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if json_match:
                cleaned = json_match.group(0)

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            return {
                "intent": "chat",
                "response": cleaned,
            }

        if parsed.get("intent") == "action" and parsed.get("action"):
            if "action_input" in parsed and parsed["action_input"] is None:
                parsed.pop("action_input")
            return parsed

        if parsed.get("intent") == "chat":
            parsed.setdefault("response", "No tengo una respuesta lista todavia.")
            return parsed

        return {
            "intent": "chat",
            "response": "No pude interpretar correctamente la respuesta del modelo.",
        }
