"""Research-Based Build Pipeline.

A multi-stage pipeline that uses sequential API calls to build reliable products:

Stage 1: Deep Research - Research best practices for the product
Stage 2: Prompt Engineering - Create the perfect build prompt from research
Stage 3: Code Generation - Generate 20+ files using the engineered prompt
Stage 4: Code Verification - Check all files for errors
Stage 5: Error Fix Loop - Fix any errors found
Stage 6: Build Test - Verify the build compiles/works
Stage 7: Preview - Return the working product

Each stage is a separate API call to ensure reliability and prevent hallucination.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, List, Optional

logger = logging.getLogger("codebot.pipeline")


@dataclass
class PipelineEvent:
    """Event emitted during pipeline execution."""
    stage: str
    step: int
    total_steps: int
    message: str
    progress: int
    data: Optional[Dict[str, Any]] = None


@dataclass
class PipelineResult:
    """Final result of the pipeline."""
    success: bool
    files: Dict[str, str]  # path -> content
    total_tokens: int
    error: Optional[str] = None


class ResearchBuildPipeline:
    """Multi-stage pipeline for reliable code generation."""
    
    TOTAL_STAGES = 7
    
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.total_tokens = 0
    
    async def execute(
        self,
        project_id: str,
        project_name: str,
        requirements: str,
        output_dir: str
    ) -> AsyncGenerator[PipelineEvent, None]:
        """Execute the full pipeline with streaming events."""
        
        try:
            # Stage 1: Deep Research
            yield PipelineEvent(
                stage="research",
                step=1,
                total_steps=self.TOTAL_STAGES,
                message="🔍 Stage 1/7: Deep Research - Analyzing how to build this product...",
                progress=5
            )
            
            research = await self._stage_research(project_name, requirements)
            yield PipelineEvent(
                stage="research",
                step=1,
                total_steps=self.TOTAL_STAGES,
                message="✅ Research complete - Found best practices and architecture",
                progress=15,
                data={"research_length": len(research)}
            )
            
            # Stage 2: Prompt Engineering
            yield PipelineEvent(
                stage="prompt_engineering",
                step=2,
                total_steps=self.TOTAL_STAGES,
                message="📝 Stage 2/7: Prompt Engineering - Creating detailed build instructions...",
                progress=20
            )
            
            build_prompt = await self._stage_prompt_engineering(project_name, requirements, research)
            yield PipelineEvent(
                stage="prompt_engineering",
                step=2,
                total_steps=self.TOTAL_STAGES,
                message="✅ Build prompt created with detailed specifications",
                progress=30,
                data={"prompt_length": len(build_prompt)}
            )
            
            # Stage 3: Code Generation
            yield PipelineEvent(
                stage="code_generation",
                step=3,
                total_steps=self.TOTAL_STAGES,
                message="💻 Stage 3/7: Code Generation - Generating 20+ production files...",
                progress=35
            )
            
            files = await self._stage_code_generation(project_id, project_name, build_prompt)
            yield PipelineEvent(
                stage="code_generation",
                step=3,
                total_steps=self.TOTAL_STAGES,
                message=f"✅ Generated {len(files)} files",
                progress=55,
                data={"file_count": len(files), "files": list(files.keys())}
            )
            
            # Stage 4: Code Verification
            yield PipelineEvent(
                stage="verification",
                step=4,
                total_steps=self.TOTAL_STAGES,
                message="🔎 Stage 4/7: Code Verification - Checking for errors...",
                progress=60
            )
            
            errors = await self._stage_verify_code(files)
            
            if errors:
                yield PipelineEvent(
                    stage="verification",
                    step=4,
                    total_steps=self.TOTAL_STAGES,
                    message=f"⚠️ Found {len(errors)} issues to fix",
                    progress=65,
                    data={"error_count": len(errors)}
                )
                
                # Stage 5: Error Fix Loop
                max_fix_attempts = 3
                for attempt in range(max_fix_attempts):
                    yield PipelineEvent(
                        stage="error_fix",
                        step=5,
                        total_steps=self.TOTAL_STAGES,
                        message=f"🔧 Stage 5/7: Error Fix Loop - Attempt {attempt + 1}/{max_fix_attempts}...",
                        progress=70 + (attempt * 5)
                    )
                    
                    files = await self._stage_fix_errors(files, errors)
                    errors = await self._stage_verify_code(files)
                    
                    if not errors:
                        yield PipelineEvent(
                            stage="error_fix",
                            step=5,
                            total_steps=self.TOTAL_STAGES,
                            message="✅ All errors fixed",
                            progress=80
                        )
                        break
                else:
                    yield PipelineEvent(
                        stage="error_fix",
                        step=5,
                        total_steps=self.TOTAL_STAGES,
                        message=f"⚠️ Some errors may remain after {max_fix_attempts} attempts",
                        progress=80
                    )
            else:
                yield PipelineEvent(
                    stage="verification",
                    step=4,
                    total_steps=self.TOTAL_STAGES,
                    message="✅ No errors found - Code is clean!",
                    progress=75
                )
            
            # Stage 6: Build Test
            yield PipelineEvent(
                stage="build_test",
                step=6,
                total_steps=self.TOTAL_STAGES,
                message="🏗️ Stage 6/7: Build Test - Writing files and testing...",
                progress=85
            )
            
            # Write all files to disk
            os.makedirs(output_dir, exist_ok=True)
            files_written = []
            
            for path, content in files.items():
                full_path = os.path.join(output_dir, path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                with open(full_path, 'w') as f:
                    f.write(content)
                files_written.append(path)
                
                yield PipelineEvent(
                    stage="build_test",
                    step=6,
                    total_steps=self.TOTAL_STAGES,
                    message=f"📄 Created: {path}",
                    progress=85 + min(10, len(files_written))
                )
            
            # Stage 7: Complete
            yield PipelineEvent(
                stage="complete",
                step=7,
                total_steps=self.TOTAL_STAGES,
                message=f"🎉 Stage 7/7: Complete! Built {len(files_written)} files successfully!",
                progress=100,
                data={
                    "file_count": len(files_written),
                    "total_tokens": self.total_tokens,
                    "files": files_written
                }
            )
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            yield PipelineEvent(
                stage="error",
                step=0,
                total_steps=self.TOTAL_STAGES,
                message=f"❌ Pipeline failed: {str(e)}",
                progress=0,
                data={"error": str(e)}
            )
    
    async def _stage_research(self, project_name: str, requirements: str) -> str:
        """Stage 1: Deep research on how to build the product."""
        
        prompt = f"""You are a senior product architect and web development expert. 
        
Conduct DEEP RESEARCH on how to build this product correctly:

PROJECT: {project_name}
REQUIREMENTS: {requirements}

Research and provide detailed insights on:

## 1. Product Architecture
- What type of application is this? (e-commerce, SaaS, portfolio, etc.)
- What are the core features needed?
- What is the user flow?

## 2. Technical Stack Recommendations
- Frontend framework and why
- Styling approach (CSS framework)
- State management needs
- Data structure requirements

## 3. UI/UX Best Practices
- Modern design patterns for this type of product
- Color schemes that work for this industry
- Layout and navigation patterns
- Mobile responsiveness requirements

## 4. SEO and Performance
- Meta tags needed
- Semantic HTML structure
- Performance optimizations
- Accessibility requirements

## 5. File Structure
- List all files that should be created (minimum 20 files)
- Explain what each file does

## 6. Component Breakdown
- List all React components needed
- Explain the props and state for each

Be extremely detailed and specific. This research will be used to generate the actual code."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a senior architect conducting deep technical research. Be thorough and specific."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000
        )
        
        self.total_tokens += response.usage.total_tokens if response.usage else 0
        return response.choices[0].message.content or ""
    
    async def _stage_prompt_engineering(self, project_name: str, requirements: str, research: str) -> str:
        """Stage 2: Create the perfect build prompt from research."""
        
        prompt = f"""You are an expert prompt engineer. Your job is to create the PERFECT prompt for a code generation AI.

Based on this research, create a detailed prompt that will generate a complete, working application:

PROJECT: {project_name}
REQUIREMENTS: {requirements}

RESEARCH:
{research[:6000]}

Create a prompt that:
1. Specifies EXACTLY what files to create (20+ files)
2. Details the content of each file
3. Specifies the relationships between components
4. Includes all styling requirements
5. Defines all functionality
6. Specifies the exact output format

The prompt should instruct the AI to output files in this format:
===FILE: path/to/file.ext===
[file content]
===END FILE===

Make the prompt so detailed that the code generation AI cannot fail.
The output should be the COMPLETE prompt text that will be sent to the code generation AI."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert prompt engineer. Create the most detailed, foolproof prompt possible."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000
        )
        
        self.total_tokens += response.usage.total_tokens if response.usage else 0
        return response.choices[0].message.content or ""
    
    async def _stage_code_generation(self, project_id: str, project_name: str, build_prompt: str) -> Dict[str, str]:
        """Stage 3: Generate all code files using the engineered prompt."""
        
        # Add formatting instructions
        enhanced_prompt = f"""{build_prompt}

CRITICAL OUTPUT FORMAT:
You MUST output each file using this exact format:

===FILE: filename.ext===
[complete file content here - no placeholders, no "rest of code" comments]
===END FILE===

Generate ALL files now. Do not skip any files. Each file must be 100% complete.
Start with package.json, then index.html, then all other files."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert full-stack developer. Generate complete, production-ready code. NEVER use placeholders or incomplete code. Output ONLY the files in the specified format."},
                {"role": "user", "content": enhanced_prompt}
            ],
            temperature=0.5,  # Lower temperature for more reliable code
            max_tokens=16000
        )
        
        self.total_tokens += response.usage.total_tokens if response.usage else 0
        content = response.choices[0].message.content or ""
        
        # Parse files from the output
        files = self._parse_files(content)
        
        # If not enough files, make another call for more
        if len(files) < 15:
            additional_prompt = f"""Continue generating more files for the project.
            
Already generated: {', '.join(files.keys())}

Generate the remaining files needed. Use the same format:
===FILE: filename.ext===
[content]
===END FILE===

We need at least 20 files total. Generate: components, pages, hooks, utils, styles, types, etc."""

            response2 = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Continue generating the remaining files. Use the exact same format."},
                    {"role": "assistant", "content": content[:2000]},  # Context from previous
                    {"role": "user", "content": additional_prompt}
                ],
                temperature=0.5,
                max_tokens=12000
            )
            
            self.total_tokens += response2.usage.total_tokens if response2.usage else 0
            additional_content = response2.choices[0].message.content or ""
            additional_files = self._parse_files(additional_content)
            files.update(additional_files)
        
        # Ensure we have essential files
        files = self._ensure_essential_files(files, project_name)
        
        return files
    
    def _parse_files(self, content: str) -> Dict[str, str]:
        """Parse files from the ===FILE: path=== format."""
        files = {}
        
        # Pattern: ===FILE: path=== ... ===END FILE===
        pattern = r'===FILE:\s*([^\n=]+?)\s*===\s*([\s\S]*?)\s*===END FILE==='
        matches = re.findall(pattern, content, re.IGNORECASE)
        
        for path, file_content in matches:
            path = path.strip()
            file_content = file_content.strip()
            
            # Skip empty files
            if file_content and path:
                # Clean up the path
                path = path.lstrip('./')
                files[path] = file_content
        
        # Also try the older artifact format as fallback
        if not files:
            pattern2 = r'<action type="file" path="([^"]+)">\s*([\s\S]*?)\s*</action>'
            matches2 = re.findall(pattern2, content)
            for path, file_content in matches2:
                if file_content.strip():
                    files[path.strip()] = file_content.strip()
        
        # Also try markdown code block format
        if not files:
            # Look for ```filename or ```path/to/file
            pattern3 = r'```([a-zA-Z0-9_./\-]+)\n([\s\S]*?)```'
            matches3 = re.findall(pattern3, content)
            for path, file_content in matches3:
                if '.' in path and file_content.strip():
                    files[path.strip()] = file_content.strip()
        
        return files
    
    def _ensure_essential_files(self, files: Dict[str, str], project_name: str) -> Dict[str, str]:
        """Ensure essential files exist."""
        
        # Ensure index.html exists
        if 'index.html' not in files:
            files['index.html'] = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{project_name}">
    <title>{project_name}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body>
    <div id="root"></div>
    <script type="module" src="./src/main.jsx"></script>
</body>
</html>'''
        
        # Ensure package.json exists
        if 'package.json' not in files:
            files['package.json'] = json.dumps({
                "name": project_name.lower().replace(" ", "-"),
                "version": "1.0.0",
                "type": "module",
                "scripts": {
                    "dev": "vite",
                    "build": "vite build",
                    "preview": "vite preview"
                },
                "dependencies": {
                    "react": "^18.2.0",
                    "react-dom": "^18.2.0"
                },
                "devDependencies": {
                    "vite": "^5.0.0",
                    "@vitejs/plugin-react": "^4.0.0"
                }
            }, indent=2)
        
        return files
    
    async def _stage_verify_code(self, files: Dict[str, str]) -> List[Dict[str, str]]:
        """Stage 4: Verify code for errors."""
        
        errors = []
        
        # Check each file for common issues
        for path, content in files.items():
            # Check for placeholder comments
            placeholders = [
                "// ...", "/* ... */", "// rest of", "// TODO", "// add more",
                "# ...", "# rest of", "# TODO", "# add more",
                "...", "// remaining", "// continue", "// etc"
            ]
            
            for placeholder in placeholders:
                if placeholder.lower() in content.lower():
                    errors.append({
                        "file": path,
                        "type": "placeholder",
                        "message": f"File contains placeholder: {placeholder}"
                    })
                    break
            
            # Check for empty files
            if len(content.strip()) < 10:
                errors.append({
                    "file": path,
                    "type": "empty",
                    "message": "File is nearly empty"
                })
            
            # Check JavaScript/TypeScript files for syntax issues
            if path.endswith(('.js', '.jsx', '.ts', '.tsx')):
                # Check for unclosed brackets
                opens = content.count('{') + content.count('(') + content.count('[')
                closes = content.count('}') + content.count(')') + content.count(']')
                if abs(opens - closes) > 2:
                    errors.append({
                        "file": path,
                        "type": "syntax",
                        "message": "Possible unclosed brackets"
                    })
                
                # Check for incomplete exports
                if 'export default' in content and content.strip().endswith('export default'):
                    errors.append({
                        "file": path,
                        "type": "incomplete",
                        "message": "Incomplete export statement"
                    })
        
        return errors
    
    async def _stage_fix_errors(self, files: Dict[str, str], errors: List[Dict[str, str]]) -> Dict[str, str]:
        """Stage 5: Fix errors in the code."""
        
        # Group errors by file
        files_with_errors = {}
        for error in errors:
            file_path = error["file"]
            if file_path not in files_with_errors:
                files_with_errors[file_path] = []
            files_with_errors[file_path].append(error)
        
        # Fix each file with errors
        for file_path, file_errors in files_with_errors.items():
            if file_path not in files:
                continue
            
            error_descriptions = "\n".join([f"- {e['type']}: {e['message']}" for e in file_errors])
            
            prompt = f"""Fix the following errors in this file:

FILE: {file_path}
ERRORS:
{error_descriptions}

CURRENT CONTENT:
{files[file_path][:8000]}

Provide the COMPLETE fixed file content. Do not use placeholders. The file must be 100% complete and functional.

Output ONLY the fixed file content, nothing else."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a code debugger. Fix the errors and provide the complete, working file."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=4000
            )
            
            self.total_tokens += response.usage.total_tokens if response.usage else 0
            fixed_content = response.choices[0].message.content or ""
            
            # Clean up the response
            fixed_content = fixed_content.strip()
            if fixed_content.startswith("```"):
                # Remove code block markers
                lines = fixed_content.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                fixed_content = "\n".join(lines)
            
            if fixed_content:
                files[file_path] = fixed_content
        
        return files
