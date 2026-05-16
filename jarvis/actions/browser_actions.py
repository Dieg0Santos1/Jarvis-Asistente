from __future__ import annotations

import webbrowser
from urllib.parse import quote_plus


class BrowserActions:
    def open_url(self, url: str) -> str:
        webbrowser.open(url)
        return f"Abriendo {url}."

    def search_google(self, query: str) -> str:
        webbrowser.open(f"https://www.google.com/search?q={quote_plus(query)}")
        return f'Buscando "{query}" en Google.'

    def open_github(self) -> str:
        webbrowser.open("https://github.com")
        return "Abriendo GitHub."
