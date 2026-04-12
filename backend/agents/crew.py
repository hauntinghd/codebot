"""Agent Crew - CrewAI-inspired orchestration.

Coordinates multiple agents working together on a task:
- Planner → Coder → Debugger → Optimizer
- Role-based delegation
- Context passing between agents
- Autonomous iteration until completion
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime

from .base import Agent, AgentRole, AgentContext, AgentResult
from .memory import AgentMemory, MemoryStore
from .planner import PlannerAgent
from .coder import CoderAgent
from .debugger import DebuggerAgent
from .optimizer import OptimizerAgent

logger = logging.getLogger("codebot.agents")


class CrewStatus(str, Enum):
    """Status of the crew execution."""
    IDLE = "idle"
    PLANNING = "planning"
    CODING = "coding"
    DEBUGGING = "debugging"
    OPTIMIZING = "optimizing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CrewMessage:
    """Message passed between agents in the crew."""
    from_agent: AgentRole
    to_agent: AgentRole
    content: str
    artifacts: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "from": self.from_agent.value,
            "to": self.to_agent.value,
            "content": self.content,
            "artifacts": self.artifacts,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class CrewResult:
    """Result from the crew execution."""
    success: bool
    status: CrewStatus
    plan: Optional[str] = None
    generated_code: Dict[str, str] = field(default_factory=dict)
    debug_report: Optional[str] = None
    optimization_report: Optional[str] = None
    messages: List[CrewMessage] = field(default_factory=list)
    total_tokens: int = 0
    execution_time: float = 0.0
    iterations: int = 0
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "status": self.status.value,
            "plan": self.plan,
            "generated_code": self.generated_code,
            "debug_report": self.debug_report,
            "optimization_report": self.optimization_report,
            "messages": [m.to_dict() for m in self.messages],
            "total_tokens": self.total_tokens,
            "execution_time": self.execution_time,
            "iterations": self.iterations,
            "errors": self.errors,
        }


class AgentCrew:
    """CrewAI-inspired agent orchestration.
    
    Coordinates multiple agents to complete a complex task:
    1. Planner creates the project plan with UML
    2. Coder generates the code files
    3. Debugger finds and fixes bugs
    4. Optimizer improves code quality
    
    Features:
    - Autonomous iteration until success
    - Context passing between agents
    - Persistent memory across sessions
    - Streaming progress updates
    """
    
    MAX_ITERATIONS = 5
    
    def __init__(
        self,
        ai_client: Any,
        model: str = "gpt-4o",
        memory_store: Optional[MemoryStore] = None,
        on_progress: Optional[Callable[[CrewStatus, str], None]] = None
    ):
        self.ai_client = ai_client
        self.model = model
        self.memory = AgentMemory(memory_store) if memory_store else None
        self.on_progress = on_progress
        
        # Initialize agents
        self.planner = PlannerAgent(ai_client, model)
        self.coder = CoderAgent(ai_client, model)
        self.debugger = DebuggerAgent(ai_client, model)
        self.optimizer = OptimizerAgent(ai_client, model)
        
        # Execution state
        self.status = CrewStatus.IDLE
        self.messages: List[CrewMessage] = []
        self.current_context: Optional[AgentContext] = None
    
    def _emit_progress(self, status: CrewStatus, message: str):
        """Emit progress update."""
        self.status = status
        if self.on_progress:
            try:
                self.on_progress(status, message)
            except Exception as e:
                logger.error(f"Progress callback failed: {e}")
    
    def _add_message(
        self,
        from_agent: AgentRole,
        to_agent: AgentRole,
        content: str,
        artifacts: Dict[str, Any] = None
    ):
        """Add a message to the crew conversation."""
        msg = CrewMessage(
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
            artifacts=artifacts or {},
        )
        self.messages.append(msg)
        return msg
    
    async def execute(
        self,
        user_request: str,
        session_id: str = None,
        skip_planning: bool = False,
        existing_plan: str = None,
        skip_optimization: bool = False,
        max_iterations: int = None,
    ) -> CrewResult:
        """Execute the full agent pipeline.
        
        Args:
            user_request: What the user wants to build
            session_id: Optional session ID for memory persistence
            skip_planning: Skip planning if plan is provided
            existing_plan: Existing plan to use
            skip_optimization: Skip the optimization phase
            max_iterations: Override max debug iterations
        """
        import time
        start_time = time.time()
        
        max_iter = max_iterations or self.MAX_ITERATIONS
        self.messages = []
        total_tokens = 0
        iterations = 0
        
        # Initialize context
        context = AgentContext(
            user_request=user_request,
            session_id=session_id,
        )
        self.current_context = context
        
        # Load memory context if available
        if self.memory and session_id:
            memory_context = self.memory.get_context(session_id)
            if memory_context:
                context.memory_context = memory_context
                logger.info(f"Loaded memory context for session {session_id}")
        
        try:
            # === PHASE 1: PLANNING ===
            if not skip_planning and not existing_plan:
                self._emit_progress(CrewStatus.PLANNING, "Creating project plan...")
                
                plan_result = await self.planner.execute(
                    context,
                    depth="standard"
                )
                
                total_tokens += plan_result.tokens_used
                
                if not plan_result.success:
                    return CrewResult(
                        success=False,
                        status=CrewStatus.FAILED,
                        errors=plan_result.errors or ["Planning failed"],
                        total_tokens=total_tokens,
                        execution_time=time.time() - start_time,
                    )
                
                context.plan = plan_result.output
                
                self._add_message(
                    AgentRole.PLANNER,
                    AgentRole.CODER,
                    "Plan created successfully",
                    {"plan": plan_result.output, "diagrams": plan_result.artifacts}
                )
                
                # Save to memory
                if self.memory and session_id:
                    self.memory.remember_decision(
                        session_id,
                        "project_plan",
                        plan_result.output[:500]
                    )
            else:
                context.plan = existing_plan
            
            # === PHASE 2: CODING ===
            self._emit_progress(CrewStatus.CODING, "Generating code...")
            
            code_result = await self.coder.execute(context)
            total_tokens += code_result.tokens_used
            
            if not code_result.success:
                return CrewResult(
                    success=False,
                    status=CrewStatus.FAILED,
                    plan=context.plan,
                    errors=code_result.errors or ["Code generation failed"],
                    total_tokens=total_tokens,
                    execution_time=time.time() - start_time,
                )
            
            # Extract generated files
            generated_files = {}
            if code_result.artifacts and "files" in code_result.artifacts:
                for file_info in code_result.artifacts["files"]:
                    generated_files[file_info["path"]] = file_info["content"]
            
            context.generated_code = generated_files
            
            self._add_message(
                AgentRole.CODER,
                AgentRole.DEBUGGER,
                f"Generated {len(generated_files)} files",
                {"files": list(generated_files.keys())}
            )
            
            # === PHASE 3: DEBUGGING (Autonomous Loop) ===
            self._emit_progress(CrewStatus.DEBUGGING, "Checking for bugs...")
            
            debug_report = ""
            
            for iteration in range(max_iter):
                iterations += 1
                
                debug_result = await self.debugger.execute(
                    context,
                    code_files=generated_files,
                    auto_fix=True
                )
                
                total_tokens += debug_result.tokens_used
                
                if debug_result.artifacts:
                    issues = debug_result.artifacts.get("issues", [])
                    fixes = debug_result.artifacts.get("fixes", {})
                    
                    # Apply fixes
                    if fixes:
                        generated_files.update(fixes)
                        context.generated_code = generated_files
                        
                        self._add_message(
                            AgentRole.DEBUGGER,
                            AgentRole.DEBUGGER,
                            f"Iteration {iteration + 1}: Fixed {len(fixes)} files",
                            {"fixes": list(fixes.keys())}
                        )
                        
                        # Save errors to memory for future avoidance
                        if self.memory and session_id:
                            for issue in issues[:3]:
                                self.memory.remember_error(
                                    session_id,
                                    issue.get("description", "Unknown error"),
                                    issue.get("fix", "")
                                )
                    
                    # Check if all issues are resolved
                    if not issues or len(issues) == 0:
                        debug_report = debug_result.output
                        break
                    
                    # Update context with remaining errors
                    context.errors = [i.get("description", "") for i in issues]
                
                debug_report = debug_result.output
            
            self._add_message(
                AgentRole.DEBUGGER,
                AgentRole.OPTIMIZER,
                f"Debugging complete after {iterations} iterations",
                {"iterations": iterations}
            )
            
            # === PHASE 4: OPTIMIZATION (Optional) ===
            optimization_report = ""
            
            if not skip_optimization:
                self._emit_progress(CrewStatus.OPTIMIZING, "Optimizing code...")
                
                opt_result = await self.optimizer.execute(
                    context,
                    code_files=generated_files,
                    optimization_focus="all"
                )
                
                total_tokens += opt_result.tokens_used
                
                if opt_result.artifacts and "optimized_files" in opt_result.artifacts:
                    optimized = opt_result.artifacts["optimized_files"]
                    if optimized:
                        generated_files.update(optimized)
                        
                        self._add_message(
                            AgentRole.OPTIMIZER,
                            AgentRole.PLANNER,
                            f"Optimized {len(optimized)} files",
                            {"optimized": list(optimized.keys())}
                        )
                
                optimization_report = opt_result.output
            
            # === COMPLETION ===
            self._emit_progress(CrewStatus.COMPLETED, "Project complete!")
            
            # Save successful code patterns to memory
            if self.memory and session_id:
                for path, content in list(generated_files.items())[:3]:
                    self.memory.remember_code(
                        session_id,
                        path,
                        content[:1000]
                    )
            
            return CrewResult(
                success=True,
                status=CrewStatus.COMPLETED,
                plan=context.plan,
                generated_code=generated_files,
                debug_report=debug_report,
                optimization_report=optimization_report,
                messages=self.messages,
                total_tokens=total_tokens,
                execution_time=time.time() - start_time,
                iterations=iterations,
            )
            
        except Exception as e:
            logger.exception(f"Crew execution failed: {e}")
            return CrewResult(
                success=False,
                status=CrewStatus.FAILED,
                plan=context.plan if context else None,
                generated_code=generated_files if 'generated_files' in locals() else {},
                messages=self.messages,
                total_tokens=total_tokens,
                execution_time=time.time() - start_time,
                iterations=iterations,
                errors=[str(e)],
            )
    
    async def execute_single_agent(
        self,
        agent_role: AgentRole,
        context: AgentContext,
        **kwargs
    ) -> AgentResult:
        """Execute a single agent."""
        agent_map = {
            AgentRole.PLANNER: self.planner,
            AgentRole.CODER: self.coder,
            AgentRole.DEBUGGER: self.debugger,
            AgentRole.OPTIMIZER: self.optimizer,
        }
        
        agent = agent_map.get(agent_role)
        if not agent:
            return AgentResult(
                success=False,
                output="",
                errors=[f"Unknown agent role: {agent_role}"],
            )
        
        return await agent.execute(context, **kwargs)
    
    async def refine(
        self,
        user_feedback: str,
        session_id: str = None
    ) -> CrewResult:
        """Refine the current project based on user feedback."""
        if not self.current_context:
            return CrewResult(
                success=False,
                status=CrewStatus.FAILED,
                errors=["No current context. Run execute() first."],
            )
        
        # Update context with feedback
        self.current_context.user_request = f"""
Original Request: {self.current_context.user_request}

User Feedback/Refinement:
{user_feedback}
"""
        
        # Re-run from coding with updated context
        return await self.execute(
            user_request=self.current_context.user_request,
            session_id=session_id,
            skip_planning=True,
            existing_plan=self.current_context.plan,
        )
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get current status of all agents."""
        return {
            "crew_status": self.status.value,
            "agents": {
                "planner": {
                    "name": self.planner.name,
                    "tokens_used": self.planner.total_tokens_used,
                },
                "coder": {
                    "name": self.coder.name,
                    "tokens_used": self.coder.total_tokens_used,
                },
                "debugger": {
                    "name": self.debugger.name,
                    "tokens_used": self.debugger.total_tokens_used,
                },
                "optimizer": {
                    "name": self.optimizer.name,
                    "tokens_used": self.optimizer.total_tokens_used,
                },
            },
            "total_messages": len(self.messages),
        }


class Orchestrator:
    """High-level orchestrator for the multi-agent system.
    
    Provides a simplified interface for common operations:
    - build_project: Full project generation
    - refine_project: Iterative refinement
    - debug_code: Debug existing code
    - optimize_code: Optimize existing code
    """
    
    def __init__(
        self,
        ai_client: Any,
        model: str = "gpt-4o",
        db_path: str = None
    ):
        self.ai_client = ai_client
        self.model = model
        
        # Initialize memory store
        self.memory_store = MemoryStore(db_path) if db_path else None
        
        # Crew instances by session
        self._crews: Dict[str, AgentCrew] = {}
    
    def get_crew(
        self,
        session_id: str,
        on_progress: Callable[[CrewStatus, str], None] = None
    ) -> AgentCrew:
        """Get or create a crew for a session."""
        if session_id not in self._crews:
            self._crews[session_id] = AgentCrew(
                ai_client=self.ai_client,
                model=self.model,
                memory_store=self.memory_store,
                on_progress=on_progress,
            )
        return self._crews[session_id]
    
    async def build_project(
        self,
        user_request: str,
        session_id: str = None,
        on_progress: Callable[[CrewStatus, str], None] = None,
        **options
    ) -> CrewResult:
        """Build a complete project from a user request."""
        import uuid
        session_id = session_id or str(uuid.uuid4())
        
        crew = self.get_crew(session_id, on_progress)
        return await crew.execute(
            user_request=user_request,
            session_id=session_id,
            **options
        )
    
    async def refine_project(
        self,
        session_id: str,
        feedback: str
    ) -> CrewResult:
        """Refine an existing project based on feedback."""
        if session_id not in self._crews:
            return CrewResult(
                success=False,
                status=CrewStatus.FAILED,
                errors=["Session not found. Start with build_project() first."],
            )
        
        crew = self._crews[session_id]
        return await crew.refine(feedback, session_id)
    
    async def debug_code(
        self,
        code_files: Dict[str, str],
        errors: List[str] = None,
        auto_fix: bool = True
    ) -> AgentResult:
        """Debug code files."""
        debugger = DebuggerAgent(self.ai_client, self.model)
        
        context = AgentContext(
            user_request="Debug the provided code",
            generated_code=code_files,
            errors=errors,
        )
        
        return await debugger.execute(context, auto_fix=auto_fix)
    
    async def optimize_code(
        self,
        code_files: Dict[str, str],
        focus: str = "all"
    ) -> AgentResult:
        """Optimize code files."""
        optimizer = OptimizerAgent(self.ai_client, self.model)
        
        context = AgentContext(
            user_request="Optimize the provided code",
            generated_code=code_files,
        )
        
        return await optimizer.execute(context, optimization_focus=focus)
    
    def cleanup_session(self, session_id: str):
        """Clean up a session's resources."""
        if session_id in self._crews:
            del self._crews[session_id]
