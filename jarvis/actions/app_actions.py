from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


class AppActions:
    def __init__(self) -> None:
        local_app_data = Path(os.getenv("LOCALAPPDATA", ""))
        app_data = Path(os.getenv("APPDATA", ""))
        program_files = Path(os.getenv("PROGRAMFILES", "C:\\Program Files"))
        program_files_x86 = Path(os.getenv("PROGRAMFILES(X86)", "C:\\Program Files (x86)"))

        self.chrome_candidates = [
            shutil.which("chrome"),
            str(program_files / "Google/Chrome/Application/chrome.exe"),
            str(program_files_x86 / "Google/Chrome/Application/chrome.exe"),
        ]
        self.vscode_candidates = [
            shutil.which("code"),
            str(local_app_data / "Programs/Microsoft VS Code/Code.exe"),
        ]
        self.spotify_candidates = [
            shutil.which("spotify"),
            str(app_data / "Spotify/Spotify.exe"),
            str(local_app_data / "Microsoft/WindowsApps/Spotify.exe"),
        ]
        self.terminal_candidates = [
            shutil.which("wt"),
            shutil.which("powershell"),
            shutil.which("cmd"),
        ]

    def open_chrome(self) -> str:
        return self._open_from_candidates(
            self.chrome_candidates,
            "Abriendo Google Chrome.",
            fallback=lambda: os.startfile("https://www.google.com"),
            fallback_message="Chrome no aparecio instalado. Abrire tu navegador predeterminado.",
        )

    def open_vscode(self) -> str:
        return self._open_from_candidates(
            self.vscode_candidates,
            "Abriendo Visual Studio Code.",
        )

    def open_spotify(self) -> str:
        return self._open_from_candidates(
            self.spotify_candidates,
            "Abriendo Spotify.",
            fallback=lambda: os.startfile("spotify:"),
            fallback_message="Intentando abrir Spotify con el lanzador del sistema.",
        )

    def open_terminal(self) -> str:
        return self._open_from_candidates(
            self.terminal_candidates,
            "Abriendo la terminal.",
        )

    def open_file_explorer(self) -> str:
        subprocess.Popen(["explorer"])
        return "Abriendo el Explorador de archivos."

    def close_app(self, process_name: str, display_name: str) -> str:
        """Cierra un proceso de Windows por nombre de ejecutable."""
        try:
            result = subprocess.run(
                ["taskkill", "/F", "/IM", process_name],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                return f"{display_name} cerrado."
            return f"{display_name} no estaba abierto."
        except Exception as exc:
            return f"No pude cerrar {display_name}: {exc}"

    def close_chrome(self) -> str:
        return self.close_app("chrome.exe", "Google Chrome")

    def close_vscode(self) -> str:
        return self.close_app("Code.exe", "Visual Studio Code")

    def close_spotify(self) -> str:
        return self.close_app("Spotify.exe", "Spotify")

    def close_terminal(self) -> str:
        return self.close_app("WindowsTerminal.exe", "La terminal")

    def execute(self, action_name: str) -> str:
        actions = {
            "open_chrome": self.open_chrome,
            "open_vscode": self.open_vscode,
            "open_spotify": self.open_spotify,
            "open_terminal": self.open_terminal,
            "open_explorer": self.open_file_explorer,
            "close_chrome": self.close_chrome,
            "close_vscode": self.close_vscode,
            "close_spotify": self.close_spotify,
            "close_terminal": self.close_terminal,
        }

        handler = actions.get(action_name)
        if handler is None:
            return "No reconozco esa accion todavia."

        try:
            return handler()
        except Exception as exc:
            return f"No pude ejecutar la accion {action_name}: {exc}"

    def _open_from_candidates(
        self,
        candidates: list[str | None],
        success_message: str,
        fallback=None,
        fallback_message: str | None = None,
    ) -> str:
        for candidate in candidates:
            if not candidate:
                continue

            candidate_path = Path(candidate)
            try:
                if candidate_path.exists():
                    os.startfile(str(candidate_path))
                    return success_message

                command = shutil.which(candidate)
                if command:
                    subprocess.Popen([command])
                    return success_message
            except Exception:
                continue

        if fallback is not None:
            fallback()
            return fallback_message or success_message

        raise FileNotFoundError("No encontre una aplicacion compatible en Windows.")
