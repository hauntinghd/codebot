from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class CorrectorBadge:
    """
    Minimal badge/metadata object referenced by chat.py.

    If your frontend displays a "Corrector" badge, it can read these fields.
    This module exists primarily to satisfy imports and keep backend startup stable.
    """
    name: str = "Corrector"
    version: str = "1.0"
    enabled: bool = True

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "enabled": self.enabled,
        }


# chat.py expects: `from backend.services.corrector_badge import corrector`
corrector = CorrectorBadge()
