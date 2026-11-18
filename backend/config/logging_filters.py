import logging
import re


class SensitiveDataFilter(logging.Filter):
    """
    Scrubs passwords, secrets, tokens, API keys, and phone numbers from all log entries.
    """
    PATTERNS = [
        (re.compile(r'(?i)\bpassword\b\s*[:=]\s*["\']?[^"\'\s,]+'), 'password=[REDACTED]'),
        (re.compile(r'(?i)\bsecret\b\s*[:=]\s*["\']?[^"\'\s,]+'), 'secret=[REDACTED]'),
        (re.compile(r'(?i)\btoken\b\s*[:=]\s*["\']?[^"\'\s,]+'), 'token=[REDACTED]'),
        (re.compile(r'(?i)\bapi[_-]?key\b\s*[:=]\s*["\']?[^"\'\s,]+'), 'api_key=[REDACTED]'),
        (re.compile(r'(?i)\b(?:bearer\s+)[A-Za-z0-9\-._~+/]+=*'), 'Bearer [REDACTED]'),
        (re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'), '[PHONE_REDACTED]'),
    ]

    def filter(self, record):
        if isinstance(record.msg, str):
            for pattern, replacement in self.PATTERNS:
                record.msg = pattern.sub(replacement, record.msg)
        return True
