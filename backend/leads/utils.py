import re
from typing import Optional

from .models import Lead


def normalize_phone(raw_phone: str) -> str:
    """
    Normalizes Indian phone numbers:
    - Strips whitespace, dashes, plus signs, brackets.
    - Strips '+91' or '91' prefix for 12-digit formats.
    - Strips leading '0' for 11-digit formats.
    Returns cleaned phone number (typically 10 digits).
    """
    if not raw_phone:
        return ""

    cleaned = re.sub(r'[\s\+\-\(\)]', '', str(raw_phone))

    if len(cleaned) == 12 and cleaned.startswith('91'):
        cleaned = cleaned[2:]
    elif len(cleaned) == 11 and cleaned.startswith('0'):
        cleaned = cleaned[1:]

    return cleaned


def find_duplicate_lead(phone: str, exclude_id: Optional[int] = None) -> Optional[Lead]:
    """
    Finds existing lead matching the normalized phone number,
    excluding merged leads and optionally a specific lead id.
    """
    normalized = normalize_phone(phone)
    if not normalized or len(normalized) < 10:
        return None

    # Query leads that end with the normalized phone or match exactly
    qs = Lead.objects.exclude(status=Lead.Status.MERGED)
    if exclude_id:
        qs = qs.exclude(id=exclude_id)

    # Search for leads with matching normalized phone
    for lead in qs.iterator():
        if normalize_phone(lead.phone) == normalized:
            return lead
    return None
