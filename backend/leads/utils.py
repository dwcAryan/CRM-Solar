import re
from typing import Optional
from django.db.models import Q

from .models import Lead
from .phone_utils import normalize_phone_number


def normalize_phone(raw_phone: str, region: str = "IN") -> str:
    """
    Standardizes a phone number to E.164 format (+91..., +61...).
    Returns E.164 if valid, else strips whitespace.
    """
    if not raw_phone:
        return ""
    e164, _, _ = normalize_phone_number(raw_phone, region)
    if e164:
        return e164
    return re.sub(r'[\s\-\(\)]', '', str(raw_phone))


def find_duplicate_lead(phone: str, exclude_id: Optional[int] = None, region: str = "IN") -> Optional[Lead]:
    """
    Finds existing lead matching phone number across regions using E.164.
    Excludes merged leads and optionally a specific lead id.
    """
    if not phone:
        return None

    e164, _, _ = normalize_phone_number(phone, region)
    clean_digits = re.sub(r'\D', '', str(phone))

    qs = Lead.objects.exclude(status=Lead.Status.MERGED)
    if exclude_id:
        qs = qs.exclude(id=exclude_id)

    # 1. Direct indexed match on E.164 if available
    if e164:
        match = qs.filter(Q(phone_e164=e164) | Q(phone=e164)).first()
        if match:
            return match

    # 2. Match raw backup or phone field directly
    if clean_digits and len(clean_digits) >= 8:
        match = qs.filter(
            Q(phone__endswith=clean_digits[-9:]) |
            Q(phone_raw_backup__endswith=clean_digits[-9:])
        ).first()
        if match:
            return match

    return None
