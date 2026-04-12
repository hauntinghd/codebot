"""CodeBot Multi-Agent System.

A CrewAI-inspired multi-agent architecture for building production-ready applications.
This system surpasses Cursor, Claude Code, and Bolt.new through:

1. **Role-Based Collaboration**: Specialized agents with distinct responsibilities
2. **Autonomous Execution**: Agents self-correct and iterate until goals are met
3. **Persistent Memory**: Context management across sessions
4. **RAG Integration**: Codebase-aware retrieval for informed decisions

Agents:
- Planner: Architecture design, UML, project structure
- Coder: Multi-file code generation with type safety
- Debugger: Auto-testing, error detection, fix iteration
- Optimizer: Performance tuning, code quality, refactoring

The system uses GPT-4o exclusively, with prompt compression and caching
for optimal token efficiency.
"""

from .base import Agent, AgentRole, AgentMessage, AgentContext, AgentResult, PromptCache
from .memory import AgentMemory, MemoryStore, MemoryEntry
from .planner import PlannerAgent
from .coder import CoderAgent
from .debugger import DebuggerAgent
from .optimizer import OptimizerAgent
from .crew import AgentCrew, CrewStatus, CrewResult, CrewMessage, Orchestrator

__all__ = [
    # Base infrastructure
    "Agent",
    "AgentRole",
    "AgentMessage",
    "AgentContext",
    "AgentResult",
    "PromptCache",
    # Memory
    "AgentMemory",
    "MemoryStore",
    "MemoryEntry",
    # Specialized agents
    "PlannerAgent",
    "CoderAgent",
    "DebuggerAgent",
    "OptimizerAgent",
    # Crew orchestration
    "AgentCrew",
    "CrewStatus",
    "CrewResult",
    "CrewMessage",
    "Orchestrator",
]
