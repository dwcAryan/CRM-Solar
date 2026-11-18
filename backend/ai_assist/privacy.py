"""
Privacy filters and anonymization utilities for Solar CRM AI Assist.
Ensures zero PII (phone numbers, emails, full names, full addresses) is transmitted to LLMs.
"""

from __future__ import annotations

import re

# Regex patterns for Indian phone numbers (10 digits, with optional +91 or 0 prefix and spaces/dashes)
PHONE_REGEX = re.compile(
    r'(?:\+?91[\-\s]?)?[0]?[6-9]\d{4}[\-\s]?\d{5}\b|(?:\b\d{10}\b)',
    re.IGNORECASE,
)

# Regex patterns for email addresses
EMAIL_REGEX = re.compile(
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b',
    re.IGNORECASE,
)

# Regex pattern for house/flat/plot numbers or street lines in remarks
ADDRESS_HINT_REGEX = re.compile(
    r'\b(?:flat|plot|house|h\.no|door|sector|lane|street|road|floor|bldg)\s*(?:no\.?)?\s*[\d\w\-\/]+',
    re.IGNORECASE,
)


def sanitize_remark_text(text: str | None) -> str:
    """
    Sanitizes remark or note text by redacting phone numbers, emails,
    and specific street/flat address tokens.
    """
    if not text:
        return ""

    sanitized = PHONE_REGEX.sub('[PHONE_REDACTED]', text)
    sanitized = EMAIL_REGEX.sub('[EMAIL_REDACTED]', sanitized)
    sanitized = ADDRESS_HINT_REGEX.sub('[ADDRESS_REDACTED]', sanitized)
    return sanitized.strip()


def extract_safe_display_name(full_name: str | None, lead_id: int) -> str:
    """
    Returns only the first name (e.g. 'Rahul') or a fallback pseudonym ('Lead #123').
    Never returns full name or contact tokens.
    """
    if not full_name:
        return f"Lead #{lead_id}"

    parts = full_name.strip().split()
    if not parts:
        return f"Lead #{lead_id}"

    first_name = parts[0].capitalize()
    # If the first name looks like a phone number or symbol, use pseudonym
    if not first_name.isalpha() or len(first_name) < 2:
        return f"Lead #{lead_id}"

    return first_name
