from __future__ import annotations

from typing import Any

from openai import OpenAI


class SearchActions:
    """
    Realiza búsquedas en internet mediante DuckDuckGo y resume
    los resultados usando OpenAI para dar una respuesta natural y hablada.
    """

    def __init__(self, openai_api_key: str, openai_model: str = "gpt-4o-mini") -> None:
        self.client = OpenAI(api_key=openai_api_key)
        self.model = openai_model

    def search_and_summarize(self, query: str) -> str:
        """
        1. Busca en DuckDuckGo (sin API key, sin límites)
        2. Extrae los fragmentos más relevantes
        3. Llama a OpenAI para resumirlos en una respuesta corta y hablada
        4. Devuelve el texto listo para que Jarvis lo lea en voz alta
        """
        try:
            snippets = self._duckduckgo_search(query)
        except Exception as e:
            return f"No pude hacer la búsqueda en internet: {e}"

        if not snippets:
            return "No encontré información relevante sobre eso en internet."

        context = "\n\n".join(snippets[:5])  # Máximo 5 fragmentos para no saturar el prompt

        try:
            prompt = (
                "Eres Jarvis, un asistente de escritorio. "
                "Tu usuario te preguntó algo y buscaste en internet. "
                "Resumí los siguientes resultados en 1-3 oraciones cortas, naturales y directas. "
                "Habla en primera persona como si tú supieras la información. "
                "No menciones que buscaste en internet ni que hay fuentes. Solo da la respuesta.\n\n"
                f"Pregunta original: {query}\n\n"
                f"Resultados de internet:\n{context}"
            )

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            # Si falla la IA, devolver el primer snippet directamente
            return snippets[0] if snippets else "No pude procesar los resultados."

    def _duckduckgo_search(self, query: str) -> list[str]:
        """Busca en DuckDuckGo y devuelve una lista de fragmentos de texto."""
        from ddgs import DDGS

        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, region="es-419", max_results=6):
                body = r.get("body", "").strip()
                title = r.get("title", "").strip()
                if body:
                    results.append(f"{title}: {body}")

        return results
