"""Agent Memory System.

Provides persistent memory and context management for agents.
Enables learning from past sessions and maintaining coherent state.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("codebot.agents")


@dataclass
class MemoryEntry:
    """A single memory entry."""
    key: str
    value: Any
    entry_type: str  # "fact", "decision", "code", "error", "feedback"
    importance: float = 1.0  # 0-1 scale
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        return self.expires_at is not None and time.time() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "entry_type": self.entry_type,
            "importance": self.importance,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        return cls(**data)


class MemoryStore:
    """SQLite-backed persistent memory store."""
    
    def __init__(self, db_path: str = "data/agent_memory.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL,
                    agent_role TEXT,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    entry_type TEXT NOT NULL,
                    importance REAL DEFAULT 1.0,
                    created_at REAL NOT NULL,
                    expires_at REAL,
                    metadata TEXT,
                    embedding TEXT,
                    UNIQUE(project_id, key)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_project 
                ON memory(project_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_type 
                ON memory(entry_type)
            """)
    
    def store(
        self,
        project_id: str,
        entry: MemoryEntry,
        agent_role: Optional[str] = None
    ) -> None:
        """Store a memory entry."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO memory 
                (project_id, agent_role, key, value, entry_type, importance, 
                 created_at, expires_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project_id,
                agent_role,
                entry.key,
                json.dumps(entry.value) if not isinstance(entry.value, str) else entry.value,
                entry.entry_type,
                entry.importance,
                entry.created_at,
                entry.expires_at,
                json.dumps(entry.metadata),
            ))
    
    def retrieve(
        self,
        project_id: str,
        key: Optional[str] = None,
        entry_type: Optional[str] = None,
        limit: int = 100,
        min_importance: float = 0.0
    ) -> List[MemoryEntry]:
        """Retrieve memory entries."""
        query = "SELECT * FROM memory WHERE project_id = ?"
        params: List[Any] = [project_id]
        
        if key:
            query += " AND key = ?"
            params.append(key)
        
        if entry_type:
            query += " AND entry_type = ?"
            params.append(entry_type)
        
        query += " AND importance >= ?"
        params.append(min_importance)
        
        query += " AND (expires_at IS NULL OR expires_at > ?)"
        params.append(time.time())
        
        query += " ORDER BY importance DESC, created_at DESC LIMIT ?"
        params.append(limit)
        
        entries = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            for row in conn.execute(query, params):
                try:
                    value = json.loads(row["value"])
                except json.JSONDecodeError:
                    value = row["value"]
                
                entries.append(MemoryEntry(
                    key=row["key"],
                    value=value,
                    entry_type=row["entry_type"],
                    importance=row["importance"],
                    created_at=row["created_at"],
                    expires_at=row["expires_at"],
                    metadata=json.loads(row["metadata"] or "{}"),
                ))
        
        return entries
    
    def search(
        self,
        project_id: str,
        query: str,
        limit: int = 10
    ) -> List[MemoryEntry]:
        """Search memory entries by text matching.
        
        In a production system, this would use vector embeddings.
        For now, we use simple text matching.
        """
        # Simple keyword search
        keywords = query.lower().split()
        
        entries = self.retrieve(project_id, limit=1000)
        scored = []
        
        for entry in entries:
            score = 0
            text = str(entry.value).lower() + entry.key.lower()
            for keyword in keywords:
                if keyword in text:
                    score += 1
            
            if score > 0:
                scored.append((score * entry.importance, entry))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored[:limit]]
    
    def clear_project(self, project_id: str) -> int:
        """Clear all memory for a project. Returns count deleted."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM memory WHERE project_id = ?",
                (project_id,)
            )
            return cursor.rowcount
    
    def cleanup_expired(self) -> int:
        """Remove expired entries. Returns count deleted."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM memory WHERE expires_at IS NOT NULL AND expires_at < ?",
                (time.time(),)
            )
            return cursor.rowcount


class AgentMemory:
    """High-level memory interface for agents.
    
    Provides:
    - Short-term memory (current session)
    - Long-term memory (persistent across sessions)
    - Working memory (current task context)
    """
    
    def __init__(
        self,
        project_id: str,
        store: Optional[MemoryStore] = None
    ):
        self.project_id = project_id
        self.store = store or MemoryStore()
        
        # Short-term memory (current session only)
        self._short_term: Dict[str, Any] = {}
        
        # Working memory (current task)
        self._working: Dict[str, Any] = {}
    
    def remember(
        self,
        key: str,
        value: Any,
        entry_type: str = "fact",
        importance: float = 1.0,
        persist: bool = True,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """Store a memory.
        
        Args:
            key: Memory identifier
            value: Value to store
            entry_type: Type of memory (fact, decision, code, error, feedback)
            importance: 0-1 scale of importance
            persist: Whether to save to long-term storage
            ttl_seconds: Time-to-live in seconds (None = forever)
        """
        entry = MemoryEntry(
            key=key,
            value=value,
            entry_type=entry_type,
            importance=importance,
            expires_at=time.time() + ttl_seconds if ttl_seconds else None,
        )
        
        # Always store in short-term
        self._short_term[key] = entry
        
        # Optionally persist
        if persist:
            self.store.store(self.project_id, entry)
    
    def recall(
        self,
        key: Optional[str] = None,
        entry_type: Optional[str] = None,
        limit: int = 10
    ) -> List[MemoryEntry]:
        """Recall memories.
        
        Checks short-term first, then long-term storage.
        """
        # Check short-term first
        if key and key in self._short_term:
            entry = self._short_term[key]
            if not entry.is_expired():
                return [entry]
        
        # Fall back to long-term
        return self.store.retrieve(
            self.project_id,
            key=key,
            entry_type=entry_type,
            limit=limit
        )
    
    def search(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """Search memories by relevance."""
        return self.store.search(self.project_id, query, limit)
    
    def set_working(self, key: str, value: Any) -> None:
        """Set working memory (cleared after task)."""
        self._working[key] = value
    
    def get_working(self, key: str, default: Any = None) -> Any:
        """Get working memory."""
        return self._working.get(key, default)
    
    def clear_working(self) -> None:
        """Clear working memory."""
        self._working.clear()
    
    def get_context_summary(self, max_entries: int = 20) -> str:
        """Get a summary of relevant context for AI prompts."""
        entries = self.store.retrieve(
            self.project_id,
            limit=max_entries,
            min_importance=0.5
        )
        
        if not entries:
            return "No previous context available."
        
        summary_parts = []
        for entry in entries:
            if entry.entry_type == "fact":
                summary_parts.append(f"• {entry.key}: {entry.value}")
            elif entry.entry_type == "decision":
                summary_parts.append(f"• Decision: {entry.value}")
            elif entry.entry_type == "error":
                summary_parts.append(f"• Previous error: {entry.value}")
        
        return "\n".join(summary_parts[:max_entries])
    
    def remember_code(self, file_path: str, content: str, importance: float = 0.8) -> None:
        """Remember generated code."""
        self.remember(
            key=f"code:{file_path}",
            value={"path": file_path, "content": content[:5000]},  # Limit size
            entry_type="code",
            importance=importance,
        )
    
    def remember_error(self, error: str, context: str = "", importance: float = 0.9) -> None:
        """Remember an error for learning."""
        self.remember(
            key=f"error:{hashlib.md5(error.encode()).hexdigest()[:8]}",
            value={"error": error, "context": context},
            entry_type="error",
            importance=importance,
        )
    
    def remember_decision(self, decision: str, reasoning: str = "", importance: float = 0.7) -> None:
        """Remember a decision made."""
        self.remember(
            key=f"decision:{int(time.time())}",
            value={"decision": decision, "reasoning": reasoning},
            entry_type="decision",
            importance=importance,
        )
