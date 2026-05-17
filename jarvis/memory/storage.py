import json
from pathlib import Path
from typing import Any

class MemoryManager:
    """
    Gestiona la memoria a largo plazo de Jarvis.
    Usa un archivo JSON local para mayor velocidad y privacidad.
    """
    def __init__(self, filepath: str = "memory.json"):
        self.filepath = Path(filepath)
        self._memory_cache = {}
        self._load()

    def _load(self):
        if self.filepath.exists():
            try:
                self._memory_cache = json.loads(self.filepath.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self._memory_cache = {}
        else:
            self._memory_cache = {}
            self._save()

    def _save(self):
        self.filepath.write_text(json.dumps(self._memory_cache, indent=4, ensure_ascii=False), encoding="utf-8")

    def get_all(self) -> dict[str, Any]:
        """Devuelve toda la memoria a largo plazo almacenada."""
        return self._memory_cache

    def get(self, key: str, default: Any = None) -> Any:
        return self._memory_cache.get(key, default)

    def set(self, key: str, value: Any):
        """Guarda o actualiza un dato en la memoria."""
        self._memory_cache[key] = value
        self._save()

    def update_dict(self, data: dict[str, Any]):
        """Actualiza múltiples datos a la vez."""
        self._memory_cache.update(data)
        self._save()
