"""Code analysis routes - deep analysis, security scanning, code quality metrics."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List, Optional

from fastapi import Depends, HTTPException, Request
import sqlite3

from backend.auth import current_user
from backend.config import API_PREFIX
from backend.database import _now, db


def calculate_cyclomatic_complexity(code: str) -> int:
    """Calculate cyclomatic complexity (simplified)."""
    # Count decision points
    decisions = len(re.findall(r'\b(if|elif|else|for|while|and|or|try|except|with)\b', code))
    return decisions + 1


def calculate_nesting_depth(code: str) -> int:
    """Calculate maximum nesting depth."""
    max_depth = 0
    current_depth = 0
    
    for line in code.split('\n'):
        stripped = line.lstrip()
        if stripped and not stripped.startswith('#'):
            # Count leading spaces
            indent = len(line) - len(stripped)
            current_depth = indent // 4  # Assume 4-space indentation
            max_depth = max(max_depth, current_depth)
    
    return max_depth


def find_security_issues(code: str, language: str) -> List[Dict[str, Any]]:
    """Scan for common security vulnerabilities."""
    issues = []
    lines = code.split('\n')
    
    # SQL injection patterns
    sql_patterns = [
        r'execute\s*\(\s*["\'].*%s.*["\']',
        r'\.format\(',
        r'f["\'].*\{.*\}.*["\']',
    ]
    
    for i, line in enumerate(lines, 1):
        # Check for SQL injection
        if 'SELECT' in line.upper() or 'INSERT' in line.upper() or 'UPDATE' in line.upper():
            for pattern in sql_patterns:
                if re.search(pattern, line):
                    issues.append({
                        "type": "security",
                        "severity": "HIGH",
                        "line": i,
                        "issue": "Potential SQL injection vulnerability",
                        "fix": "Use parameterized queries instead of string formatting"
                    })
        
        # Check for hardcoded secrets
        if re.search(r'(password|secret|api_key|token)\s*=\s*["\'][^"\']+["\']', line, re.IGNORECASE):
            issues.append({
                "type": "security",
                "severity": "HIGH",
                "line": i,
                "issue": "Hardcoded credential detected",
                "fix": "Use environment variables or secure vault"
            })
        
        # Check for eval/exec
        if re.search(r'\beval\(|\bexec\(', line):
            issues.append({
                "type": "security",
                "severity": "HIGH",
                "line": i,
                "issue": "Unsafe use of eval() or exec()",
                "fix": "Avoid dynamic code execution or use safer alternatives"
            })
    
    return issues


def find_code_smells(code: str, language: str) -> List[Dict[str, Any]]:
    """Detect code smells and anti-patterns."""
    smells = []
    lines = code.split('\n')
    
    # Function length
    in_function = False
    func_start = 0
    func_lines = 0
    
    for i, line in enumerate(lines, 1):
        if re.search(r'\bdef\s+\w+\(', line):
            in_function = True
            func_start = i
            func_lines = 0
        elif in_function:
            if line.strip() and not line.strip().startswith('#'):
                func_lines += 1
            if not line.startswith(' ') and not line.startswith('\t') and line.strip():
                # Function ended
                if func_lines > 50:
                    smells.append({
                        "type": "code_smell",
                        "severity": "MEDIUM",
                        "line": func_start,
                        "issue": f"Long function ({func_lines} lines)",
                        "fix": "Break into smaller functions (aim for < 30 lines)"
                    })
                in_function = False
        
        # Too many parameters
        match = re.search(r'def\s+\w+\((.*?)\):', line)
        if match:
            params = [p.strip() for p in match.group(1).split(',') if p.strip()]
            if len(params) > 5:
                smells.append({
                    "type": "code_smell",
                    "severity": "MEDIUM",
                    "line": i,
                    "issue": f"Too many parameters ({len(params)})",
                    "fix": "Consider using a configuration object or builder pattern"
                })
        
        # Nested loops (performance issue)
        if re.search(r'^\s+for\s+.*in.*:', line):
            indent = len(line) - len(line.lstrip())
            if indent >= 8:  # Nested at least 2 levels
                smells.append({
                    "type": "performance",
                    "severity": "MEDIUM",
                    "line": i,
                    "issue": "Deeply nested loop (O(n²) or worse)",
                    "fix": "Consider alternative algorithms or data structures"
                })
    
    return smells


def calculate_maintainability_index(code: str) -> float:
    """
    Calculate maintainability index (0-100).
    Formula: 171 - 5.2*ln(HV) - 0.23*CC - 16.2*ln(LOC)
    Simplified version without full Halstead metrics.
    """
    lines = [l for l in code.split('\n') if l.strip() and not l.strip().startswith('#')]
    loc = len(lines)
    
    if loc == 0:
        return 100.0
    
    complexity = calculate_cyclomatic_complexity(code)
    
    # Simplified calculation
    import math
    try:
        mi = 171 - 5.2 * math.log(loc * 10) - 0.23 * complexity - 16.2 * math.log(loc)
        mi = max(0, min(100, mi))  # Clamp to 0-100
    except:
        mi = 50.0
    
    return round(mi, 2)


def register_routes(api):
    """Register analysis routes."""
    
    @api.post(f"{API_PREFIX}/analyze/code")
    async def analyze_code(
        request: Request,
        u: sqlite3.Row = Depends(current_user)
    ) -> Dict[str, Any]:
        """
        Deep code analysis: metrics, security scanning, code smells.
        
        Body: {
            "code": str,
            "language": str (python, javascript, typescript, etc.),
            "file_name": str (optional)
        }
        """
        body = await request.json()
        code = body.get("code", "")
        language = body.get("language", "python").lower()
        file_name = body.get("file_name", "untitled")
        
        if not code:
            raise HTTPException(status_code=400, detail="Code content required")
        
        # Calculate hash for caching
        code_hash = hashlib.sha256(code.encode()).hexdigest()[:16]
        
        # Check cache
        with db() as conn:
            cached = conn.execute(
                "SELECT metrics FROM analysis_results WHERE code_hash = ? AND created_at > ?",
                (code_hash, _now() - 3600)  # Cache for 1 hour
            ).fetchone()
            
            if cached:
                return json.loads(cached["metrics"])
        
        # Calculate metrics
        loc = len([l for l in code.split('\n') if l.strip()])
        complexity = calculate_cyclomatic_complexity(code)
        nesting = calculate_nesting_depth(code)
        maintainability = calculate_maintainability_index(code)
        
        # Find issues
        security_issues = find_security_issues(code, language)
        code_smells = find_code_smells(code, language)
        
        # Combine all issues
        all_issues = security_issues + code_smells
        
        # Calculate severity counts
        severity_counts = {
            "HIGH": len([i for i in all_issues if i["severity"] == "HIGH"]),
            "MEDIUM": len([i for i in all_issues if i["severity"] == "MEDIUM"]),
            "LOW": len([i for i in all_issues if i["severity"] == "LOW"])
        }
        
        # Overall grade
        if maintainability >= 80 and severity_counts["HIGH"] == 0:
            grade = "A"
        elif maintainability >= 60 and severity_counts["HIGH"] <= 1:
            grade = "B"
        elif maintainability >= 40 and severity_counts["HIGH"] <= 3:
            grade = "C"
        elif maintainability >= 20:
            grade = "D"
        else:
            grade = "F"
        
        result = {
            "file_name": file_name,
            "language": language,
            "metrics": {
                "lines_of_code": loc,
                "cyclomatic_complexity": complexity,
                "max_nesting_depth": nesting,
                "maintainability_index": maintainability,
                "grade": grade
            },
            "issues": all_issues,
            "severity_counts": severity_counts,
            "summary": {
                "total_issues": len(all_issues),
                "critical": severity_counts["HIGH"],
                "fixable": len([i for i in all_issues if i.get("fix")])
            }
        }
        
        # Cache result
        with db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO analysis_results (code_hash, metrics, created_at) VALUES (?, ?, ?)",
                (code_hash, json.dumps(result), _now())
            )
        
        return result
