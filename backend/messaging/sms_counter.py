import math
from typing import Dict, Any

# GSM 03.38 Basic Character Set
GSM_BASIC = set(
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ\x1bÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
    "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ`abcdefghijklmnopqrstuvwxyzäöñüà"
)
# GSM 03.38 Extension Table characters (count as 2 septets in GSM-7)
GSM_EXTENDED = set("^{}\\[~]|€")


def is_gsm_text(text: str) -> bool:
    """Check if all characters can be encoded in standard GSM-7 (basic or extended)."""
    return all(c in GSM_BASIC or c in GSM_EXTENDED for c in text)


class SmsCountResult(dict):
    def __getattr__(self, name):
        if name in self:
            return self[name]
        if name == 'segments':
            return self.get('segment_count', 0)
        if name == 'char_count':
            return self.get('character_count', 0)
        if name == 'chars_remaining':
            return self.get('chars_remaining_in_segment', 0)
        if name == 'chars_per_segment':
            # Single segment limit if segments <= 1, else multi-segment limit
            if self.get('segment_count', 0) <= 1:
                return self.get('max_single_segment', 160 if self.get('encoding') == 'GSM-7' else 70)
            return self.get('max_multi', 153 if self.get('encoding') == 'GSM-7' else 67)
        raise AttributeError(name)


def calculate_sms_segments(text: str) -> SmsCountResult:
    """
    Calculate SMS segment count, encoding type, and character limits.
    Standards:
      GSM-7: 160 chars for 1 segment; 153 chars/segment for multi-segment.
      UCS-2 (Unicode e.g. Hindi/Devanagari): 70 chars for 1 segment; 67 chars/segment for multi-segment.
    """
    if not text:
        return SmsCountResult({
            'character_count': 0,
            'segment_count': 0,
            'encoding': 'GSM-7',
            'is_unicode': False,
            'max_single_segment': 160,
            'chars_remaining_in_segment': 160,
            'warning': None,
        })

    is_gsm = is_gsm_text(text)

    if is_gsm:
        # Extended chars count as 2
        effective_len = sum(2 if c in GSM_EXTENDED else 1 for c in text)
        encoding = 'GSM-7'
        is_unicode = False
        max_single = 160
        max_multi = 153
    else:
        effective_len = len(text)
        encoding = 'UCS-2'
        is_unicode = True
        max_single = 70
        max_multi = 67

    if effective_len <= max_single:
        segment_count = 1
        chars_remaining = max_single - effective_len
    else:
        segment_count = math.ceil(effective_len / max_multi)
        chars_remaining = (segment_count * max_multi) - effective_len

    warning = None
    if is_unicode and segment_count > 1:
        warning = f"Message contains Unicode characters ({encoding}). Multi-segment messages use 67 characters per segment."
    elif segment_count > 3:
        warning = f"Long message ({segment_count} segments). Carrier charges may apply per segment."

    return SmsCountResult({
        'character_count': len(text),
        'effective_length': effective_len,
        'segment_count': segment_count,
        'encoding': encoding,
        'is_unicode': is_unicode,
        'max_single_segment': max_single,
        'max_multi': max_multi,
        'chars_remaining_in_segment': chars_remaining,
        'warning': warning,
    })
