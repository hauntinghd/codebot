"""Helper functions for file operations, projects, and utilities."""
from __future__ import annotations

import logging
import zipfile
from pathlib import Path
from typing import List, Tuple

from fastapi import HTTPException

from backend.config import MAX_FILE_READ_BYTES, TOKENS_PER_CHAR

logger = logging.getLogger("codebot")


def safe_join(root: Path, rel: str) -> Path:
    """Safely join paths with traversal protection."""
    rel = rel.lstrip("/").lstrip("\\")
    p = (root / rel).resolve()
    if not str(p).startswith(str(root)):
        raise HTTPException(status_code=400, detail="Invalid path")
    return p


def extract_zip_safely(zip_path: Path, dest_dir: Path) -> None:
    """Safely extract ZIP file with path traversal protection."""
    max_file_size = 100 * 1024 * 1024  # 100MB per file limit
    max_total_size = 500 * 1024 * 1024  # 500MB total limit
    total_size = 0
    file_count = 0
    max_files = 10000  # Prevent zip bombs
    
    with zipfile.ZipFile(zip_path, "r") as z:
        # Check for zip bomb (too many files or too large)
        for info in z.infolist():
            file_count += 1
            if file_count > max_files:
                raise HTTPException(status_code=400, detail="ZIP contains too many files")
            if info.file_size > max_file_size:
                raise HTTPException(status_code=400, detail=f"File {info.filename} exceeds size limit")
            total_size += info.file_size
            if total_size > max_total_size:
                raise HTTPException(status_code=400, detail="ZIP total size exceeds limit")
        
        # Extract with path validation
        for info in z.infolist():
            name = info.filename.replace("\\", "/")
            # Prevent path traversal
            if name.startswith("/") or ".." in name.split("/"):
                raise HTTPException(status_code=400, detail="Unsafe ZIP contents: path traversal detected")
            # Prevent absolute paths
            if name.startswith("C:") or name.startswith("/"):
                raise HTTPException(status_code=400, detail="Unsafe ZIP contents: absolute path detected")
            
            out_path = (dest_dir / name).resolve()
            # Ensure extracted file is within destination directory
            if not str(out_path).startswith(str(dest_dir.resolve())):
                raise HTTPException(status_code=400, detail="Unsafe ZIP contents: path outside destination")
        z.extractall(dest_dir)


def walk_files(root: Path) -> List[str]:
    """Walk directory tree and return relative file paths."""
    out: List[str] = []
    for p in root.rglob("*"):
        if p.is_file():
            rel = str(p.relative_to(root)).replace("\\", "/")
            out.append(rel)
    out.sort()
    return out


def read_text_file_limited(path: Path, limit: int = MAX_FILE_READ_BYTES) -> str:
    """Read text file with size limit and encoding detection."""
    try:
        # Check file size first
        file_size = path.stat().st_size
        if file_size > limit:
            # Read only up to limit
            with path.open("rb") as f:
                data = f.read(limit)
        else:
            data = path.read_bytes()
    except (OSError, IOError, PermissionError) as e:
        logger.warning(f"Failed to read file {path}: {e}")
        return ""
    except Exception as e:
        logger.warning(f"Unexpected error reading file {path}: {e}")
        return ""
    
    # Try UTF-8 first, then fallback encodings
    for encoding in ["utf-8", "latin-1", "cp1252"]:
        try:
            return data.decode(encoding, errors="replace")
        except (UnicodeDecodeError, LookupError):
            continue
    
    # Last resort: replace errors
    return data.decode(errors="replace")


def file_importance_score(rel_path: str) -> int:
    """Score file importance (higher = more important). Prioritize important files for context."""
    path_lower = rel_path.lower()
    score = 0
    
    # High priority: README, main files, configs
    if any(name in path_lower for name in ["readme", "main", "index", "app", "server", "entry"]):
        score += 100
    if any(name in path_lower for name in ["package.json", "requirements.txt", "pyproject.toml", "cargo.toml", "go.mod", "pom.xml"]):
        score += 90
    if any(name in path_lower for name in [".env.example", "config", "settings", ".gitignore"]):
        score += 80
    
    # Code files get priority
    code_exts = [".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".cpp", ".c", ".h", ".cs", ".php", ".rb", ".swift", ".kt"]
    if any(path_lower.endswith(ext) for ext in code_exts):
        score += 50
    
    # Penalize: node_modules, .git, dist, build, __pycache__, .venv
    if any(skip in path_lower for skip in ["node_modules", ".git", "dist", "build", "__pycache__", ".venv", ".next", ".nuxt", "vendor"]):
        score -= 1000  # Effectively exclude
    
    # Penalize: test files (lower priority but still include if space)
    if "test" in path_lower or "spec" in path_lower:
        score -= 20
    
    # Prefer root-level files
    depth = rel_path.count("/")
    score -= depth * 5  # Prefer shallower files
    
    return score


def estimate_tokens(text: str) -> int:
    """Estimate token count from text (rough: ~4 chars per token)."""
    return int(len(text) * TOKENS_PER_CHAR)


def select_model(message: str, file_count: int = 0, code_length: int = 0) -> str:
    """
    MVP cost optimization: Select model based on task complexity.
    Defaults to mini (cheaper) - only use best model for very complex tasks.
    Returns: "gpt-4o-mini" or "gpt-4o"
    """
    from backend.config import OPENAI_MODEL_BEST, OPENAI_MODEL_MINI
    
    # MVP: Use best model only for very complex tasks to save costs
    # For most tasks, mini is sufficient and 16x cheaper
    if file_count > 5 or code_length > 10000:
        return OPENAI_MODEL_BEST
    
    msg_lower = message.lower()
    
    # Complex keywords that require best model
    complex_keywords = [
        "refactor", "optimize", "architecture", "design", "security", "performance",
        "debug", "fix bug", "error", "exception", "complex", "algorithm", "data structure"
    ]
    
    # Simple keywords that can use mini
    simple_keywords = [
        "fix typo", "format", "indent", "add import", "simple", "add comment",
        "rename", "move", "copy", "delete", "create file"
    ]
    
    if any(kw in msg_lower for kw in complex_keywords):
        return OPENAI_MODEL_BEST
    if any(kw in msg_lower for kw in simple_keywords):
        return OPENAI_MODEL_MINI
    
    # Short messages likely simple tasks
    if len(message) < 200:
        return OPENAI_MODEL_MINI
    
    # Default: use mini for cost savings, can upgrade if needed
    return OPENAI_MODEL_MINI


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost in dollars for a given model and token usage."""
    from backend.config import MODEL_PRICING
    
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["gpt-4o-mini"])
    input_cost = (input_tokens / 1000.0) * pricing["input_per_1k"]
    output_cost = (output_tokens / 1000.0) * pricing["output_per_1k"]
    return input_cost + output_cost


def estimate_cost(model: str, estimated_input_tokens: int, estimated_output_tokens: int) -> float:
    """Estimate cost before making API call."""
    return calculate_cost(model, estimated_input_tokens, estimated_output_tokens)

