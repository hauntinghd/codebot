"""Base Agent Framework.

Provides the foundational classes for all CodeBot agents.
Designed to be model-agnostic and support future fine-tuned models.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, TypeVar

logger = logging.getLogger("codebot.agents")


class AgentRole(str, Enum):
    """Roles that agents can take in the system."""
    PLANNER = "planner"
    CODER = "coder"
    DEBUGGER = "debugger"
    OPTIMIZER = "optimizer"
    REVIEWER = "reviewer"
    ORCHESTRATOR = "orchestrator"


@dataclass
class AgentMessage:
    """A message exchanged between agents or with the AI backend."""
    role: str  # "user", "assistant", "system", "agent"
    content: str
    agent_role: Optional[AgentRole] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "agent_role": self.agent_role.value if self.agent_role else None,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMessage":
        return cls(
            role=data["role"],
            content=data["content"],
            agent_role=AgentRole(data["agent_role"]) if data.get("agent_role") else None,
            metadata=data.get("metadata", {}),
            timestamp=data.get("timestamp", time.time()),
        )


@dataclass
class AgentContext:
    """Context passed to agents containing project state and history."""
    user_request: str
    
    # Project identifiers (optional)
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    session_id: Optional[str] = None
    
    # Project state
    files: Dict[str, str] = field(default_factory=dict)  # path -> content
    plan: Optional[str] = None
    generated_code: Dict[str, str] = field(default_factory=dict)
    test_results: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    # Conversation history
    messages: List[AgentMessage] = field(default_factory=list)
    
    # Memory from previous interactions
    memory: Dict[str, Any] = field(default_factory=dict)
    memory_context: Optional[str] = None  # Loaded memory for context
    
    # Configuration
    model: str = "gpt-4o"
    max_tokens: int = 4000
    temperature: float = 0.7
    
    def add_message(self, message: AgentMessage) -> None:
        """Add a message to the context."""
        self.messages.append(message)
    
    def get_recent_messages(self, count: int = 10) -> List[AgentMessage]:
        """Get the most recent messages."""
        return self.messages[-count:]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "session_id": self.session_id,
            "user_request": self.user_request,
            "files": self.files,
            "plan": self.plan,
            "generated_code": self.generated_code,
            "test_results": self.test_results,
            "errors": self.errors,
            "messages": [m.to_dict() for m in self.messages],
            "memory": self.memory,
            "model": self.model,
        }


@dataclass
class AgentResult:
    """Result of an agent's execution."""
    success: bool
    output: str
    artifacts: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    tokens_used: int = 0
    execution_time: float = 0.0
    next_agent: Optional[AgentRole] = None  # Suggestion for next agent
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "artifacts": self.artifacts,
            "errors": self.errors,
            "tokens_used": self.tokens_used,
            "execution_time": self.execution_time,
            "next_agent": self.next_agent.value if self.next_agent else None,
        }


class PromptCache:
    """Cache for compressed prompts to reduce token usage."""
    
    def __init__(self, max_size: int = 100):
        self._cache: Dict[str, str] = {}
        self._access_times: Dict[str, float] = {}
        self.max_size = max_size
    
    def _hash_prompt(self, prompt: str) -> str:
        """Create a hash key for the prompt."""
        return hashlib.md5(prompt.encode()).hexdigest()[:16]
    
    def get(self, prompt: str) -> Optional[str]:
        """Get cached compressed prompt."""
        key = self._hash_prompt(prompt)
        if key in self._cache:
            self._access_times[key] = time.time()
            return self._cache[key]
        return None
    
    def set(self, prompt: str, compressed: str) -> None:
        """Cache a compressed prompt."""
        if len(self._cache) >= self.max_size:
            # Evict least recently used
            oldest = min(self._access_times, key=self._access_times.get)
            del self._cache[oldest]
            del self._access_times[oldest]
        
        key = self._hash_prompt(prompt)
        self._cache[key] = compressed
        self._access_times[key] = time.time()


class Agent(ABC):
    """Base class for all CodeBot agents.
    
    Agents are specialized AI workers that collaborate to build applications.
    Each agent has a specific role and set of capabilities.
    """
    
    # Class-level prompt cache shared across agents
    _prompt_cache = PromptCache()
    
    def __init__(
        self,
        ai_client: Any,  # OpenAI-compatible client
        role: AgentRole,
        name: str,
        description: str,
        model: str = "gpt-4o",
    ):
        self.client = ai_client
        self.role = role
        self.name = name
        self.description = description
        self.model = model
        self._execution_count = 0
        self._total_tokens_used = 0
    
    @property
    def total_tokens_used(self) -> int:
        """Total tokens used by this agent across all executions."""
        return self._total_tokens_used
    
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """The system prompt that defines this agent's behavior."""
        pass
    
    @abstractmethod
    async def execute(
        self,
        context: AgentContext,
        **kwargs
    ) -> AgentResult:
        """Execute the agent's main task."""
        pass
    
    async def stream_execute(
        self,
        context: AgentContext,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream the agent's execution output."""
        result = await self.execute(context, **kwargs)
        yield result.output
    
    def compress_prompt(self, prompt: str, max_tokens: int = 2000) -> str:
        """Compress a prompt to reduce token usage.
        
        Uses caching and intelligent truncation.
        """
        # Check cache first
        cached = self._prompt_cache.get(prompt)
        if cached:
            return cached
        
        # Estimate tokens (rough: 4 chars per token)
        estimated_tokens = len(prompt) // 4
        
        if estimated_tokens <= max_tokens:
            return prompt
        
        # Compress by removing redundant whitespace and truncating
        compressed = " ".join(prompt.split())
        
        # If still too long, truncate intelligently
        if len(compressed) // 4 > max_tokens:
            # Keep first and last parts, truncate middle
            target_chars = max_tokens * 4
            keep_each = target_chars // 2 - 50
            compressed = (
                compressed[:keep_each] +
                "\n\n[... content truncated for efficiency ...]\n\n" +
                compressed[-keep_each:]
            )
        
        self._prompt_cache.set(prompt, compressed)
        return compressed
    
    async def _call_ai(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None,
    ) -> tuple[str, int]:
        """Call the AI backend and return response + tokens used."""
        start_time = time.time()
        
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or 0.7,
        }
        
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        
        if response_format:
            kwargs["response_format"] = response_format
        
        try:
            response = self.client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content or ""
            tokens = response.usage.total_tokens if response.usage else 0
            
            # Track total tokens
            self._total_tokens_used += tokens
            self._execution_count += 1
            
            logger.debug(
                f"[{self.name}] AI call: {tokens} tokens, "
                f"{time.time() - start_time:.2f}s"
            )
            
            return content, tokens
            
        except Exception as e:
            logger.error(f"[{self.name}] AI call failed: {e}")
            raise
    
    async def _call_ai_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream AI response."""
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or 0.7,
            "stream": True,
        }
        
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        
        try:
            response = self.client.chat.completions.create(**kwargs)
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"[{self.name}] AI stream failed: {e}")
            raise
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} role={self.role.value} name={self.name}>"
