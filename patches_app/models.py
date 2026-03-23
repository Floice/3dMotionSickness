from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class PatchShape:
    shape_id: int
    kind: str
    x: int
    y: int
    width: int
    height: int

    def normalized(self) -> "PatchShape":
        width = max(20, int(self.width))
        height = max(20, int(self.height))
        x = int(self.x)
        y = int(self.y)
        return PatchShape(
            shape_id=int(self.shape_id),
            kind=self.kind if self.kind in {"rectangle", "circle"} else "rectangle",
            x=x,
            y=y,
            width=width,
            height=height,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self.normalized())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PatchShape":
        return cls(
            shape_id=int(data.get("shape_id", 0)),
            kind=str(data.get("kind", "rectangle")),
            x=int(data.get("x", 0)),
            y=int(data.get("y", 0)),
            width=int(data.get("width", 120)),
            height=int(data.get("height", 80)),
        ).normalized()
