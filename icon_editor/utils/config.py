import json
from pathlib import Path


DEFAULT_PATH = Path.home() / ".icon_editor_config.json"


class AppConfig:
    def __init__(self, path: Path | None = None):
        self.path = path or DEFAULT_PATH
        self.recent_files: list[str] = []
        self.theme: str = "System"
        self._load()

    def _load(self):
        try:
            if self.path.exists():
                data = json.loads(self.path.read_text(encoding="utf-8"))
                self.recent_files = list(data.get("recent_files", []))[:5]
                self.theme = str(data.get("theme", "System"))
        except Exception:
            self.recent_files = []
            self.theme = "System"

    def save(self):
        try:
            data = {
                "recent_files": self.recent_files[:5],
                "theme": self.theme
            }
            self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass
