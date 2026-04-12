"""Enhanced Architecture Pipeline with Multi-Agent System.

Upgrades the existing pipeline to use the CrewAI-inspired multi-agent framework:
- PlannerAgent: Creates UML diagrams and architecture plans
- CoderAgent: Generates production-ready multi-file code  
- DebuggerAgent: Finds and fixes bugs autonomously
- OptimizerAgent: Refactors for performance and quality

This module provides both:
1. Full crew execution (autonomous multi-agent pipeline)
2. Streaming-compatible generator for the frontend
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

from backend.agents import (
    AgentCrew,
    AgentContext,
    AgentRole,
    CrewStatus,
    CrewResult,
    Orchestrator,
    PlannerAgent,
    CoderAgent,
    DebuggerAgent,
    OptimizerAgent,
    MemoryStore,
    AgentMemory,
)
from .artifact_parser import ArtifactParser, ParseResult
from .codebot_prompt import (
    get_system_prompt,
    get_planning_prompt,
    get_build_prompt,
    get_validation_prompt,
    get_correction_prompt,
)

logger = logging.getLogger("codebot.pipeline")


@dataclass
class PipelineEvent:
    """Event emitted during pipeline execution."""
    type: str  # agent_start, agent_complete, file_created, progress, complete, error
    agent: Optional[str] = None  # planner, coder, debugger, optimizer
    data: Dict[str, Any] = field(default_factory=dict)
    message: str = ""
    progress: int = 0


@dataclass 
class EnhancedPipelineConfig:
    """Configuration for the enhanced multi-agent pipeline."""
    model: str = "gpt-4o"
    max_debug_iterations: int = 3
    enable_planning: bool = True
    enable_optimization: bool = True
    streaming: bool = True
    project_dir: Optional[str] = None
    memory_db_path: Optional[str] = None  # Path for persistent memory


class EnhancedPipeline:
    """Enhanced Architecture Pipeline with Multi-Agent System.
    
    Uses the CrewAI-inspired agent framework for:
    1. Planner Agent: Architecture design with UML/Mermaid
    2. Coder Agent: Multi-file code generation with type safety
    3. Debugger Agent: Autonomous bug detection and fixing
    4. Optimizer Agent: Performance and quality improvements
    
    Features:
    - Autonomous iteration until code passes validation
    - Persistent memory across sessions
    - Streaming events for real-time UI updates
    - Token tracking and optimization
    """
    
    PROGRESS_MAP = {
        "planning": (0, 20),
        "coding": (20, 60),
        "debugging": (60, 85),
        "optimizing": (85, 95),
        "executing": (95, 100),
    }
    
    def __init__(
        self,
        ai_client: Any,
        config: Optional[EnhancedPipelineConfig] = None
    ):
        self.client = ai_client
        self.config = config or EnhancedPipelineConfig()
        
        # Initialize memory store if path provided
        memory_store = None
        if self.config.memory_db_path:
            memory_store = MemoryStore(self.config.memory_db_path)
        
        # Initialize agents
        self.planner = PlannerAgent(ai_client, self.config.model)
        self.coder = CoderAgent(ai_client, self.config.model)
        self.debugger = DebuggerAgent(ai_client, self.config.model)
        self.optimizer = OptimizerAgent(ai_client, self.config.model)
        
        # Initialize crew for full orchestration
        self.crew = AgentCrew(
            ai_client=ai_client,
            model=self.config.model,
            memory_store=memory_store,
        )
        
        # Artifact parser for legacy compatibility
        self.parser = ArtifactParser()
        
        # State tracking
        self.current_stage = "idle"
        self.total_tokens = 0
        self.generated_files: Dict[str, str] = {}
        self.commands: List[str] = []
    
    async def execute(
        self,
        user_request: str,
        project_id: str,
        project_title: str,
    ) -> AsyncGenerator[PipelineEvent, None]:
        """Execute the multi-agent pipeline with streaming events.
        
        This is the main entry point for the architecture build flow.
        It coordinates all agents and yields events for the UI.
        """
        import time
        start_time = time.time()
        session_id = project_id
        
        try:
            # === PLANNING PHASE ===
            if self.config.enable_planning:
                yield PipelineEvent(
                    type="agent_start",
                    agent="planner",
                    message="🧠 Analyzing requirements and creating architecture plan...",
                    progress=5,
                )
                
                context = AgentContext(
                    user_request=user_request,
                    session_id=session_id,
                )
                
                plan_result = await self.planner.execute(
                    context,
                    depth="standard",
                    project_title=project_title,
                )
                
                self.total_tokens += plan_result.tokens_used
                
                if not plan_result.success:
                    yield PipelineEvent(
                        type="error",
                        agent="planner",
                        message=f"❌ Planning failed: {plan_result.errors}",
                        progress=10,
                    )
                    return
                
                context.plan = plan_result.output
                
                # Extract UML diagrams if present
                diagrams = plan_result.artifacts.get("diagrams", []) if plan_result.artifacts else []
                
                yield PipelineEvent(
                    type="agent_complete",
                    agent="planner",
                    message="✅ Architecture plan created",
                    progress=20,
                    data={
                        "plan": plan_result.output[:2000],  # Truncate for UI
                        "diagrams": diagrams,
                        "tokens": plan_result.tokens_used,
                    },
                )
            else:
                context = AgentContext(
                    user_request=user_request,
                    session_id=session_id,
                    plan=f"Build: {project_title}\n\n{user_request}"
                )
            
            # === CODING PHASE ===
            yield PipelineEvent(
                type="agent_start",
                agent="coder",
                message="💻 Analyzing project structure and preparing code generation...",
                progress=25,
            )
            
            code_result = await self.coder.execute(context)
            self.total_tokens += code_result.tokens_used
            
            if not code_result.success:
                yield PipelineEvent(
                    type="error",
                    agent="coder",
                    message=f"❌ Code generation failed: {code_result.errors}",
                    progress=30,
                )
                return
            
            # Extract files from artifacts
            if code_result.artifacts and "files" in code_result.artifacts:
                total_files = len(code_result.artifacts["files"])
                batches_used = code_result.artifacts.get("batches_used", 1)
                
                yield PipelineEvent(
                    type="progress",
                    agent="coder",
                    message=f"📦 Generated {total_files} files in {batches_used} batches",
                    progress=50,
                    data={"total_files": total_files, "batches": batches_used},
                )
                
                for idx, file_info in enumerate(code_result.artifacts["files"]):
                    self.generated_files[file_info["path"]] = file_info["content"]
                    # Only emit events for first 10 and last 5 files to avoid spam
                    if idx < 10 or idx >= total_files - 5:
                        yield PipelineEvent(
                            type="file_created",
                            agent="coder",
                            message=f"📄 {file_info['path']}",
                            progress=self._calc_progress("coding", idx + 1, total_files),
                            data={"path": file_info["path"], "size": file_info.get("size", 0)},
                        )
                    elif idx == 10:
                        yield PipelineEvent(
                            type="progress",
                            agent="coder",
                            message=f"📄 ... generating {total_files - 15} more files ...",
                            progress=self._calc_progress("coding", idx + 1, total_files),
                        )
                
                # Extract commands
                self.commands = code_result.artifacts.get("commands", [])
            
            context.generated_code = self.generated_files
            
            yield PipelineEvent(
                type="agent_complete",
                agent="coder",
                message=f"✅ Generated {len(self.generated_files)} files",
                progress=60,
                data={
                    "file_count": len(self.generated_files),
                    "files": list(self.generated_files.keys()),
                    "tokens": code_result.tokens_used,
                },
            )
            
            # === DEBUGGING PHASE ===
            yield PipelineEvent(
                type="agent_start",
                agent="debugger",
                message="🔍 Analyzing code for bugs and issues...",
                progress=62,
            )
            
            debug_iterations = 0
            for i in range(self.config.max_debug_iterations):
                debug_iterations += 1
                
                debug_result = await self.debugger.execute(
                    context,
                    code_files=self.generated_files,
                    auto_fix=True,
                )
                
                self.total_tokens += debug_result.tokens_used
                
                if debug_result.artifacts:
                    issues = debug_result.artifacts.get("issues", [])
                    fixes = debug_result.artifacts.get("fixes", {})
                    
                    if issues:
                        yield PipelineEvent(
                            type="progress",
                            agent="debugger",
                            message=f"⚠️ Found {len(issues)} issues, applying fixes...",
                            progress=self._calc_progress("debugging", i + 1, self.config.max_debug_iterations),
                            data={"issues": len(issues), "iteration": i + 1},
                        )
                    
                    # Apply fixes
                    if fixes:
                        self.generated_files.update(fixes)
                        context.generated_code = self.generated_files
                        
                        for path in fixes:
                            yield PipelineEvent(
                                type="file_updated",
                                agent="debugger",
                                message=f"🔧 Fixed: {path}",
                                progress=self._calc_progress("debugging", i + 1, self.config.max_debug_iterations),
                                data={"path": path},
                            )
                    
                    # If no issues, we're done debugging
                    if not issues:
                        break
                    
                    context.errors = [issue.get("description", "") for issue in issues]
            
            yield PipelineEvent(
                type="agent_complete",
                agent="debugger",
                message=f"✅ Debugging complete ({debug_iterations} iterations)",
                progress=85,
                data={
                    "iterations": debug_iterations,
                    "tokens": debug_result.tokens_used if debug_result else 0,
                },
            )
            
            # === OPTIMIZATION PHASE (Optional) ===
            if self.config.enable_optimization:
                yield PipelineEvent(
                    type="agent_start",
                    agent="optimizer",
                    message="⚡ Optimizing code for performance and quality...",
                    progress=87,
                )
                
                opt_result = await self.optimizer.execute(
                    context,
                    code_files=self.generated_files,
                    optimization_focus="all",
                )
                
                self.total_tokens += opt_result.tokens_used
                
                if opt_result.artifacts and "optimized_files" in opt_result.artifacts:
                    optimized = opt_result.artifacts["optimized_files"]
                    if optimized:
                        self.generated_files.update(optimized)
                        
                        for path in optimized:
                            yield PipelineEvent(
                                type="file_updated",
                                agent="optimizer",
                                message=f"⚡ Optimized: {path}",
                                progress=92,
                                data={"path": path},
                            )
                
                yield PipelineEvent(
                    type="agent_complete",
                    agent="optimizer",
                    message="✅ Optimization complete",
                    progress=95,
                    data={
                        "findings": len(opt_result.artifacts.get("findings", [])) if opt_result.artifacts else 0,
                        "optimized": len(opt_result.artifacts.get("optimized_files", {})) if opt_result.artifacts else 0,
                        "tokens": opt_result.tokens_used,
                    },
                )
            
            # === EXECUTION PHASE ===
            yield PipelineEvent(
                type="agent_start",
                agent="executor",
                message="📁 Writing files to project...",
                progress=96,
            )
            
            # Write files
            files_written = await self._write_files(project_id)
            
            yield PipelineEvent(
                type="agent_complete",
                agent="executor",
                message=f"✅ Wrote {len(files_written)} files",
                progress=98,
                data={"files": files_written},
            )
            
            # Log commands (don't execute automatically for safety)
            if self.commands:
                yield PipelineEvent(
                    type="commands_ready",
                    message="📋 Commands ready to run",
                    progress=99,
                    data={"commands": self.commands},
                )
            
            # === COMPLETE ===
            execution_time = time.time() - start_time
            
            yield PipelineEvent(
                type="complete",
                message="🎉 Project built successfully!",
                progress=100,
                data={
                    "files": list(self.generated_files.keys()),
                    "file_count": len(self.generated_files),
                    "commands": self.commands,
                    "total_tokens": self.total_tokens,
                    "execution_time": execution_time,
                    "debug_iterations": debug_iterations,
                },
            )
            
        except Exception as e:
            logger.exception(f"Enhanced pipeline error: {e}")
            yield PipelineEvent(
                type="error",
                message=f"❌ Pipeline failed: {str(e)}",
                progress=self._current_progress(),
                data={"error": str(e)},
            )
    
    async def _write_files(self, project_id: str) -> List[str]:
        """Write generated files to the project directory."""
        base_dir = self.config.project_dir or f"data/projects/{project_id}/frontend"
        os.makedirs(base_dir, exist_ok=True)
        
        files_written = []
        
        for rel_path, content in self.generated_files.items():
            # Ensure relative path doesn't escape
            safe_path = rel_path.lstrip("/").lstrip("\\")
            if ".." in safe_path:
                logger.warning(f"Skipping unsafe path: {rel_path}")
                continue
            
            full_path = os.path.join(base_dir, safe_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            try:
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)
                files_written.append(safe_path)
                logger.debug(f"Wrote file: {full_path}")
            except Exception as e:
                logger.error(f"Failed to write {full_path}: {e}")
        
        return files_written
    
    def _calc_progress(self, stage: str, current: int, total: int) -> int:
        """Calculate progress within a stage."""
        if stage not in self.PROGRESS_MAP:
            return 50
        
        start, end = self.PROGRESS_MAP[stage]
        range_size = end - start
        
        if total <= 0:
            return start
        
        progress_in_stage = (current / total) * range_size
        return int(start + progress_in_stage)
    
    def _current_progress(self) -> int:
        """Get current progress based on stage."""
        stage_progress = {
            "idle": 0,
            "planning": 10,
            "coding": 40,
            "debugging": 70,
            "optimizing": 90,
            "executing": 95,
            "complete": 100,
        }
        return stage_progress.get(self.current_stage, 50)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current pipeline status."""
        return {
            "stage": self.current_stage,
            "total_tokens": self.total_tokens,
            "files_count": len(self.generated_files),
            "agents": {
                "planner": self.planner.total_tokens_used,
                "coder": self.coder.total_tokens_used,
                "debugger": self.debugger.total_tokens_used,
                "optimizer": self.optimizer.total_tokens_used,
            },
        }


async def run_enhanced_build(
    ai_client: Any,
    user_request: str,
    project_id: str,
    project_title: str,
    config: Optional[EnhancedPipelineConfig] = None,
) -> AsyncGenerator[PipelineEvent, None]:
    """Convenience function to run the enhanced pipeline.
    
    Example:
        async for event in run_enhanced_build(client, "Build a todo app", "proj-123", "Todo App"):
            print(f"{event.progress}% - {event.message}")
    """
    pipeline = EnhancedPipeline(ai_client, config)
    async for event in pipeline.execute(user_request, project_id, project_title):
        yield event
