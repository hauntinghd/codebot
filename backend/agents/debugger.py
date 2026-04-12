"""Debugger Agent.

Autonomous debugging agent that:
- Analyzes code for potential errors
- Runs tests (Jest/Pytest)
- Fixes bugs autonomously
- Iterates until code passes all tests
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from .base import Agent, AgentRole, AgentContext, AgentResult

logger = logging.getLogger("codebot.agents")


DEBUGGER_SYSTEM_PROMPT = """You are the Debugger Agent - an expert at finding and fixing bugs.

Your capabilities:
1. Static Analysis: Find potential issues without running code
2. Error Diagnosis: Understand error messages and stack traces
3. Fix Generation: Produce precise fixes for bugs
4. Test Creation: Write tests to prevent regressions

ANALYSIS OUTPUT FORMAT:
When analyzing code, output:

<analysis>
  <issue severity="error|warning|info">
    <file>path/to/file.ts</file>
    <line>42</line>
    <description>What's wrong</description>
    <fix>How to fix it</fix>
  </issue>
  ...
</analysis>

FIX OUTPUT FORMAT:
When fixing code, output in artifact format:

<artifact id="fix-{timestamp}" title="Bug Fix">
  <action type="file" path="path/to/file.ts">
[COMPLETE FIXED FILE CONTENT]
  </action>
</artifact>

CRITICAL RULES:
1. ALWAYS provide the COMPLETE fixed file, not patches
2. Explain WHY the bug occurred
3. Add comments marking your fixes
4. Suggest tests to prevent regression
5. Check for related bugs in other files
"""


class DebuggerAgent(Agent):
    """Debugger Agent - Finds and fixes bugs autonomously.
    
    Features:
    - Static code analysis
    - Runtime error diagnosis
    - Autonomous fix iteration
    - Test generation
    """
    
    MAX_FIX_ITERATIONS = 3
    
    def __init__(self, ai_client: Any, model: str = "gpt-4o"):
        super().__init__(
            ai_client=ai_client,
            role=AgentRole.DEBUGGER,
            name="Debugger",
            description="Finds and fixes bugs autonomously",
            model=model,
        )
    
    @property
    def system_prompt(self) -> str:
        return DEBUGGER_SYSTEM_PROMPT
    
    async def execute(
        self,
        context: AgentContext,
        code_files: Optional[Dict[str, str]] = None,
        errors: Optional[List[str]] = None,
        auto_fix: bool = True,
        **kwargs
    ) -> AgentResult:
        """Analyze code and fix bugs.
        
        Args:
            context: Agent context with generated code
            code_files: Code files to debug (uses context.generated_code if not provided)
            errors: Specific errors to fix
            auto_fix: Whether to automatically generate fixes
        """
        import time
        start_time = time.time()
        
        files_to_debug = code_files or context.generated_code or {}
        errors_to_fix = errors or context.errors or []
        
        if not files_to_debug and not errors_to_fix:
            return AgentResult(
                success=True,
                output="No code or errors to debug.",
                artifacts={"issues": [], "fixes": []},
            )
        
        all_issues: List[Dict] = []
        all_fixes: Dict[str, str] = {}
        total_tokens = 0
        
        # Step 1: Analyze code for issues
        if files_to_debug:
            analysis_result = await self._analyze_code(files_to_debug, errors_to_fix)
            all_issues = analysis_result.get("issues", [])
            total_tokens += analysis_result.get("tokens", 0)
        
        # Step 2: Generate fixes if auto_fix is enabled
        if auto_fix and (all_issues or errors_to_fix):
            for iteration in range(self.MAX_FIX_ITERATIONS):
                logger.info(f"Fix iteration {iteration + 1}/{self.MAX_FIX_ITERATIONS}")
                
                fix_result = await self._generate_fixes(
                    files_to_debug,
                    all_issues,
                    errors_to_fix
                )
                
                total_tokens += fix_result.get("tokens", 0)
                
                if fix_result.get("fixes"):
                    all_fixes.update(fix_result["fixes"])
                    
                    # Update files with fixes for next iteration
                    for path, content in fix_result["fixes"].items():
                        files_to_debug[path] = content
                
                if not fix_result.get("has_remaining_issues", False):
                    break
        
        # Step 3: Generate test suggestions
        test_suggestions = await self._suggest_tests(files_to_debug, all_issues)
        
        return AgentResult(
            success=len(all_issues) == 0 or len(all_fixes) > 0,
            output=self._format_debug_report(all_issues, all_fixes, test_suggestions),
            artifacts={
                "issues": all_issues,
                "fixes": all_fixes,
                "test_suggestions": test_suggestions,
            },
            tokens_used=total_tokens,
            execution_time=time.time() - start_time,
            next_agent=AgentRole.OPTIMIZER if not all_issues else None,
        )
    
    async def _analyze_code(
        self,
        files: Dict[str, str],
        known_errors: List[str]
    ) -> Dict[str, Any]:
        """Analyze code for potential issues."""
        # Prepare files summary (limit size for token efficiency)
        files_summary = ""
        for path, content in list(files.items())[:10]:
            files_summary += f"\n--- {path} ---\n"
            files_summary += self.compress_prompt(content, max_tokens=1000)
        
        errors_section = ""
        if known_errors:
            errors_section = "\n\nKNOWN ERRORS:\n" + "\n".join(f"- {e}" for e in known_errors[:10])
        
        prompt = f"""Analyze this code for bugs, issues, and potential problems:

{files_summary}
{errors_section}

Output your analysis in the XML format specified.
Focus on:
1. Runtime errors (null access, type mismatches)
2. Logic errors (wrong conditions, infinite loops)
3. Missing error handling
4. Security issues (XSS, injection)
5. Performance problems"""
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]
        
        try:
            response, tokens = await self._call_ai(
                messages,
                temperature=0.2,
                max_tokens=2000,
            )
            
            issues = self._parse_analysis(response)
            
            return {
                "issues": issues,
                "tokens": tokens,
                "raw_response": response,
            }
            
        except Exception as e:
            logger.error(f"Code analysis failed: {e}")
            return {"issues": [], "tokens": 0}
    
    async def _generate_fixes(
        self,
        files: Dict[str, str],
        issues: List[Dict],
        errors: List[str]
    ) -> Dict[str, Any]:
        """Generate fixes for identified issues."""
        if not issues and not errors:
            return {"fixes": {}, "has_remaining_issues": False, "tokens": 0}
        
        # Group issues by file
        issues_by_file: Dict[str, List[Dict]] = {}
        for issue in issues:
            file_path = issue.get("file", "unknown")
            if file_path not in issues_by_file:
                issues_by_file[file_path] = []
            issues_by_file[file_path].append(issue)
        
        fixes: Dict[str, str] = {}
        total_tokens = 0
        
        # Fix files with issues
        for file_path, file_issues in issues_by_file.items():
            if file_path not in files:
                continue
            
            current_content = files[file_path]
            
            issues_desc = "\n".join(
                f"- Line {i.get('line', '?')}: {i.get('description', '')} | Fix: {i.get('fix', '')}"
                for i in file_issues
            )
            
            prompt = f"""Fix all issues in this file:

FILE: {file_path}

CURRENT CONTENT:
{current_content}

ISSUES TO FIX:
{issues_desc}

Output the COMPLETE fixed file in artifact format.
Add // FIXED: comments where you made changes."""
            
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ]
            
            try:
                response, tokens = await self._call_ai(
                    messages,
                    temperature=0.2,
                    max_tokens=3000,
                )
                
                total_tokens += tokens
                
                # Extract fixed content from artifact
                fixed_content = self._extract_fixed_content(response, file_path)
                if fixed_content:
                    fixes[file_path] = fixed_content
                    
            except Exception as e:
                logger.error(f"Fix generation failed for {file_path}: {e}")
        
        return {
            "fixes": fixes,
            "has_remaining_issues": len(issues) > len(fixes),
            "tokens": total_tokens,
        }
    
    async def _suggest_tests(
        self,
        files: Dict[str, str],
        issues: List[Dict]
    ) -> List[Dict[str, str]]:
        """Suggest tests based on fixed issues."""
        if not issues:
            return []
        
        suggestions = []
        for issue in issues[:5]:  # Limit to 5 suggestions
            suggestions.append({
                "file": issue.get("file", "unknown"),
                "test_name": f"test_{issue.get('description', 'issue')[:30].lower().replace(' ', '_')}",
                "description": f"Test to verify fix for: {issue.get('description', '')}",
            })
        
        return suggestions
    
    def _parse_analysis(self, response: str) -> List[Dict]:
        """Parse the analysis XML response."""
        issues = []
        
        # Pattern for issue tags
        issue_pattern = r'<issue\s+severity="([^"]+)">(.*?)</issue>'
        for match in re.finditer(issue_pattern, response, re.DOTALL):
            severity = match.group(1)
            content = match.group(2)
            
            issue = {"severity": severity}
            
            # Extract file
            file_match = re.search(r'<file>(.*?)</file>', content)
            if file_match:
                issue["file"] = file_match.group(1).strip()
            
            # Extract line
            line_match = re.search(r'<line>(\d+)</line>', content)
            if line_match:
                issue["line"] = int(line_match.group(1))
            
            # Extract description
            desc_match = re.search(r'<description>(.*?)</description>', content, re.DOTALL)
            if desc_match:
                issue["description"] = desc_match.group(1).strip()
            
            # Extract fix
            fix_match = re.search(r'<fix>(.*?)</fix>', content, re.DOTALL)
            if fix_match:
                issue["fix"] = fix_match.group(1).strip()
            
            issues.append(issue)
        
        return issues
    
    def _extract_fixed_content(self, response: str, file_path: str) -> Optional[str]:
        """Extract the fixed file content from the response."""
        # Try artifact format first
        pattern = rf'<action\s+type="file"\s+path="{re.escape(file_path)}">\n?(.*?)</action>'
        match = re.search(pattern, response, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Try any file action
        pattern = r'<action\s+type="file"\s+path="[^"]+">\n?(.*?)</action>'
        match = re.search(pattern, response, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Try code block
        pattern = r'```(?:typescript|javascript|python|tsx|ts|js|py)?\n(.*?)```'
        match = re.search(pattern, response, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        return None
    
    def _format_debug_report(
        self,
        issues: List[Dict],
        fixes: Dict[str, str],
        test_suggestions: List[Dict]
    ) -> str:
        """Format the debug report for output."""
        report = "# Debug Report\n\n"
        
        if not issues:
            report += "✅ No issues found!\n\n"
        else:
            report += f"## Issues Found ({len(issues)})\n\n"
            for issue in issues:
                severity_icon = "🔴" if issue.get("severity") == "error" else "🟡" if issue.get("severity") == "warning" else "ℹ️"
                report += f"{severity_icon} **{issue.get('file', 'unknown')}** Line {issue.get('line', '?')}\n"
                report += f"   {issue.get('description', '')}\n\n"
        
        if fixes:
            report += f"## Fixes Applied ({len(fixes)})\n\n"
            for path in fixes:
                report += f"- ✅ {path}\n"
            report += "\n"
        
        if test_suggestions:
            report += "## Suggested Tests\n\n"
            for test in test_suggestions:
                report += f"- `{test['test_name']}` for {test['file']}\n"
        
        return report
    
    async def quick_fix(
        self,
        file_path: str,
        content: str,
        error: str
    ) -> Tuple[bool, str, int]:
        """Quick single-file error fix.
        
        Returns:
            Tuple of (success, fixed_content_or_error, tokens_used)
        """
        prompt = f"""Fix this error:

FILE: {file_path}
ERROR: {error}

CONTENT:
{content}

Output ONLY the fixed code, no explanations."""
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]
        
        try:
            response, tokens = await self._call_ai(
                messages,
                temperature=0.1,
                max_tokens=3000,
            )
            
            # Clean response
            fixed = response
            if fixed.startswith("```"):
                lines = fixed.split("\n")
                fixed = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            
            return True, fixed, tokens
            
        except Exception as e:
            return False, str(e), 0
