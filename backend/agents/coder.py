"""Coder Agent - Production-Ready Multi-File Code Generation.

The primary code generation agent that builds complete applications.
Uses iterative batch generation to create 30-100+ files for real products.

Features:
- Iterative file generation (not limited by token count)
- Component-by-component building
- Cross-file import tracking
- Type-safe code (TypeScript/Python)
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from .base import Agent, AgentRole, AgentContext, AgentResult

logger = logging.getLogger("codebot.agents")


CODER_SYSTEM_PROMPT = """You are the Coder Agent - a senior full-stack engineer building production applications.

Your code is:
- Type-safe (TypeScript strict mode, Python type hints)
- Well-documented (JSDoc/docstrings for all exports)
- Error-handled (try-catch, proper error messages, loading states)
- Modular (small functions, single responsibility, max 150 lines per file)
- Clean (no commented code, no console.logs in production code)
- Complete (NEVER use placeholders like "// ... rest of code" or "// TODO")

OUTPUT FORMAT - Use artifact tags that can be parsed:

<artifact id="project-id" title="Project Title">
  <action type="file" path="relative/path/file.ts">
[COMPLETE FILE CONTENT - NO PLACEHOLDERS]
  </action>
  <action type="command">
npm install package-name
  </action>
</artifact>

CRITICAL RULES:
1. EVERY file must be 100% COMPLETE and runnable - NO PLACEHOLDERS EVER
2. Include ALL imports at the top of each file
3. Export all components, functions, types that other files need
4. Maximum 150 lines per file - split larger files into modules
5. Use proper file extensions (.ts, .tsx, .css, .json)
6. Generate ALL files needed for a working application
"""

BATCH_GENERATION_PROMPT = """Generate the next batch of files for this application.

PROJECT: {project_title}
USER REQUEST: {user_request}

PROJECT PLAN:
{plan}

FILES ALREADY GENERATED ({existing_count} files):
{existing_files}

BATCH TO GENERATE NOW:
{batch_description}

Generate ONLY the files listed above. Each file must be:
- 100% complete with all code (NO PLACEHOLDERS)
- Properly importing from already-generated files
- Exporting anything other files will need

Output in artifact format with <action type="file" path="..."> tags."""

FILE_STRUCTURE_PROMPT = """Analyze this project and create a complete file structure.

PROJECT: {project_title}
USER REQUEST: {user_request}

PROJECT PLAN:
{plan}

Create a COMPLETE file structure for a production application.
Include ALL necessary files - this should be 25-60+ files for a real app.

Required categories:
1. Configuration (package.json, tsconfig.json, vite.config.ts, tailwind.config.js, etc.)
2. Types/Interfaces (all TypeScript types in src/types/)
3. Utilities/Helpers (src/lib/, src/utils/)
4. API/Services (src/services/, src/api/)
5. State Management (stores, contexts, hooks)
6. UI Components (src/components/ - buttons, inputs, cards, modals, etc.)
7. Layout Components (headers, footers, sidebars, navigation)
8. Page Components (src/pages/ - one per route)
9. Feature Components (feature-specific components)
10. Styles (global CSS, component styles)

Output as JSON:
{{
  "files": [
    {{"path": "package.json", "description": "Dependencies and scripts", "priority": 1, "batch": 1}},
    {{"path": "src/types/index.ts", "description": "Core type definitions", "priority": 2, "batch": 1}},
    ...
  ],
  "total_files": 45,
  "batches": 5
}}"""


class CoderAgent(Agent):
    """Coder Agent - Generates complete production applications.
    
    Uses iterative batch generation to build real products with
    30-100+ files, not limited by single API call token limits.
    
    Generation Strategy:
    1. Analyze plan and create complete file structure
    2. Generate files in batches (8-12 files per batch)
    3. Track cross-file dependencies
    4. Iterate until all files are generated
    """
    
    # Configuration
    FILES_PER_BATCH = 10
    MAX_BATCHES = 10  # Up to 100 files
    
    def __init__(self, ai_client: Any, model: str = "gpt-4o"):
        super().__init__(
            ai_client=ai_client,
            role=AgentRole.CODER,
            name="Coder",
            description="Generates complete production applications with 30-100+ files",
            model=model,
        )
    
    @property
    def system_prompt(self) -> str:
        return CODER_SYSTEM_PROMPT
    
    async def execute(
        self,
        context: AgentContext,
        plan: Optional[str] = None,
        target_files: Optional[List[str]] = None,
        language: str = "typescript",
        **kwargs
    ) -> AgentResult:
        """Generate a complete application using iterative batch generation.
        
        This method:
        1. Creates a complete file structure from the plan
        2. Generates files in batches of 10
        3. Tracks dependencies between files
        4. Continues until all files are generated
        """
        import time
        start_time = time.time()
        
        plan_to_use = plan or context.plan
        project_title = context.project_name or "Application"
        
        if not plan_to_use:
            return AgentResult(
                success=False,
                output="",
                errors=["No plan provided. Run Planner agent first."],
            )
        
        all_files: Dict[str, str] = {}  # path -> content
        all_commands: List[str] = []
        total_tokens = 0
        
        try:
            # Step 1: Generate complete file structure
            logger.info(f"[Coder] Creating file structure for: {project_title}")
            file_structure, tokens = await self._create_file_structure(
                context.user_request, plan_to_use, project_title
            )
            total_tokens += tokens
            
            if not file_structure or not file_structure.get("files"):
                # Fallback to single-batch generation
                logger.warning("[Coder] File structure failed, using single batch")
                return await self._single_batch_generate(context, plan_to_use, language, start_time)
            
            files_to_generate = file_structure["files"]
            total_files = len(files_to_generate)
            logger.info(f"[Coder] Planning to generate {total_files} files")
            
            # Step 2: Generate files in batches
            batch_num = 0
            while files_to_generate and batch_num < self.MAX_BATCHES:
                batch_num += 1
                batch = files_to_generate[:self.FILES_PER_BATCH]
                files_to_generate = files_to_generate[self.FILES_PER_BATCH:]
                
                logger.info(f"[Coder] Generating batch {batch_num}: {len(batch)} files")
                
                # Create batch description
                batch_desc = "\n".join(
                    f"- {f['path']}: {f.get('description', 'Implementation')}"
                    for f in batch
                )
                
                # Generate this batch
                batch_files, batch_commands, tokens = await self._generate_batch(
                    context.user_request,
                    plan_to_use,
                    project_title,
                    all_files,
                    batch_desc
                )
                
                total_tokens += tokens
                all_files.update(batch_files)
                all_commands.extend(batch_commands)
                
                logger.info(f"[Coder] Batch {batch_num} complete: {len(batch_files)} files generated")
            
            # Step 3: Ensure critical files exist
            all_files, tokens = await self._ensure_critical_files(
                all_files, context.user_request, plan_to_use, project_title
            )
            total_tokens += tokens
            
            # Prepare artifacts
            artifacts = {
                "files": [
                    {"path": path, "content": content, "size": len(content)}
                    for path, content in all_files.items()
                ],
                "commands": all_commands,
                "file_count": len(all_files),
                "batches_used": batch_num,
            }
            
            logger.info(f"[Coder] Complete: {len(all_files)} files, {total_tokens} tokens")
            
            return AgentResult(
                success=len(all_files) > 0,
                output=f"Generated {len(all_files)} files for {project_title}",
                artifacts=artifacts,
                tokens_used=total_tokens,
                execution_time=time.time() - start_time,
                next_agent=AgentRole.DEBUGGER,
            )
            
        except Exception as e:
            logger.error(f"[Coder] Generation failed: {e}", exc_info=True)
            return AgentResult(
                success=False,
                output="",
                errors=[str(e)],
                execution_time=time.time() - start_time,
            )
    
    async def _create_file_structure(
        self,
        user_request: str,
        plan: str,
        project_title: str
    ) -> Tuple[Dict[str, Any], int]:
        """Create a complete file structure from the plan."""
        prompt = FILE_STRUCTURE_PROMPT.format(
            project_title=project_title,
            user_request=user_request,
            plan=self.compress_prompt(plan, max_tokens=3000)
        )
        
        messages = [
            {"role": "system", "content": "You are an expert software architect. Output only valid JSON."},
            {"role": "user", "content": prompt},
        ]
        
        try:
            response, tokens = await self._call_ai(
                messages,
                temperature=0.3,
                max_tokens=4000,
            )
            
            # Parse JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                structure = json.loads(json_match.group())
                return structure, tokens
            
            return {}, tokens
            
        except Exception as e:
            logger.error(f"[Coder] File structure creation failed: {e}")
            return {}, 0
    
    async def _generate_batch(
        self,
        user_request: str,
        plan: str,
        project_title: str,
        existing_files: Dict[str, str],
        batch_description: str
    ) -> Tuple[Dict[str, str], List[str], int]:
        """Generate a batch of files."""
        # Create summary of existing files
        existing_summary = ""
        if existing_files:
            existing_summary = "\n".join(
                f"- {path} ({len(content)} chars)"
                for path, content in existing_files.items()
            )
        else:
            existing_summary = "(No files generated yet)"
        
        prompt = BATCH_GENERATION_PROMPT.format(
            project_title=project_title,
            user_request=user_request,
            plan=self.compress_prompt(plan, max_tokens=2000),
            existing_count=len(existing_files),
            existing_files=existing_summary,
            batch_description=batch_description
        )
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]
        
        try:
            response, tokens = await self._call_ai(
                messages,
                temperature=0.3,
                max_tokens=16000,  # Large batch needs more tokens
            )
            
            # Parse files and commands from response
            files = self._extract_files(response)
            commands = self._extract_commands(response)
            
            return files, commands, tokens
            
        except Exception as e:
            logger.error(f"[Coder] Batch generation failed: {e}")
            return {}, [], 0
    
    async def _ensure_critical_files(
        self,
        files: Dict[str, str],
        user_request: str,
        plan: str,
        project_title: str
    ) -> Tuple[Dict[str, str], int]:
        """Ensure critical files like package.json and index.html exist."""
        critical_files = [
            "package.json",
            "index.html",
            "vite.config.ts",
            "tsconfig.json",
            "tailwind.config.js",
            "src/main.tsx",
            "src/App.tsx",
        ]
        
        missing = [f for f in critical_files if f not in files and not any(f.endswith(p.split("/")[-1]) for p in files)]
        
        if not missing:
            return files, 0
        
        logger.info(f"[Coder] Generating missing critical files: {missing}")
        
        prompt = f"""Generate these CRITICAL missing files for the project:

PROJECT: {project_title}
FILES NEEDED: {', '.join(missing)}

EXISTING FILES: {', '.join(files.keys())}

Generate complete, production-ready versions of the missing files.
Output in artifact format with <action type="file" path="..."> tags."""
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]
        
        try:
            response, tokens = await self._call_ai(
                messages,
                temperature=0.2,
                max_tokens=8000,
            )
            
            new_files = self._extract_files(response)
            files.update(new_files)
            
            return files, tokens
            
        except Exception as e:
            logger.error(f"[Coder] Critical files generation failed: {e}")
            return files, 0
    
    async def _single_batch_generate(
        self,
        context: AgentContext,
        plan: str,
        language: str,
        start_time: float
    ) -> AgentResult:
        """Fallback single-batch generation for simpler projects."""
        import time
        
        prompt = f"""Generate a COMPLETE production application.

USER REQUEST: {context.user_request}

PROJECT PLAN:
{plan}

REQUIREMENTS:
- Generate ALL files needed for a working application
- Minimum 20 files for a real application
- Include: package.json, configs, types, components, pages, utils, styles
- Use {language} with full type safety
- Every file must be COMPLETE (no placeholders)

Output in artifact format with <action type="file" path="..."> tags."""
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]
        
        try:
            response, tokens = await self._call_ai(
                messages,
                temperature=0.3,
                max_tokens=16000,
            )
            
            files = self._extract_files(response)
            commands = self._extract_commands(response)
            
            artifacts = {
                "files": [
                    {"path": path, "content": content, "size": len(content)}
                    for path, content in files.items()
                ],
                "commands": commands,
                "file_count": len(files),
            }
            
            return AgentResult(
                success=len(files) > 0,
                output=response,
                artifacts=artifacts,
                tokens_used=tokens,
                execution_time=time.time() - start_time,
                next_agent=AgentRole.DEBUGGER,
            )
            
        except Exception as e:
            return AgentResult(
                success=False,
                output="",
                errors=[str(e)],
                execution_time=time.time() - start_time,
            )
    
    def _extract_files(self, response: str) -> Dict[str, str]:
        """Extract files from the AI response."""
        files = {}
        
        # Pattern for <action type="file" path="...">content</action>
        pattern = r'<action\s+type="file"\s+path="([^"]+)"[^>]*>\n?(.*?)</action>'
        for match in re.finditer(pattern, response, re.DOTALL):
            path = match.group(1).strip()
            content = match.group(2).strip()
            if path and content:
                files[path] = content
        
        # Also try alternative format: ```filename\ncontent```
        alt_pattern = r'```(\S+)\s*\n(.*?)```'
        for match in re.finditer(alt_pattern, response, re.DOTALL):
            filename = match.group(1).strip()
            content = match.group(2).strip()
            # Only use if it looks like a file path
            if '.' in filename and '/' not in filename[:3] and filename not in files:
                files[filename] = content
        
        return files
    
    def _extract_commands(self, response: str) -> List[str]:
        """Extract commands from the AI response."""
        commands = []
        
        pattern = r'<action\s+type="command"[^>]*>\n?(.*?)</action>'
        for match in re.finditer(pattern, response, re.DOTALL):
            cmd = match.group(1).strip()
            if cmd:
                commands.append(cmd)
        
        return commands
    
    async def generate_single_file(
        self,
        context: AgentContext,
        file_path: str,
        file_purpose: str,
        dependencies: List[str] = None
    ) -> AgentResult:
        """Generate a single file with specific requirements."""
        import time
        start_time = time.time()
        
        deps = ", ".join(dependencies) if dependencies else "standard libraries"
        
        prompt = f"""Generate a single production-ready file:

FILE: {file_path}
PURPOSE: {file_purpose}
DEPENDENCIES: {deps}

PROJECT CONTEXT:
{context.user_request}

Output ONLY the complete file content in an artifact tag.
The code must be complete and runnable with NO PLACEHOLDERS."""
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]
        
        try:
            response, tokens = await self._call_ai(
                messages,
                temperature=0.2,
                max_tokens=4000,
            )
            
            files = self._extract_files(response)
            content = files.get(file_path, response)
            
            # Clean markdown if present
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            
            return AgentResult(
                success=True,
                output=content,
                artifacts={
                    "file_path": file_path,
                    "content": content,
                },
                tokens_used=tokens,
                execution_time=time.time() - start_time,
            )
            
        except Exception as e:
            return AgentResult(
                success=False,
                output="",
                errors=[str(e)],
            )
    
    async def fix_file(
        self,
        context: AgentContext,
        file_path: str,
        current_content: str,
        errors: List[str]
    ) -> AgentResult:
        """Fix errors in a specific file."""
        import time
        start_time = time.time()
        
        prompt = f"""Fix the errors in this file:

FILE: {file_path}

CURRENT CONTENT:
{current_content}

ERRORS:
{chr(10).join(f"- {e}" for e in errors)}

Output the COMPLETE fixed file in an artifact tag. No explanations, just the fixed code."""
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]
        
        try:
            response, tokens = await self._call_ai(
                messages,
                temperature=0.2,
                max_tokens=4000,
            )
            
            files = self._extract_files(response)
            fixed_content = files.get(file_path) or list(files.values())[0] if files else response
            
            return AgentResult(
                success=True,
                output=fixed_content,
                artifacts={
                    "file_path": file_path,
                    "fixed_content": fixed_content,
                    "errors_fixed": errors,
                },
                tokens_used=tokens,
                execution_time=time.time() - start_time,
            )
            
        except Exception as e:
            return AgentResult(
                success=False,
                output="",
                errors=[str(e)],
            )
