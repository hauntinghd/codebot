"""Multi-media file handler for CodeBot.

Supports:
- Images: PNG, WebP, JPEG (up to 20)
- Video: MP4 (up to 1)
- Audio: MP3, WAV, M4A
- Code: Any text file
- Archives: ZIP
"""

from __future__ import annotations

import json
import logging
import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("codebot")

# File type configurations
FILE_CONFIGS = {
    "images": {
        "extensions": [".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"],
        "mimetypes": ["image/png", "image/jpeg", "image/webp", "image/gif", "image/bmp"],
        "max_count": 20,
        "max_size_mb": 5,
        "description": "Images (PNG, JPEG, WebP, GIF, BMP)",
    },
    "video": {
        "extensions": [".mp4", ".webm", ".mov", ".avi"],
        "mimetypes": ["video/mp4", "video/webm", "video/quicktime", "video/x-msvideo"],
        "max_count": 1,
        "max_size_mb": 100,
        "description": "Video (MP4, WebM, MOV, AVI)",
    },
    "audio": {
        "extensions": [".mp3", ".wav", ".m4a", ".aac", ".ogg"],
        "mimetypes": ["audio/mpeg", "audio/wav", "audio/mp4", "audio/aac", "audio/ogg"],
        "max_count": 5,
        "max_size_mb": 50,
        "description": "Audio (MP3, WAV, M4A, AAC, OGG)",
    },
    "code": {
        "extensions": [
            ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".cpp", ".c", ".h", ".hpp",
            ".cs", ".rb", ".go", ".rs", ".php", ".swift", ".kt", ".scala", ".r",
            ".html", ".css", ".xml", ".json", ".yaml", ".yml", ".toml", ".ini", ".env",
            ".sql", ".sh", ".bash", ".md", ".txt"
        ],
        "mimetypes": [
            "text/plain", "text/x-python", "text/javascript", "text/typescript",
            "text/x-java", "text/x-c", "text/x-csharp", "text/x-ruby", "text/x-go",
            "text/html", "text/css", "application/json", "application/xml",
            "text/x-yaml", "application/x-sh", "text/x-shellscript", "text/markdown"
        ],
        "max_count": 100,
        "max_size_mb": 10,
        "description": "Code files (Python, JavaScript, Java, C++, etc.)",
    },
    "archive": {
        "extensions": [".zip", ".tar", ".gz", ".rar", ".7z"],
        "mimetypes": ["application/zip", "application/x-tar", "application/gzip", "application/x-rar-compressed", "application/x-7z-compressed"],
        "max_count": 5,
        "max_size_mb": 50,
        "description": "Archives (ZIP, TAR, GZ, RAR, 7Z)",
    },
}

# Reverse mapping for quick lookup
EXTENSION_TO_TYPE = {}
MIMETYPE_TO_TYPE = {}
for file_type, config in FILE_CONFIGS.items():
    for ext in config["extensions"]:
        EXTENSION_TO_TYPE[ext.lower()] = file_type
    for mime in config["mimetypes"]:
        MIMETYPE_TO_TYPE[mime.lower()] = file_type


class FileValidator:
    """Validates files for CodeBot upload."""

    @staticmethod
    def get_file_type(filename: str, mimetype: Optional[str] = None) -> Optional[str]:
        """Determine file type from extension or MIME type."""
        # Try extension first
        ext = Path(filename).suffix.lower()
        if ext in EXTENSION_TO_TYPE:
            return EXTENSION_TO_TYPE[ext]

        # Try MIME type
        if mimetype:
            mime_lower = mimetype.lower()
            if mime_lower in MIMETYPE_TO_TYPE:
                return MIMETYPE_TO_TYPE[mime_lower]

        # Guess from filename
        guessed_mime, _ = mimetypes.guess_type(filename)
        if guessed_mime and guessed_mime.lower() in MIMETYPE_TO_TYPE:
            return MIMETYPE_TO_TYPE[guessed_mime.lower()]

        return None

    @staticmethod
    def validate_file(
        filename: str,
        file_size: int,
        mimetype: Optional[str] = None,
        current_uploads: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        """
        Validate a file for upload.

        Args:
            filename: Original filename
            file_size: File size in bytes
            mimetype: MIME type (optional)
            current_uploads: Current upload counts by type (optional)

        Returns:
            {
                "valid": bool,
                "file_type": str or None,
                "error": str or None,
                "message": str or None,
            }
        """
        if current_uploads is None:
            current_uploads = {}

        # Get file type
        file_type = FileValidator.get_file_type(filename, mimetype)
        if not file_type:
            return {
                "valid": False,
                "file_type": None,
                "error": "Unsupported file type",
                "message": f"'{filename}' is not a supported file type. Supported: images, video, audio, code, archives.",
            }

        config = FILE_CONFIGS[file_type]

        # Check file size
        max_bytes = config["max_size_mb"] * 1024 * 1024
        if file_size > max_bytes:
            return {
                "valid": False,
                "file_type": file_type,
                "error": "File too large",
                "message": f"{config['description']} must be <= {config['max_size_mb']}MB. Got {file_size / 1024 / 1024:.1f}MB.",
            }

        # Check count limit
        current_count = current_uploads.get(file_type, 0)
        if current_count >= config["max_count"]:
            return {
                "valid": False,
                "file_type": file_type,
                "error": "Too many files",
                "message": f"Maximum {config['max_count']} {file_type} files allowed. You have {current_count}.",
            }

        return {
            "valid": True,
            "file_type": file_type,
            "error": None,
            "message": f"✓ {config['description']} - {file_size / 1024:.1f}KB",
        }

    @staticmethod
    def get_summary(uploads_by_type: Dict[str, List[Dict]]) -> str:
        """Get human-readable summary of uploaded files."""
        if not uploads_by_type:
            return "No files uploaded"

        lines = []
        for file_type, files in uploads_by_type.items():
            if not files:
                continue
            config = FILE_CONFIGS.get(file_type)
            if config:
                count = len(files)
                total_size = sum(f.get("size", 0) for f in files) / 1024 / 1024
                lines.append(f"• {config['description']}: {count} file{'s' if count != 1 else ''} ({total_size:.1f}MB)")

        return "\n".join(lines) if lines else "No files uploaded"


class MultiMediaAnalyzer:
    """Analyzes media files for CodeBot."""

    @staticmethod
    def should_use_vision(file_type: str) -> bool:
        """Check if file should use vision API."""
        return file_type == "images"

    @staticmethod
    def should_transcribe(file_type: str) -> bool:
        """Check if file should be transcribed."""
        return file_type == "audio"

    @staticmethod
    def should_extract(file_type: str) -> bool:
        """Check if file should be extracted/parsed."""
        return file_type in ("archive", "code")

    @staticmethod
    def get_analysis_cost(file_type: str, file_size: int) -> Dict[str, Any]:
        """
        Estimate analysis cost for a file.

        Returns token estimate and cost in credits.
        """
        # Base costs per file type (in estimated tokens)
        base_tokens = {
            "images": 500,      # Per image (vision API)
            "video": 2000,      # For video frame extraction
            "audio": 1000,      # For transcription
            "code": 100,        # Per KB of code
            "archive": 500,     # For extraction overhead
        }

        # Calculate tokens
        if file_type == "code":
            tokens = base_tokens[file_type] * (file_size / 1024)
        else:
            tokens = base_tokens.get(file_type, 100)

        # Rough cost estimate ($0.05 per 1M tokens for gpt-4o-mini)
        cost = (tokens / 1000000) * 0.00015

        return {
            "file_type": file_type,
            "estimated_tokens": int(tokens),
            "estimated_cost": cost,
            "description": f"Analysis of {file_type} file",
        }


# Export for use in routes
__all__ = [
    "FILE_CONFIGS",
    "EXTENSION_TO_TYPE",
    "MIMETYPE_TO_TYPE",
    "FileValidator",
    "MultiMediaAnalyzer",
]
