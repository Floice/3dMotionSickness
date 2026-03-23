from __future__ import annotations

import json
from pathlib import Path

from .models import PatchShape


APP_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = APP_DIR / "patches_config.json"


class ConfigStore:
    def __init__(self, path: Path = CONFIG_PATH) -> None:
        self.path = path

    def load_shapes(self) -> list[PatchShape]:
        if not self.path.exists():
            return []

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []

        shapes: list[PatchShape] = []
        for item in payload.get("shapes", []):
            if isinstance(item, dict):
                shapes.append(PatchShape.from_dict(item))
        return shapes

    def save_shapes(self, shapes: list[PatchShape]) -> None:
        payload = {"shapes": [shape.to_dict() for shape in shapes]}
        self.path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
