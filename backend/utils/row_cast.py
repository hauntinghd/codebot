from typing import Any
import sqlite3

def row_to_dict(obj: Any) -> Any:
    """
    Recursively convert sqlite3.Row / tuples to plain dicts.
    This is the ONLY allowed shape crossing into API / streaming layers.
    """
    if isinstance(obj, sqlite3.Row):
        return {k: obj[k] for k in obj.keys()}

    if isinstance(obj, dict):
        return {k: row_to_dict(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple)):
        return [row_to_dict(v) for v in obj]

    return obj
