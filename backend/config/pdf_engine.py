"""
Centralized PDF Engine & Utilities for Solar CRM (Phase 14M).
Ensures:
1. Standard A4 pagesize across all generated documents.
2. Robust Unicode / TrueType font embedding (Nirmala UI / Arial / DejaVuSans)
   preventing tofu on non-ASCII characters (e.g. ₹, A$, Hindi names/notes).
3. Concurrency limiting (max 2 parallel renders) with a hard 15s timeout.
4. RFC 5987 compliant Content-Disposition filename formatting.
"""
import logging
import os
import threading
from urllib.parse import quote

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger(__name__)

# Concurrency limiting: max 2 simultaneous renders
_RENDER_SEMAPHORE = threading.Semaphore(2)

_font_lock = threading.Lock()
_registered_font_name = 'Helvetica'
_registered_bold_font_name = 'Helvetica-Bold'


def ensure_unicode_fonts() -> tuple[str, str]:
    """
    Registers a TrueType font that supports Unicode, Currency symbols (₹, A$),
    and Indic scripts (Devanagari/Hindi). Falls back cleanly to Helvetica if unavailable.
    """
    global _registered_font_name, _registered_bold_font_name

    with _font_lock:
        if _registered_font_name != 'Helvetica':
            return _registered_font_name, _registered_bold_font_name

        candidates_regular = [
            'C:/Windows/Fonts/Nirmala.ttf',
            'C:/Windows/Fonts/arial.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/freefont/FreeSans.ttf',
        ]
        candidates_bold = [
            'C:/Windows/Fonts/NirmalaB.ttf',
            'C:/Windows/Fonts/arialbd.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf',
        ]

        found_regular = None
        for path in candidates_regular:
            if os.path.exists(path):
                found_regular = path
                break

        found_bold = None
        for path in candidates_bold:
            if os.path.exists(path):
                found_bold = path
                break

        if found_regular:
            try:
                pdfmetrics.registerFont(TTFont('AppUnicode', found_regular))
                _registered_font_name = 'AppUnicode'
                if found_bold:
                    pdfmetrics.registerFont(TTFont('AppUnicodeBold', found_bold))
                    _registered_bold_font_name = 'AppUnicodeBold'
                else:
                    _registered_bold_font_name = 'AppUnicode'
            except Exception as e:
                logger.warning(f"Could not register font {found_regular}: {e}")

        return _registered_font_name, _registered_bold_font_name


class RenderSlotContext:
    """
    Context manager to enforce maximum 2 concurrent renders with a 15-second timeout.
    """
    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout
        self.acquired = False

    def __enter__(self):
        self.acquired = _RENDER_SEMAPHORE.acquire(timeout=self.timeout)
        if not self.acquired:
            raise TimeoutError("PDF rendering engine busy (concurrency limit reached). Please retry.")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.acquired:
            _RENDER_SEMAPHORE.release()


def format_rfc5987_content_disposition(filename: str) -> str:
    """
    Constructs an RFC 5987 compliant Content-Disposition header.
    Handles non-ASCII characters, quotes, and spaces safely.
    Example output:
    attachment; filename="safe_ascii.pdf"; filename*=UTF-8''encoded%20name.pdf
    """
    import re
    raw_ascii = "".join(c if (c.isascii() and (c.isalnum() or c in ".-")) else "_" for c in filename)
    safe_ascii = re.sub(r'_+', '_', raw_ascii).strip('_') or "document.pdf"
    if not safe_ascii.endswith('.pdf'):
        safe_ascii += '.pdf'
    encoded = quote(filename)
    return f'attachment; filename="{safe_ascii}"; filename*=UTF-8\'\'{encoded}'
