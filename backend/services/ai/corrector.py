"""
Corrector Layer: 5th layer of AI architecture
Detects and corrects hallucinations, adds source citations, implements user feedback loop
"""

import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json

# Known hallucination patterns
HALLUCINATION_PATTERNS = [
    r"I don't have access to",
    r"I cannot (read|see|access|check)",
    r"As an AI language model",
    r"I don't actually have",
    r"I cannot directly (read|see|access|check)",
    r"I'm unable to (read|see|access|check)",
    r"I don't see any files",
    r"I cannot verify",
    r"I don't have the ability to",
    r"I'm an AI and can't",
]

# Trusted source URLs (expandable)
TRUSTED_SOURCES = {
    "python": [
        "https://docs.python.org/3/",
        "https://peps.python.org/",
        "https://realpython.com/",
    ],
    "javascript": [
        "https://developer.mozilla.org/",
        "https://javascript.info/",
        "https://tc39.es/",
    ],
    "typescript": [
        "https://www.typescriptlang.org/docs/",
        "https://github.com/microsoft/TypeScript",
    ],
    "react": [
        "https://react.dev/",
        "https://github.com/facebook/react",
    ],
    "fastapi": [
        "https://fastapi.tiangolo.com/",
        "https://github.com/tiangolo/fastapi",
    ],
    "nextjs": [
        "https://nextjs.org/docs",
        "https://github.com/vercel/next.js",
    ],
    "tailwind": [
        "https://tailwindcss.com/docs",
    ],
    "svelte": [
        "https://svelte.dev/docs",
    ],
    "vue": [
        "https://vuejs.org/guide/",
    ],
    "node": [
        "https://nodejs.org/docs/latest/api/",
    ],
    "express": [
        "https://expressjs.com/en/api.html",
    ],
    "stripe": [
        "https://docs.stripe.com/api",
    ],
}


class CorrectorLayer:
    """
    Fifth layer: Detects hallucinations, verifies code accuracy, adds citations
    """

    def __init__(self, db_conn=None):
        self.db = db_conn
        self.correction_cache = {}

    async def analyze_response(
        self,
        response: str,
        context: Dict,
        files_accessed: List[str] = None,
    ) -> Dict:
        """
        Main analysis function
        Returns: {
            'has_hallucination': bool,
            'confidence': float,
            'issues': List[str],
            'corrections': List[Dict],
            'sources': List[str],
            'verified': bool
        }
        """
        result = {
            "has_hallucination": False,
            "confidence": 1.0,
            "issues": [],
            "corrections": [],
            "sources": [],
            "verified": False,
        }

        # Pattern-based hallucination detection
        hallucination_score = 0
        for pattern in HALLUCINATION_PATTERNS:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                hallucination_score += len(matches)
                result["issues"].append(f"Detected limitation statement: {matches[0][:50]}...")

        if hallucination_score > 0:
            result["has_hallucination"] = True
            result["confidence"] = max(0.0, 1.0 - (hallucination_score * 0.2))

        # Check file access claims vs actual files accessed
        if files_accessed is not None:
            claimed_files = self._extract_file_mentions(response)
            for claimed_file in claimed_files:
                if claimed_file not in files_accessed and claimed_file not in response:
                    result["issues"].append(
                        f"Mentioned file '{claimed_file}' but may not have accessed it"
                    )
                    result["confidence"] -= 0.1

        # Code quality checks
        code_issues = self._check_code_quality(response, context)
        if code_issues:
            result["issues"].extend(code_issues)
            result["confidence"] -= len(code_issues) * 0.05

        # Detect vague responses
        if self._is_vague_response(response):
            result["issues"].append("Response may be too vague or generic")
            result["confidence"] -= 0.15

        # Add sources for code snippets
        detected_lang = self._detect_language(response)
        if detected_lang:
            result["sources"] = TRUSTED_SOURCES.get(detected_lang, [])

        # Verify against previous corrections
        if self.db:
            similar_corrections = await self._check_correction_history(response)
            if similar_corrections:
                result["corrections"] = similar_corrections

        result["verified"] = result["confidence"] >= 0.7 and not result["has_hallucination"]

        return result

    def _check_code_quality(self, response: str, context: Dict) -> List[str]:
        """Check generated code for common quality issues."""
        issues = []
        # Check for placeholder/stub code
        placeholder_patterns = [
            r"TODO",
            r"FIXME",
            r"HACK",
            r"// rest of .*remains",
            r"# rest of .*remains",
            r"\.\.\. more code here",
            r"placeholder",
            r"lorem ipsum",
            r"coming soon",
        ]
        for pattern in placeholder_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                issues.append(f"Contains placeholder/incomplete code: '{pattern}'")

        # Check for common security issues in generated code
        security_patterns = [
            (r"eval\(", "Uses eval() — potential security risk"),
            (r"innerHTML\s*=", "Uses innerHTML — XSS risk, prefer textContent"),
            (r"password.*=.*['\"][^'\"]{1,20}['\"]", "Possible hardcoded password"),
            (r"api[_-]?key.*=.*['\"][^'\"]{10,}['\"]", "Possible hardcoded API key"),
        ]
        for pattern, desc in security_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                issues.append(desc)

        return issues

    def _extract_file_mentions(self, text: str) -> List[str]:
        """Extract file paths mentioned in response"""
        file_pattern = r"[\w\-/]+\.(py|js|tsx|ts|css|html|json|md|txt|yml|yaml)"
        return list(set(re.findall(file_pattern, text)))

    def _is_vague_response(self, text: str) -> bool:
        """Detect overly vague or generic responses"""
        vague_phrases = [
            "you might want to",
            "you could try",
            "it depends on",
            "there are many ways",
            "it's possible that",
            "you may need to",
            "consider checking",
            "you should probably",
        ]
        
        vague_count = sum(1 for phrase in vague_phrases if phrase in text.lower())
        
        # Also check for lack of specifics (no code, no file names, no line numbers)
        has_code = "```" in text
        has_files = bool(self._extract_file_mentions(text))
        has_numbers = bool(re.search(r"line \d+|L\d+|\d+ lines", text))
        
        is_vague = vague_count >= 2 and not (has_code or has_files or has_numbers)
        return is_vague

    def _detect_language(self, text: str) -> Optional[str]:
        """Detect programming language from code blocks"""
        code_block_match = re.search(r"```(\w+)", text)
        if code_block_match:
            lang = code_block_match.group(1).lower()
            if lang in TRUSTED_SOURCES:
                return lang
        
        # Fallback: detect by keywords
        if "import React" in text or "useState" in text:
            return "react"
        elif "from fastapi" in text or "FastAPI" in text:
            return "fastapi"
        elif "def " in text and "import" in text:
            return "python"
        elif "function" in text or "const " in text:
            return "javascript"
            
        return None

    async def _check_correction_history(self, response: str) -> List[Dict]:
        """Check if similar issues were reported before"""
        # This would query the hallucination_reports table
        # For now, return empty list (implement with DB later)
        return []

    async def report_issue(
        self,
        message_id: int,
        issue_type: str,
        description: str,
        user_id: int,
        code_snippet: Optional[str] = None,
    ) -> int:
        """
        User feedback: Report hallucination or error
        Types: 'hallucination', 'incorrect_code', 'wrong_file', 'vague', 'other'
        """
        if not self.db:
            return -1

        cursor = self.db.cursor()
        cursor.execute(
            """
            INSERT INTO hallucination_reports 
            (message_id, issue_type, description, code_snippet, reported_by, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
        """,
            (
                message_id,
                issue_type,
                description,
                code_snippet,
                user_id,
                datetime.utcnow().isoformat(),
            ),
        )
        self.db.commit()
        report_id = cursor.lastrowid

        # Log for analysis
        print(f"[CORRECTOR] Issue reported: {issue_type} - {description[:50]}...")

        return report_id

    async def get_verified_badge(self, analysis: Dict) -> Dict:
        """
        Generate verification badge data for frontend
        """
        if analysis["verified"]:
            return {
                "show": True,
                "type": "verified",
                "text": "Verified Response",
                "color": "green",
                "confidence": analysis["confidence"],
            }
        elif analysis["has_hallucination"]:
            return {
                "show": True,
                "type": "warning",
                "text": "Contains Limitations",
                "color": "yellow",
                "confidence": analysis["confidence"],
            }
        elif analysis["confidence"] < 0.5:
            return {
                "show": True,
                "type": "caution",
                "text": "May Need Verification",
                "color": "orange",
                "confidence": analysis["confidence"],
            }
        else:
            return {"show": False}

    def inject_sources(self, response: str, sources: List[str]) -> str:
        """
        Add source citations to response
        """
        if not sources:
            return response

        citation_block = "\n\n---\n**Sources:**\n"
        for i, source in enumerate(sources[:3], 1):  # Max 3 sources
            citation_block += f"{i}. [{source}]({source})\n"

        return response + citation_block


# Global instance
corrector = CorrectorLayer()


async def correct_and_verify(
    response: str,
    context: Dict,
    files_accessed: List[str] = None,
    inject_citations: bool = True,
) -> Tuple[str, Dict]:
    """
    Main entry point for Corrector Layer
    Returns: (potentially modified response, analysis report)
    """
    analysis = await corrector.analyze_response(response, context, files_accessed)

    # Inject sources if detected language
    if inject_citations and analysis["sources"]:
        response = corrector.inject_sources(response, analysis["sources"])

    # Log high-confidence hallucinations
    if analysis["has_hallucination"] and analysis["confidence"] < 0.5:
        print(f"[CORRECTOR] High-confidence hallucination detected: {analysis['issues']}")

    return response, analysis
