"""Optimizer Agent.

Refactoring and performance optimization agent that:
- Improves code quality
- Reduces bundle size
- Enhances performance
- Ensures best practices
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from .base import Agent, AgentRole, AgentContext, AgentResult

logger = logging.getLogger("codebot.agents")


OPTIMIZER_SYSTEM_PROMPT = """You are the Optimizer Agent - an expert at making code faster, cleaner, and more efficient.

Your optimization areas:
1. **Performance**: Reduce render cycles, optimize algorithms, minimize network calls
2. **Bundle Size**: Tree-shake, lazy load, code split
3. **Code Quality**: DRY, SOLID, clean architecture
4. **Best Practices**: Accessibility, SEO, security
5. **Developer Experience**: Better types, documentation, testing

ANALYSIS OUTPUT FORMAT:
<optimization-analysis>
  <metric name="performance" score="8/10">
    <finding>Description of what can be improved</finding>
    <recommendation>How to improve it</recommendation>
    <impact>high|medium|low</impact>
  </metric>
  ...
</optimization-analysis>

REFACTORED OUTPUT FORMAT:
<artifact id="optimized-{timestamp}" title="Optimized Code">
  <action type="file" path="path/to/file.ts">
[COMPLETE OPTIMIZED FILE CONTENT]
  </action>
</artifact>

CRITICAL RULES:
1. Don't break working code - optimizations must maintain functionality
2. Measure improvements - state what improves (render time, bundle size, etc.)
3. Prioritize high-impact changes
4. Keep code readable - don't over-optimize
5. Add performance comments for future maintainers
"""


class OptimizerAgent(Agent):
    """Optimizer Agent - Improves code quality and performance.
    
    Capabilities:
    - Performance profiling suggestions
    - Code refactoring
    - Bundle size optimization
    - Best practices enforcement
    """
    
    def __init__(self, ai_client: Any, model: str = "gpt-4o"):
        super().__init__(
            ai_client=ai_client,
            role=AgentRole.OPTIMIZER,
            name="Optimizer",
            description="Optimizes code for performance and quality",
            model=model,
        )
    
    @property
    def system_prompt(self) -> str:
        return OPTIMIZER_SYSTEM_PROMPT
    
    async def execute(
        self,
        context: AgentContext,
        code_files: Optional[Dict[str, str]] = None,
        optimization_focus: str = "all",
        **kwargs
    ) -> AgentResult:
        """Analyze and optimize code.
        
        Args:
            context: Agent context with generated code
            code_files: Code files to optimize (uses context.generated_code if not provided)
            optimization_focus: Focus area ("performance", "quality", "size", "all")
        """
        import time
        start_time = time.time()
        
        files_to_optimize = code_files or context.generated_code or {}
        
        if not files_to_optimize:
            return AgentResult(
                success=True,
                output="No code to optimize.",
                artifacts={"optimizations": []},
            )
        
        total_tokens = 0
        all_findings: List[Dict] = []
        optimized_files: Dict[str, str] = {}
        
        # Step 1: Analyze code quality
        analysis = await self._analyze_code_quality(files_to_optimize, optimization_focus)
        all_findings = analysis.get("findings", [])
        total_tokens += analysis.get("tokens", 0)
        
        # Step 2: Apply optimizations for high-impact findings
        high_impact = [f for f in all_findings if f.get("impact") == "high"]
        
        if high_impact:
            optimization_result = await self._apply_optimizations(
                files_to_optimize,
                high_impact
            )
            optimized_files = optimization_result.get("optimized_files", {})
            total_tokens += optimization_result.get("tokens", 0)
        
        # Step 3: Generate optimization report
        report = self._generate_report(all_findings, optimized_files)
        
        return AgentResult(
            success=True,
            output=report,
            artifacts={
                "findings": all_findings,
                "optimized_files": optimized_files,
                "metrics": {
                    "total_findings": len(all_findings),
                    "high_impact": len(high_impact),
                    "files_optimized": len(optimized_files),
                },
            },
            tokens_used=total_tokens,
            execution_time=time.time() - start_time,
        )
    
    async def _analyze_code_quality(
        self,
        files: Dict[str, str],
        focus: str
    ) -> Dict[str, Any]:
        """Analyze code quality and find optimization opportunities."""
        # Prepare files summary
        files_summary = ""
        for path, content in list(files.items())[:10]:
            files_summary += f"\n--- {path} ---\n"
            files_summary += self.compress_prompt(content, max_tokens=800)
        
        focus_instruction = ""
        if focus == "performance":
            focus_instruction = "Focus on runtime performance: React re-renders, algorithm complexity, memoization, lazy loading."
        elif focus == "quality":
            focus_instruction = "Focus on code quality: DRY violations, code duplication, complex functions, unclear naming."
        elif focus == "size":
            focus_instruction = "Focus on bundle size: unused code, large imports, missing tree-shaking, missing code splitting."
        else:
            focus_instruction = "Analyze all aspects: performance, quality, and bundle size."
        
        prompt = f"""Analyze this code for optimization opportunities:

{files_summary}

{focus_instruction}

Output your analysis in the XML format specified.
Rate each metric out of 10 and provide actionable recommendations."""
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]
        
        try:
            response, tokens = await self._call_ai(
                messages,
                temperature=0.3,
                max_tokens=2500,
            )
            
            findings = self._parse_analysis(response)
            
            return {
                "findings": findings,
                "tokens": tokens,
                "raw_response": response,
            }
            
        except Exception as e:
            logger.error(f"Code quality analysis failed: {e}")
            return {"findings": [], "tokens": 0}
    
    async def _apply_optimizations(
        self,
        files: Dict[str, str],
        findings: List[Dict]
    ) -> Dict[str, Any]:
        """Apply optimizations based on findings."""
        optimized_files: Dict[str, str] = {}
        total_tokens = 0
        
        # Group findings by file if possible
        files_to_optimize = set()
        for finding in findings:
            # Try to identify which files the finding applies to
            for file_path in files:
                if file_path in finding.get("finding", "") or file_path in finding.get("recommendation", ""):
                    files_to_optimize.add(file_path)
        
        # If no specific files, optimize the main component files
        if not files_to_optimize:
            for path in files:
                if any(x in path.lower() for x in ["app", "main", "index", "component"]):
                    files_to_optimize.add(path)
                    if len(files_to_optimize) >= 3:
                        break
        
        # Apply optimizations to each file
        for file_path in files_to_optimize:
            if file_path not in files:
                continue
            
            content = files[file_path]
            relevant_findings = [
                f for f in findings
                if file_path in f.get("finding", "") or file_path in f.get("recommendation", "")
            ]
            
            if not relevant_findings:
                relevant_findings = findings[:2]  # Apply general findings
            
            findings_desc = "\n".join(
                f"- {f.get('metric', 'general')}: {f.get('finding', '')} → {f.get('recommendation', '')}"
                for f in relevant_findings
            )
            
            prompt = f"""Optimize this file based on the findings:

FILE: {file_path}

CONTENT:
{content}

FINDINGS TO ADDRESS:
{findings_desc}

Apply the optimizations and output the COMPLETE optimized file in artifact format.
Add // OPTIMIZED: comments where you made changes."""
            
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
                
                # Extract optimized content
                optimized_content = self._extract_optimized_content(response)
                if optimized_content:
                    optimized_files[file_path] = optimized_content
                    
            except Exception as e:
                logger.error(f"Optimization failed for {file_path}: {e}")
        
        return {
            "optimized_files": optimized_files,
            "tokens": total_tokens,
        }
    
    def _parse_analysis(self, response: str) -> List[Dict]:
        """Parse the analysis XML response."""
        findings = []
        
        # Pattern for metric tags
        metric_pattern = r'<metric\s+name="([^"]+)"\s+score="([^"]+)">(.*?)</metric>'
        for match in re.finditer(metric_pattern, response, re.DOTALL):
            metric_name = match.group(1)
            score = match.group(2)
            content = match.group(3)
            
            finding = {
                "metric": metric_name,
                "score": score,
            }
            
            # Extract finding
            finding_match = re.search(r'<finding>(.*?)</finding>', content, re.DOTALL)
            if finding_match:
                finding["finding"] = finding_match.group(1).strip()
            
            # Extract recommendation
            rec_match = re.search(r'<recommendation>(.*?)</recommendation>', content, re.DOTALL)
            if rec_match:
                finding["recommendation"] = rec_match.group(1).strip()
            
            # Extract impact
            impact_match = re.search(r'<impact>(.*?)</impact>', content, re.DOTALL)
            if impact_match:
                finding["impact"] = impact_match.group(1).strip().lower()
            
            findings.append(finding)
        
        return findings
    
    def _extract_optimized_content(self, response: str) -> Optional[str]:
        """Extract optimized file content from response."""
        # Try artifact format
        pattern = r'<action\s+type="file"\s+path="[^"]+">\n?(.*?)</action>'
        match = re.search(pattern, response, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Try code block
        pattern = r'```(?:typescript|javascript|tsx|ts|js)?\n(.*?)```'
        match = re.search(pattern, response, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        return None
    
    def _generate_report(
        self,
        findings: List[Dict],
        optimized_files: Dict[str, str]
    ) -> str:
        """Generate the optimization report."""
        report = "# Optimization Report\n\n"
        
        if not findings:
            report += "✅ Code is already well-optimized!\n\n"
            return report
        
        # Score summary
        report += "## Quality Scores\n\n"
        for finding in findings:
            score = finding.get("score", "?/10")
            metric = finding.get("metric", "unknown")
            impact = finding.get("impact", "medium")
            icon = "🔴" if impact == "high" else "🟡" if impact == "medium" else "🟢"
            report += f"- {icon} **{metric.title()}**: {score}\n"
        report += "\n"
        
        # High-impact findings
        high_impact = [f for f in findings if f.get("impact") == "high"]
        if high_impact:
            report += "## High-Impact Optimizations\n\n"
            for f in high_impact:
                report += f"### {f.get('metric', 'Optimization').title()}\n"
                report += f"**Issue**: {f.get('finding', 'N/A')}\n\n"
                report += f"**Fix**: {f.get('recommendation', 'N/A')}\n\n"
        
        # Applied optimizations
        if optimized_files:
            report += f"## Changes Applied ({len(optimized_files)} files)\n\n"
            for path in optimized_files:
                report += f"- ✅ {path}\n"
        
        return report
    
    async def quick_refactor(
        self,
        file_path: str,
        content: str,
        refactor_type: str = "clean"
    ) -> AgentResult:
        """Quick single-file refactoring.
        
        Args:
            file_path: Path to the file
            content: Current file content
            refactor_type: Type of refactoring ("clean", "performance", "types", "docs")
        """
        import time
        start_time = time.time()
        
        refactor_instructions = {
            "clean": "Clean up the code: remove dead code, improve naming, simplify logic.",
            "performance": "Optimize for performance: memoization, lazy loading, reduce re-renders.",
            "types": "Improve TypeScript types: add missing types, make types stricter, use generics.",
            "docs": "Add documentation: JSDoc comments, inline comments for complex logic.",
        }
        
        instruction = refactor_instructions.get(refactor_type, refactor_instructions["clean"])
        
        prompt = f"""Refactor this file:

FILE: {file_path}
TASK: {instruction}

CONTENT:
{content}

Output the COMPLETE refactored file. Add // REFACTORED: comments where you made changes."""
        
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
            
            # Clean response
            refactored = response
            if refactored.startswith("```"):
                lines = refactored.split("\n")
                refactored = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            
            return AgentResult(
                success=True,
                output=refactored,
                artifacts={
                    "file_path": file_path,
                    "refactored_content": refactored,
                    "refactor_type": refactor_type,
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
