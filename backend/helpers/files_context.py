"""
backend/helpers/files_context.py

Safe helper used by backend/routes/chat.py to build a "files context" block.

Design goals:
- Must exist so imports never crash startup.
- Must be safe: do not read arbitrary paths outside project.
- Must be cheap: cap output size.
- If no files are provided, return empty string.

This is intentionally minimal and can be expanded later.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence


# Hard safety caps to prevent huge prompts / memory spikes
MAX_FILES = 30
MAX_BYTES_PER_FILE = 80_000      # ~80KB per file
MAX_TOTAL_BYTES = 250_000        # ~250KB total content returned


@dataclass
class FileItem:
    path: str
    content: Optional[str] = None


def _is_safe_path(project_root: str, candidate: str) -> bool:
    project_root = os.path.realpath(project_root)
    candidate_real = os.path.realpath(candidate)
    return candidate_real.startswith(project_root + os.sep) or candidate_real == project_root


def _read_text_file(path: str, max_bytes: int) -> str:
    # Read as bytes then decode forgivingly; prevents weird encoding crashes.
    with open(path, "rb") as f:
        data = f.read(max_bytes + 1)
    if len(data) > max_bytes:
        data = data[:max_bytes]
    return data.decode("utf-8", errors="replace")


def build_file_context(
    files: Optional[Sequence[str]] = None,
    *,
    project_root: Optional[str] = None,
) -> str:
    """
    Return a prompt-ready block containing selected file contents.

    `files` is expected to be a list of repo-relative or absolute paths.
    Only files within project_root are allowed (defaults to cwd).
    """
    if not files:
        return ""

    root = project_root or os.getcwd()
    root = os.path.realpath(root)

    selected: list[str] = []
    total_bytes = 0
    count = 0

    for p in files:
        if count >= MAX_FILES:
            break

        # If relative, interpret relative to root
        candidate = p
        if not os.path.isabs(candidate):
            candidate = os.path.join(root, candidate)

        # Must be inside repo root
        if not _is_safe_path(root, candidate):
            continue

        # Must exist and be a regular file
        if not os.path.isfile(candidate):
            continue

        remaining = MAX_TOTAL_BYTES - total_bytes
        if remaining <= 0:
            break

        # Read with per-file + remaining caps
        cap = min(MAX_BYTES_PER_FILE, remaining)
        try:
            text = _read_text_file(candidate, cap)
        except Exception:
            continue

        block = f"\n--- FILE: {os.path.relpath(candidate, root)} ---\n{text}\n"
        b = len(block.encode("utf-8", errors="ignore"))

        if total_bytes + b > MAX_TOTAL_BYTES:
            break

        selected.append(block)
        total_bytes += b
        count += 1

    if not selected:
        return ""

    return "## Attached File Context\n" + "".join(selected)
