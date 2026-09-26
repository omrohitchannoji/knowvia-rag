"""
Output Security Guardrails & Secret Redaction.
Scans generated LLM outputs to prevent leakage of credentials, tokens, or PII.
"""

import re
from typing import Tuple, List
from backend.app.core.logging import logger

REDACTION_MARKER = "[REDACTED_SECRET]"

# Regex patterns identifying confidential secret tokens and key material
SECRET_PATTERNS: List[Tuple[str, str]] = [
    (r"\b(AKIA|ASIA)[0-9A-Z]{16}\b", "AWS Access Key ID"),
    (r"\b(sk-[a-zA-Z0-9]{20,64})\b", "API Token (sk-...)"),
    (r"\b(prod_secret_[a-zA-Z0-9]{12,64})\b", "Internal Secret Key"),
    (r"\beyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\b", "JWT Token"),
    (r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END \1PRIVATE KEY-----", "Private Key Header"),
    (r"(?i)(password|secret|api_key|access_token)\s*[:=]\s*[\"']?([a-zA-Z0-9_\-\$!@#%^&*]{8,})[\"']?", "Plaintext Credential Assignment")
]

class OutputGuardrail:
    """
    Scans LLM output text and redacts sensitive credentials or token leakages before sending to the client.
    """

    @staticmethod
    def redact_secrets(text: str) -> Tuple[str, bool]:
        """
        Scans and replaces matched secret tokens with [REDACTED_SECRET].
        
        Returns:
            Tuple[str, bool]: (redacted_text, secrets_detected)
        """
        if not text:
            return text, False

        redacted_text = text
        secrets_detected = False

        for pattern, label in SECRET_PATTERNS:
            matches = re.findall(pattern, redacted_text)
            if matches:
                secrets_detected = True
                logger.warning(f"Output Guardrail: Leakage prevented for pattern [{label}]. Redacting...")
                
                # For tuple matches from regex capture groups, handle properly
                if isinstance(matches[0], tuple):
                    # Replace full match
                    def replace_func(match):
                        return match.group(0).replace(match.group(2), REDACTION_MARKER) if len(match.groups()) >= 2 else REDACTION_MARKER
                    redacted_text = re.sub(pattern, replace_func, redacted_text)
                else:
                    redacted_text = re.sub(pattern, REDACTION_MARKER, redacted_text)

        return redacted_text, secrets_detected
