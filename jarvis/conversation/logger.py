from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


class ConversationLogger:
    """Writes daily Markdown logs for Jarvis interactions."""

    def __init__(self, base_dir: str = "logs/conversaciones") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def log_interaction(
        self,
        user_text: str,
        response: str,
        *,
        intent: str = "",
        action: str = "",
        action_input: Any = "",
    ) -> None:
        now = datetime.now()
        log_path = self._path_for_date(now)
        if not log_path.exists():
            log_path.write_text(f"# Conversacion {now:%Y-%m-%d}\n\n", encoding="utf-8")

        metadata = []
        if intent:
            metadata.append(f"intent={intent}")
        if action:
            metadata.append(f"action={action}")
        if action_input:
            metadata.append(f"input={self._format_value(action_input)}")

        metadata_text = f" ({'; '.join(metadata)})" if metadata else ""
        entry = (
            f"## [{now:%H:%M:%S}]{metadata_text}\n"
            f"**Usuario:** {user_text.strip()}\n\n"
            f"**Jarvis:** {response.strip()}\n\n"
        )
        with log_path.open("a", encoding="utf-8") as file:
            file.write(entry)

    def get_today_text(self) -> str:
        path = self._path_for_date(datetime.now())
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def _path_for_date(self, date: datetime) -> Path:
        return self.base_dir / f"conversacion_{date:%Y-%m-%d}.md"

    def _format_value(self, value: Any) -> str:
        text = str(value).replace("\n", " ").strip()
        if len(text) <= 120:
            return text
        return text[:117].rstrip() + "..."
