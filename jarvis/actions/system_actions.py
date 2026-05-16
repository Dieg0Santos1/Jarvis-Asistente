from __future__ import annotations

from datetime import datetime


class SystemActions:
    def get_current_time(self) -> str:
        now = datetime.now()
        return f"Son las {now.strftime('%H:%M')}."

    def lock_pc(self) -> None:
        raise NotImplementedError("System actions are not wired yet.")
