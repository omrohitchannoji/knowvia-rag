"""
Input Security Guardrails & Prompt Injection Detection.
Inspects user input queries before retrieval and LLM generation.
"""

import re
from typing import Tuple, Optional, List
from backend.app.core.logging import logger

# Regex patterns matching known prompt injection, jailbreak, and system override attempts
INJECTION_PATTERNS: List[Tuple[str, str]] = [
    (r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|directives|prompts|rules)", "Direct prompt override attempt"),
    (r"(?i)disregard\s+(all\s+)?(previous|prior)\s+(system|prompts|rules)", "System prompt disregard attempt"),
    (r"(?i)you\s+are\s+now\s+(DAN|unlocked|developer\s+mode|root|god\s+mode)", "Jailbreak persona attempt"),
    (r"(?i)system\s+override", "System override attempt"),
    (r"(?i)(reveal|output|print|show|dump)\s+(the\s+)?(system\s+prompt|system\s+instructions|internal\s+prompt)", "System prompt extraction attempt"),
    (r"(?i)(dump|print|reveal)\s+(all\s+)?(api\s+keys|passwords|admin\s+credentials|secret\s+tokens)", "Credential harvesting attempt"),
    (r"(?i)</?UNTRUSTED_CONTEXT_CHUNKS>", "Security boundary tag injection attempt"),
    (r"(?i)</?system>", "XML System tag injection attempt"),
]

class InputGuardrail:
    """
    Scans user query strings for prompt injection, jailbreak, and system prompt exfiltration threats.
    """
    
    @staticmethod
    def inspect_query(query: str) -> Tuple[bool, Optional[str]]:
        """
        Inspects query string.
        Returns:
            (is_safe: bool, violation_reason: Optional[str])
        """
        if not query or not query.strip():
            return False, "Query string is empty"

        cleaned_query = query.strip()

        for pattern, description in INJECTION_PATTERNS:
            if re.search(pattern, cleaned_query):
                logger.warning(f"Input Guardrail Blocked Query: Pattern matched [{description}] in query: '{query}'")
                return False, f"Security Policy Violation: {description} detected."

        return True, None

    @staticmethod
    def sanitize_query(query: str) -> str:
        """
        Sanitizes user input by escaping hazardous XML/HTML injection tags.
        """
        if not query:
            return ""
        
        # Replace dangerous boundary tag markers
        sanitized = re.sub(r"(?i)</?UNTRUSTED_CONTEXT_CHUNKS>", "", query)
        sanitized = re.sub(r"(?i)</?system>", "", sanitized)
        return sanitized.strip()
