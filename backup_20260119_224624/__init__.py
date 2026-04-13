from __future__ import annotations

"""
backend.config package

Rule:
- NO importing backend.database / FastAPI routers from here (prevents circular imports).
- Export ALL config constants from backend/config/settings.py (copied from the original backend/config.py).
"""

from .settings import *  # noqa: F401,F403

# Optional: keep __all__ clean for star-import users
__all__ = [k for k in globals().keys() if k.isupper()]
