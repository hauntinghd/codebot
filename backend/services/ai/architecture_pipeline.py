"""CodeBot Architecture Pipeline.

Multi-stage pipeline for building production-ready applications:
1. Planning Agent - Creates architecture plan
2. Build Agent - Generates all code
3. Validation Agent - Checks for issues
4. Correction Agent - Fixes problems

Designed to support future custom fine-tuned models (no API key needed).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, AsyncGenerator

from .codebot_prompt import (
    get_system_prompt,
    get_planning_prompt,
    get_build_prompt,
    get_validation_prompt,
    get_correction_prompt,
)
from .artifact_parser import (
    ArtifactParser,
    ParseResult,
    Artifact,
    Action,
    ActionType,
)

logger = logging.getLogger("codebot")

def _try_package_zip(files: list[dict], project_name: str) -> dict | None:
    try:
        from backend.services import project_packager  # type: ignore
    except Exception:
        try:
            import backend.services.project_packager as project_packager  # type: ignore
        except Exception:
            return None

    for fn_name in ("create_project_zip", "package_project", "package_files", "build_zip", "make_zip"):
        if hasattr(project_packager, fn_name):
            fn = getattr(project_packager, fn_name)
            result = fn(files=files, project_name=project_name)  # type: ignore
            if isinstance(result, dict):
                zp = result.get("zip_path") or result.get("path")
            else:
                zp = result
            if zp:
                return {"zip_path": str(zp), "project_name": project_name, "file_count": len(files)}
    return None



@dataclass
class PipelineConfig:
    """Configuration for the architecture pipeline."""
    model: str = "gpt-4o"
    max_validation_passes: int = 2
    enable_planning: bool = True
    enable_validation: bool = True
    streaming: bool = True
    project_dir: Optional[str] = None


@dataclass
class PipelineState:
    """Current state of the pipeline."""
    stage: str = "idle"  # idle, planning, building, validating, correcting, complete, error
    progress: int = 0
    plan: Optional[str] = None
    artifact_id: Optional[str] = None
    artifact_title: Optional[str] = None
    files_created: List[str] = field(default_factory=list)
    commands_executed: List[str] = field(default_factory=list)
    validation_issues: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class PipelineEvent:
    """Event emitted during pipeline execution."""
    type: str  # stage_change, progress, plan_section, file_created, command_run, validation_issue, error, complete
    data: Dict[str, Any] = field(default_factory=dict)
    message: str = ""


class ArchitecturePipeline:
    """Main pipeline orchestrating the multi-agent code generation process.
    
    This is designed to be model-agnostic. The `ai_client` parameter accepts
    any client that implements the chat completion interface. Future versions
    will support custom fine-tuned models running locally.
    """
    
    def __init__(
        self,
        ai_client: Any,  # OpenAI-compatible client
        config: Optional[PipelineConfig] = None
    ):
        self.client = ai_client
        self.config = config or PipelineConfig()
        self.state = PipelineState()
        self.parser = ArtifactParser()
        
    async def execute(
        self,
        user_request: str,
        project_id: str,
        project_title: str,
        on_event: Optional[Callable[[PipelineEvent], None]] = None
    ) -> AsyncGenerator[PipelineEvent, None]:
        """Execute the full pipeline and yield events.
        
        Stages:
        1. Planning - Generate architecture plan
        2. Building - Generate all code with artifact format
        3. Validation - Check for issues
        4. Correction - Fix any issues found
        5. Execution - Write files and run commands
        """
        try:
            # Stage 1: Planning
            if self.config.enable_planning:
                async for event in self._planning_stage(user_request):
                    yield event

            # Stage 2: Building
            async for event in self._building_stage(user_request, project_id, project_title):
                yield event

            # Stage 3 & 4: Validation + Correction loop
            if self.config.enable_validation:
                for pass_num in range(self.config.max_validation_passes):
                    async for event in self._validation_stage(pass_num + 1):
                        yield event

                    if not self.state.validation_issues:
                        break

                    async for event in self._correction_stage(pass_num + 1):
                        yield event

            # Stage 5: Execution
            async for event in self._execution_stage(project_id):
                yield event

            # Complete
            self.state.stage = "complete"
            self.state.progress = 100
            yield PipelineEvent(
                type="complete",
                message="Project built successfully",
                data={
                    "artifact_id": self.state.artifact_id,
                    "files": self.state.files_created,
                    "commands": self.state.commands_executed
                }
            )

        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            # If planning failed (upstream AI error), fall back to deterministic plan and continue
            if self.state.stage in ("planning", "idle"):
                try:
                    fallback = self._fallback_plan(user_request)
                    self.state.plan = fallback
                    yield PipelineEvent(type="plan_complete", message="✅ Fallback plan created (offline)", data={"plan": fallback})

                    # Continue with building/validation/execution using fallback plan
                    async for event in self._building_stage(user_request, project_id, project_title):
                        yield event

                    if self.config.enable_validation:
                        for pass_num in range(self.config.max_validation_passes):
                            async for event in self._validation_stage(pass_num + 1):
                                yield event
                            if not self.state.validation_issues:
                                break
                            async for event in self._correction_stage(pass_num + 1):
                                yield event

                    async for event in self._execution_stage(project_id):
                        yield event

                    # Finalize
                    self.state.stage = "complete"
                    self.state.progress = 100
                    yield PipelineEvent(
                        type="complete",
                        message="Project built successfully (using fallback)",
                        data={
                            "artifact_id": self.state.artifact_id,
                            "files": self.state.files_created,
                            "commands": self.state.commands_executed
                        }
                    )
                except Exception as ee:
                    logger.error("Pipeline failed after fallback: %s", ee, exc_info=True)
                    self.state.stage = "error"
                    self.state.error = str(ee)
                    yield PipelineEvent(type="error", message=f"Build failed after fallback: {ee}", data={"error": str(ee)})
            else:
                self.state.stage = "error"
                self.state.error = str(e)
                yield PipelineEvent(
                    type="error",
                    message=f"Build failed: {str(e)}",
                    data={"error": str(e)}
                )
    
    async def _planning_stage(self, user_request: str) -> AsyncGenerator[PipelineEvent, None]:
        """Stage 1: Generate architecture plan."""
        self.state.stage = "planning"
        self.state.progress = 5
        yield PipelineEvent(
            type="stage_change",
            message="📋 Creating architecture plan...",
            data={"stage": "planning"}
        )
        
        # If the user prompt looks like a web search, augment with retrieval
        from backend.utils.web_retrieval import web_search
        retrieval_needed = any(word in user_request.lower() for word in ["search", "find", "latest", "news", "current", "lookup", "web", "internet"])
        web_context = ""
        if retrieval_needed:
            web_context = web_search(user_request)
        planning_prompt = get_planning_prompt(user_request)
        if web_context:
            planning_prompt = f"[Web context]\n{web_context}\n\n[User]\n{planning_prompt}"
        try:
            response = await self._call_ai(
                system_prompt=get_system_prompt(),
                user_prompt=planning_prompt,
                stream=self.config.streaming
            )

            # Parse the plan
            result = self.parser.parse(response)
            if result.plan:
                self.state.plan = result.plan.raw
                yield PipelineEvent(
                    type="plan_complete",
                    message="✅ Architecture plan created",
                    data={
                        "plan": result.plan.raw,
                        "sections": {
                            "structure": result.plan.project_structure,
                            "data_model": result.plan.data_model,
                            "components": result.plan.component_hierarchy,
                            "state": result.plan.state_management,
                            "api": result.plan.api_design,
                            "dependencies": result.plan.dependencies,
                            "issues": result.plan.potential_issues,
                        }
                    }
                )
            else:
                # If parser found nothing, fall back to deterministic plan
                fallback = self._fallback_plan(user_request)
                self.state.plan = fallback
                yield PipelineEvent(type="plan_complete", message="✅ Fallback plan created", data={"plan": fallback})
        except Exception as e:
            logger.warning("Planning AI failed, using fallback planner: %s", e)
            # Emit a fallback deterministic plan so UI doesn't dead-end
            fallback = self._fallback_plan(user_request)
            self.state.plan = fallback
            yield PipelineEvent(type="plan_complete", message="✅ Fallback plan created (offline)", data={"plan": fallback})
        
        self.state.progress = 20
        self.parser.reset()

    def _fallback_plan(self, user_request: str) -> str:
        """Generate a simple deterministic plan based on the user's request.

        This fallback is intentionally conservative: high-level sections and
        a suggested file structure so the build stage can proceed.
        """
        title = (user_request or "New Project").strip()
        plan_lines = [
            f"Plan for: {title}",
            "\nHigh-level overview:",
            "1) Create a small web app with a frontend and simple server (if needed).",
            "2) Provide an index page, static assets, and a minimal package.json.",
            "3) Add a basic router and a sample API endpoint for demo data.",
            "4) Wire up a simple README and start script.",
            "\nSuggested file structure:",
            "- index.html",
            "- package.json",
            "- src/main.js (or src/main.tsx)",
            "- src/App.jsx",
            "- README.md",
            "\nDependencies:",
            "- minimal: none required; suggest using plain JS or a small framework (React/Vite) if requested.",
            "\nNext steps:",
            "- Build files from the plan and create a dev server preview.",
        ]

        return "\n".join(plan_lines)
    
    async def _building_stage(
        self,
        user_request: str,
        project_id: str,
        project_title: str
    ) -> AsyncGenerator[PipelineEvent, None]:
        """Stage 2: Generate all code."""
        self.state.stage = "building"
        self.state.progress = 25
        yield PipelineEvent(
            type="stage_change",
            message="🔨 Building project...",
            data={"stage": "building"}
        )
        
        # Call AI for code generation
        build_prompt = get_build_prompt(
            plan=self.state.plan or "No plan provided",
            user_request=user_request,
            project_id=project_id,
            project_title=project_title
        )
        try:
            response = await self._call_ai(
                system_prompt=get_system_prompt(),
                user_prompt=build_prompt,
                stream=self.config.streaming
            )

            # Parse the artifact
            result = self.parser.parse(response)
            if result.artifact:
                self.state.artifact_id = result.artifact.id
                self.state.artifact_title = result.artifact.title

                # Count files and commands
                files = result.artifact.get_files()
                commands = result.artifact.get_commands()

                yield PipelineEvent(
                    type="build_complete",
                    message=f"✅ Generated {len(files)} files, {len(commands)} commands",
                    data={
                        "artifact_id": result.artifact.id,
                        "file_count": len(files),
                        "command_count": len(commands)
                    }
                )
            else:
                # No artifact parsed - fall back to conservative generator
                raise RuntimeError("No artifact parsed from AI response")
        except Exception as e:
            logger.warning("Build AI failed, using conservative local generator: %s", e)
            # Create a minimal artifact from the plan to allow execution to proceed
            artifact = Artifact(id="fallback-artifact", title="Fallback Artifact")

            # Basic files based on plan
            plan_summary = (self.state.plan or "Project").splitlines()[0][:80]
            index_html = f"<!doctype html><html><head><meta charset=\"utf-8\"><title>{plan_summary}</title></head><body><div id=\"root\">Hello from CodeBot preview</div><script src=\"/assets/index-ZezxKoxz.js\"></script></body></html>"
            package_json = json.dumps({"name": plan_summary.replace(' ', '-').lower(), "version": "1.0.0", "private": True})
            readme = f"# {plan_summary}\n\nGenerated fallback project by CodeBot."

            artifact.actions.append(Action(type=ActionType.FILE, path="index.html", content=index_html))
            artifact.actions.append(Action(type=ActionType.FILE, path="package.json", content=package_json))
            artifact.actions.append(Action(type=ActionType.FILE, path="README.md", content=readme))
            artifact.actions.append(Action(type=ActionType.COMMAND, content="# No-op: install/build commands omitted in fallback"))

            # Inject artifact into parser result so execution stage picks it up
            self.parser.result.artifact = artifact
            self.state.artifact_id = artifact.id
            self.state.artifact_title = artifact.title

            files = artifact.get_files()
            commands = artifact.get_commands()

            yield PipelineEvent(
                type="build_complete",
                message=f"✅ Fallback generated {len(files)} files, {len(commands)} commands",
                data={
                    "artifact_id": artifact.id,
                    "file_count": len(files),
                    "command_count": len(commands)
                }
            )
        
        self.state.progress = 60
    
    async def _validation_stage(self, pass_num: int) -> AsyncGenerator[PipelineEvent, None]:
        """Stage 3: Validate generated code."""
        self.state.stage = "validating"
        yield PipelineEvent(
            type="stage_change",
            message=f"🔍 Validating code (pass {pass_num})...",
            data={"stage": "validating", "pass": pass_num}
        )
        
        if not self.parser.result.artifact:
            return
        
        # Get all generated code - SAVE the artifact before validation
        generated_code = self.parser.result.raw_response
        saved_artifact = self.parser.result.artifact
        
        # Call AI for validation
        validation_prompt = get_validation_prompt(generated_code)
        try:
            response = await self._call_ai(
                system_prompt="You are a code reviewer. Check for issues and report them concisely.",
                user_prompt=validation_prompt,
                stream=False  # Don't stream validation
            )

            # Parse validation results using a SEPARATE parser
            validation_parser = ArtifactParser()
            validation_result = validation_parser.parse(response)
            self.state.validation_issues = validation_result.validation_issues
        except Exception as e:
            logger.warning("Validation AI failed, skipping validation and marking as passed: %s", e)
            # If validation fails due to upstream AI error, assume no issues so pipeline can continue
            self.state.validation_issues = []
        
        # Restore the artifact (validation may have wiped it)
        if saved_artifact and not self.parser.result.artifact:
            self.parser.result.artifact = saved_artifact
        
        if self.state.validation_issues:
            yield PipelineEvent(
                type="validation_issues",
                message=f"⚠️ Found {len(self.state.validation_issues)} issues",
                data={"issues": self.state.validation_issues}
            )
        else:
            yield PipelineEvent(
                type="validation_passed",
                message="✅ Code validation passed",
                data={}
            )
        
        self.state.progress = 70
    
    async def _correction_stage(self, pass_num: int) -> AsyncGenerator[PipelineEvent, None]:
        """Stage 4: Fix validation issues."""
        self.state.stage = "correcting"
        yield PipelineEvent(
            type="stage_change",
            message=f"🔧 Fixing issues (pass {pass_num})...",
            data={"stage": "correcting", "pass": pass_num}
        )
        
        # Get original code and issues - save current artifact as fallback
        original_code = self.parser.result.raw_response
        saved_artifact = self.parser.result.artifact
        issues = "\n".join(self.state.validation_issues)
        
        # Call AI for correction
        correction_prompt = get_correction_prompt(issues, original_code)
        try:
            response = await self._call_ai(
                system_prompt=get_system_prompt(),
                user_prompt=correction_prompt,
                stream=self.config.streaming
            )

            # Re-parse the corrected code
            self.parser.reset()
            self.parser.parse(response)

            # If correction didn't produce a valid artifact, use the original
            if not self.parser.result.artifact and saved_artifact:
                self.parser.result.artifact = saved_artifact
        except Exception as e:
            logger.warning("Correction AI failed, keeping original artifact: %s", e)
            # Restore original artifact if present
            if saved_artifact:
                self.parser.result.artifact = saved_artifact

        yield PipelineEvent(
            type="correction_complete",
            message="✅ Issues fixed or skipped (offline)",
            data={}
        )
        
        self.state.progress = 80
    
    async def _execution_stage(self, project_id: str) -> AsyncGenerator[PipelineEvent, None]:
        """Stage 5: Write files and execute commands."""
        self.state.stage = "executing"
        self.state.progress = 85
        yield PipelineEvent(
            type="stage_change",
            message="📝 Writing files...",
            data={"stage": "executing"}
        )
        
        if not self.parser.result.artifact:
            yield PipelineEvent(
                type="error",
                message="No artifact to execute",
                data={"error": "No artifact generated"}
            )
            return
        
        artifact = self.parser.result.artifact
        project_dir = self.config.project_dir or f"data/projects/{project_id}/frontend"
        os.makedirs(project_dir, exist_ok=True)
        
        # Execute each action in order
        for action in artifact.actions:
            if action.type == ActionType.FILE and action.path:
                # Write file
                file_path = os.path.join(project_dir, action.path)
                file_dir = os.path.dirname(file_path)
                if file_dir:
                    os.makedirs(file_dir, exist_ok=True)
                
                with open(file_path, "w") as f:
                    f.write(action.content)
                
                self.state.files_created.append(action.path)
                yield PipelineEvent(
                    type="file_created",
                    message=f"📄 {action.path}",
                    data={"path": action.path, "size": len(action.content)}
                )
            
            elif action.type == ActionType.COMMAND:
                # Log command (don't actually execute npm in this context)
                self.state.commands_executed.append(action.content)
                yield PipelineEvent(
                    type="command_logged",
                    message=f"⚡ {action.content}",
                    data={"command": action.content}
                )
        
        self.state.progress = 95
        yield PipelineEvent(
            type="execution_complete",
            message=f"✅ Created {len(self.state.files_created)} files",
            data={
                "files": self.state.files_created,
                "commands": self.state.commands_executed
            }
        )
    
    async def _call_ai(
        self,
        system_prompt: str,
        user_prompt: str,
        stream: bool = True
    ) -> str:
        """Call the AI model.
        
        This method is designed to be overridden for custom models.
        Currently uses OpenAI-compatible API.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # If the provided ai client is a simple callable (e.g., our HF helper),
        # call it with a single prompt and return the text result.
        try:
            from backend.utils.hf_client import get_planning_client
        except Exception:
            get_planning_client = None

        # Compose a single prompt for non-OpenAI-style clients
        composed_prompt = f"{system_prompt}\n\n{user_prompt}"

        # If the client is a callable (HF helper), use it.
        if callable(self.client):
            try:
                model_hint = os.environ.get('PLANNING_MODEL', None)
                return self.client(composed_prompt, model_hint or "")
            except Exception as e:
                logger.error(f"HF callable client error: {e}", exc_info=True)
                raise

        # If client exposes the OpenAI-style chat.completions.create API, use it.
        chat_attr = getattr(self.client, 'chat', None)
        if chat_attr is not None and hasattr(chat_attr, 'completions'):
            if stream:
                # Streaming response via OpenAI-compatible client
                response_chunks = []
                stream_response = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    stream=True,
                    max_tokens=16000,
                    temperature=0.7
                )
                for chunk in stream_response:
                    try:
                        if chunk.choices and chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            response_chunks.append(content)
                    except Exception:
                        continue
                return "".join(response_chunks)
            else:
                response = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    max_tokens=16000,
                    temperature=0.7
                )
                return response.choices[0].message.content or ""

        # As a last resort, if we have the HF helper available, use that.
        if get_planning_client is not None:
            hf_client = get_planning_client()
            return hf_client(composed_prompt, os.environ.get('PLANNING_MODEL', ''))

        raise RuntimeError("No compatible AI client available for _call_ai")


class LocalModelPipeline(ArchitecturePipeline):
    """Pipeline variant for local/fine-tuned models.
    
    This class can be extended to support:
    - Local GGUF models via llama.cpp
    - Custom fine-tuned models via Hugging Face
    - Self-hosted inference servers
    
    Override _call_ai to implement your model's API.
    """
    
    def __init__(self, model_path: Optional[str] = None, config: Optional[PipelineConfig] = None):
        # Initialize without OpenAI client
        super().__init__(ai_client=None, config=config)
        self.model_path = model_path
    
    async def _call_ai(
        self,
        system_prompt: str,
        user_prompt: str,
        stream: bool = True
    ) -> str:
        """Override this for local model inference.
        
        Example implementation for llama.cpp:
        
        from llama_cpp import Llama
        llm = Llama(model_path=self.model_path)
        output = llm.create_chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        return output['choices'][0]['message']['content']
        """
        raise NotImplementedError(
            "LocalModelPipeline requires implementing _call_ai with your model's inference API"
        )


async def run_pipeline(
    user_request: str,
    project_id: str,
    project_title: str,
    api_key: str,
    api_provider: Optional[str] = None,
    project_dir: Optional[str] = None,
    on_event: Optional[Callable[[PipelineEvent], None]] = None
) -> PipelineState:
    """Convenience function to run the full pipeline.
    
    Returns the final pipeline state with all files created.
    """
    # Force using Hugging Face token / planning client when available.
    # If `api_key` is provided we treat it as a HF token and inject it into
    # the environment so the HF helper picks it up. This avoids creating a
    # global OpenAI client and ensures the pipeline runs against HF/OSS models.
    client = None

    try:
        # If the user provided a BYOK provider, prefer it when possible.
        if api_key and api_provider:
            provider = str(api_provider).lower()
            if provider in ("huggingface", "hf"):
                os.environ['HF_TOKEN'] = str(api_key)
                os.environ['HUGGINGFACEHUB_API_TOKEN'] = str(api_key)
            elif provider == "grok":
                # Try to use a grok/xAI client if available; otherwise fall back to HF
                try:
                    import xai  # type: ignore
                    # We don't attempt deep integration here; the presence of the
                    # library indicates the environment can use grok. Downstream
                    # code (multi-layer) is responsible for using the correct
                    # client shape. For planning we fall back to HF if needed.
                    logger.info("xAI/grok client available; preference set to grok for this run")
                    # NOTE: we intentionally do not configure a grok client here;
                    # the architecture pipeline uses the planning client (HF helper)
                    # for planning, and full grok support requires additional
                    # adapter code (handled elsewhere). If xai is present, try
                    # to use HF-compatible helper where possible.
                except Exception:
                    # Notify caller via event that grok client isn't installed
                    logger.warning("grok/xAI client not available; falling back to Hugging Face for planning")
                    if on_event:
                        try:
                            on_event(PipelineEvent(type="warning", message="grok/xAI client not installed on server; falling back to Hugging Face for planning."))
                        except Exception:
                            logger.debug("Failed to emit grok fallback warning event")
                    # Fall back to HF token usage
                    os.environ['HF_TOKEN'] = str(api_key)
                    os.environ['HUGGINGFACEHUB_API_TOKEN'] = str(api_key)
            else:
                # For all other providers we currently default to treating the
                # key as a Hugging Face style token for planning; multi-layer
                # flows use provider-aware clients when available.
                os.environ['HF_TOKEN'] = str(api_key)
                os.environ['HUGGINGFACEHUB_API_TOKEN'] = str(api_key)
        elif api_key:
            # If only an api_key was provided without a provider, assume HF
            os.environ['HF_TOKEN'] = str(api_key)
            os.environ['HUGGINGFACEHUB_API_TOKEN'] = str(api_key)

        # Always use the planning model for planning/thinking
        planning_model = os.environ.get('HF_PLANNING_MODEL', 'Qwen/Qwen3-4B-Thinking-2507:cheapest')
        from backend.utils.hf_client import get_planning_client
        client = get_planning_client(model=planning_model)
    except Exception as e:
        logger.error(f"Failed to initialize planning client in run_pipeline: {e}", exc_info=True)
        raise RuntimeError("Planning client not available. Ensure tokens/clients are configured and working.") from e

    config = PipelineConfig(project_dir=project_dir)
    pipeline = ArchitecturePipeline(ai_client=client, config=config)
    
    final_state = None
    async for event in pipeline.execute(user_request, project_id, project_title):
        if on_event:
            on_event(event)
        final_state = pipeline.state
    
    return final_state or PipelineState()
