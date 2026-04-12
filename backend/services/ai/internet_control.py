"""
Internet Access Control Layer
Restricts AI from accessing internet unless absolutely necessary
"""

import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class InternetAccessController:
    """
    Controls when AI can access internet information.
    Default: FORBIDDEN
    Only allows access for specific critical cases
    """

    # Patterns that indicate internet access might be legitimately needed
    LEGITIMATE_INTERNET_NEEDS = [
        # Error messages that require documentation lookup
        r"error:\s+[A-Z]\w+Error:",  # Python errors
        r"TypeError|ValueError|AttributeError|ImportError|ModuleNotFoundError",
        r"Cannot find module|Module not found",  # JS/TS errors
        r"SyntaxError|ReferenceError|RangeError",
        r"TS\d{4}:",  # TypeScript errors (e.g., TS2304)
        r"pylance\(\w+\)",  # Pylance errors
        r"eslint\(\w+\)",  # ESLint errors
        
        # Package/dependency version lookups (when absolutely needed)
        r"(npm|pip|poetry)\s+install\s+\S+@\d+",
        r"package.*version.*compatibility",
        
        # Security vulnerabilities (need CVE lookups)
        r"CVE-\d{4}-\d+",
        r"security vulnerability",
        r"known exploit",
    ]

    # Patterns that indicate user is asking about general knowledge (DO NOT allow internet)
    FORBIDDEN_PATTERNS = [
        r"what is|who is|tell me about|explain",
        r"how to|best way to|best practice",
        r"tutorial|example|sample code",
        r"difference between|compare",
        r"pros and cons|advantages|disadvantages",
    ]

    def __init__(self):
        self.access_log = []

    def analyze_request(self, user_message: str, context: Dict) -> Dict:
        """
        Analyze if internet access is legitimately needed.
        Returns: {
            'allowed': bool,
            'reason': str,
            'confidence': float,
            'specific_lookup': str or None
        }
        """
        result = {
            'allowed': False,
            'reason': 'Internet access forbidden by default',
            'confidence': 0.0,
            'specific_lookup': None,
        }

        # First check if this is a forbidden general knowledge request
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, user_message, re.IGNORECASE):
                result['reason'] = 'General knowledge request detected - must work with uploaded files only'
                result['confidence'] = 1.0
                return result

        # Check if user has uploaded files - if yes, they should work with those first
        has_files = context.get('file_count', 0) > 0 or len(context.get('files_accessed', [])) > 0
        if has_files:
            result['reason'] = 'User has uploaded files - must use those instead of internet'
            result['confidence'] = 0.9
            return result

        # Now check if there's a legitimate need for internet
        for pattern in self.LEGITIMATE_INTERNET_NEEDS:
            match = re.search(pattern, user_message, re.IGNORECASE)
            if match:
                # Found a legitimate case - extract specific lookup
                error_text = match.group(0)
                
                result['allowed'] = True
                result['reason'] = f'Specific error lookup required: {error_text}'
                result['confidence'] = 0.8
                result['specific_lookup'] = error_text
                
                # Log the access
                self._log_access(user_message, error_text, 'ALLOWED')
                return result

        # Check if message contains actual error output (stacktrace)
        if self._has_error_stacktrace(user_message):
            result['allowed'] = True
            result['reason'] = 'Error stacktrace detected - documentation lookup may be needed'
            result['confidence'] = 0.7
            result['specific_lookup'] = self._extract_primary_error(user_message)
            self._log_access(user_message, result['specific_lookup'], 'ALLOWED')
            return result

        # Default: FORBIDDEN
        self._log_access(user_message, None, 'DENIED')
        return result

    def _has_error_stacktrace(self, text: str) -> bool:
        """Detect if text contains an error stacktrace"""
        indicators = [
            r"Traceback \(most recent call last\):",
            r"File \".*\", line \d+",
            r"^\s+at\s+\S+\s+\(.*:\d+:\d+\)",  # JS stacktrace
            r"Error: .* at line \d+",
            r"Exception in thread",
        ]
        
        for indicator in indicators:
            if re.search(indicator, text, re.MULTILINE):
                return True
        return False

    def _extract_primary_error(self, text: str) -> Optional[str]:
        """Extract the main error message from stacktrace"""
        # Python errors
        python_match = re.search(r"(\w+Error|Exception): (.+?)(?:\n|$)", text)
        if python_match:
            return f"{python_match.group(1)}: {python_match.group(2)}"
        
        # TypeScript errors
        ts_match = re.search(r"(TS\d{4}): (.+?)(?:\n|$)", text)
        if ts_match:
            return f"{ts_match.group(1)}: {ts_match.group(2)}"
        
        # JavaScript errors
        js_match = re.search(r"(TypeError|ReferenceError|SyntaxError): (.+?)(?:\n|$)", text)
        if js_match:
            return f"{js_match.group(1)}: {js_match.group(2)}"
        
        return None

    def _log_access(self, message: str, lookup: Optional[str], decision: str):
        """Log internet access decisions for audit"""
        self.access_log.append({
            'timestamp': datetime.utcnow().isoformat(),
            'message_preview': message[:100],
            'lookup': lookup,
            'decision': decision,
        })
        
        # Keep only last 100 entries
        if len(self.access_log) > 100:
            self.access_log = self.access_log[-100:]

    def generate_restricted_prompt(self, original_prompt: str, context: Dict) -> str:
        """
        Add internet restriction to system prompt
        """
        restriction = """
CRITICAL INTERNET ACCESS RESTRICTION:
- You are FORBIDDEN from using internet knowledge or making assumptions
- You MUST work ONLY with the uploaded files and code provided
- If you don't have the information in the uploaded files, say "I don't have that information in the uploaded files"
- DO NOT cite documentation, tutorials, or examples from memory
- DO NOT make assumptions about package versions, APIs, or best practices
- If you genuinely encounter an error you cannot solve with uploaded files, you may request specific documentation lookup

FILES AVAILABLE TO YOU:
"""
        
        if context.get('file_count', 0) > 0:
            restriction += f"- {context['file_count']} files uploaded by user\n"
            restriction += "- WORK WITH THESE FILES ONLY\n"
        else:
            restriction += "- NO FILES UPLOADED - you have extremely limited knowledge\n"
            restriction += "- You can only help with very basic syntax questions\n"

        return restriction + "\n" + original_prompt

    def should_block_response(self, response: str) -> Tuple[bool, Optional[str]]:
        """
        Check if AI response appears to use internet knowledge when it shouldn't.
        Returns: (should_block, reason)
        """
        # Check if AI is citing sources it shouldn't know about
        citation_patterns = [
            r"according to (the )?(official )?(documentation|docs|tutorial)",
            r"as mentioned in.*documentation",
            r"from (the )?\w+ docs?:",
            r"see (the )?\w+ documentation for",
            r"as per (the )?\w+ documentation",
            r"based on.*best practices",
            r"it('?s| is) (recommended|advised|best practice) to",
        ]
        
        for pattern in citation_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                return True, f"AI attempted to cite documentation without uploaded files: '{pattern}'"

        # Check if AI is making version assumptions
        version_assumptions = [
            r"in (version|v)\s*\d+\.\d+",
            r"since (version|v)\s*\d+",
            r"as of.*\d{4}",  # temporal references
        ]
        
        for pattern in version_assumptions:
            if re.search(pattern, response, re.IGNORECASE):
                return True, f"AI made version assumptions without uploaded files: '{pattern}'"

        return False, None

    def get_access_stats(self) -> Dict:
        """Get statistics on internet access requests"""
        if not self.access_log:
            return {
                'total_requests': 0,
                'allowed': 0,
                'denied': 0,
                'allow_rate': 0.0
            }
        
        allowed = sum(1 for entry in self.access_log if entry['decision'] == 'ALLOWED')
        denied = sum(1 for entry in self.access_log if entry['decision'] == 'DENIED')
        
        return {
            'total_requests': len(self.access_log),
            'allowed': allowed,
            'denied': denied,
            'allow_rate': allowed / len(self.access_log) if self.access_log else 0.0,
            'recent_lookups': [entry['lookup'] for entry in self.access_log[-5:] if entry['lookup']]
        }


# Global instance
internet_controller = InternetAccessController()


def check_internet_access(user_message: str, context: Dict) -> Dict:
    """
    Main entry point for internet access control.
    Call this before processing any AI request.
    """
    return internet_controller.analyze_request(user_message, context)


def get_restricted_prompt(original_prompt: str, context: Dict) -> str:
    """
    Add internet restrictions to system prompt.
    """
    return internet_controller.generate_restricted_prompt(original_prompt, context)


def validate_response(response: str) -> Tuple[bool, Optional[str]]:
    """
    Validate AI response doesn't violate internet restrictions.
    Returns: (is_valid, violation_reason)
    """
    should_block, reason = internet_controller.should_block_response(response)
    return (not should_block, reason)
