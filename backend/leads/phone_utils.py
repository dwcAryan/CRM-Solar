import re
import urllib.parse
from typing import Optional, Tuple

import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberFormat


def normalize_phone_number(
    raw_phone: str,
    default_region: str = "IN",
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Parses, validates, and standardizes a phone number for India or Australia.
    Returns:
        (e164_number, formatted_display, error_message)
        If valid: (e164_str, display_str, None)
        If invalid: (None, None, error_str)
    """
    if not raw_phone or not str(raw_phone).strip():
        return None, None, "Phone number is required."

    raw_phone = str(raw_phone).strip()
    region_code = (default_region or "IN").upper()

    # Pre-clean obvious spacing / formatting artifacts
    clean_digits = re.sub(r'[^\d+]', '', raw_phone)

    # Specific quick pre-checks for common user mistakes
    try:
        parsed = phonenumbers.parse(clean_digits, region_code)
    except NumberParseException as e:
        if region_code == "IN":
            return None, None, f"Invalid phone format: Must normalize to 10 digits ({e._msg})."
        return None, None, f"Invalid phone format: {e._msg}"

    if not phonenumbers.is_valid_number(parsed):
        # Give country-specific actionable error messages
        num_region = phonenumbers.region_code_for_number(parsed) or region_code
        if num_region == "AU":
            return (
                None,
                None,
                "Invalid Australian phone number. Mobile numbers should be 10 digits starting with 04 (e.g. 0412 345 678) or landlines with area code (02, 03, 07, 08).",
            )
        elif num_region == "IN":
            return (
                None,
                None,
                "Invalid Indian phone number. Must normalize to 10 digits starting with 6, 7, 8, or 9 (e.g. 98765 43210).",
            )
        else:
            return None, None, f"Phone number is not valid for region {num_region}."

    # Valid! Format as E.164 and as formatted display with country code
    e164_str = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
    # International format has country code: "+91 98765 43210" or "+61 412 345 678"
    display_str = phonenumbers.format_number(parsed, PhoneNumberFormat.INTERNATIONAL)

    return e164_str, display_str, None


def get_whatsapp_url(e164_phone: str, message: str = "") -> str:
    """Generates direct wa.me link using clean digits without '+'."""
    digits = re.sub(r'\D', '', e164_phone or "")
    if not digits:
        return ""
    base = f"https://wa.me/{digits}"
    if message:
        return f"{base}?text={urllib.parse.quote(message)}"
    return base


def get_tel_url(e164_phone: str) -> str:
    """Generates standard tel: URL with E.164 string."""
    if not e164_phone:
        return ""
    return f"tel:{e164_phone.strip()}"
