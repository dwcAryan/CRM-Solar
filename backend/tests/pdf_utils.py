"""
Shared PDF Test Harness (Phase 14M).
Validates PDF properties including A4 size, extractable text (including non-ASCII,
currency symbols and Hindi), font embedding, non-empty pages, and response caching.
"""
import io
import re
from urllib.parse import unquote
import pypdf
from reportlab.lib.pagesizes import A4


def assert_pdf_valid(
    pdf_bytes: bytes,
    expected_substrings: list[str] | None = None,
    expected_page_count: int | None = None,
    check_a4: bool = True,
    check_fonts_embedded: bool = False,
    check_non_empty_pages: bool = True,
) -> pypdf.PdfReader:
    """
    Asserts structural correctness of generated PDF bytes.
    """
    assert isinstance(pdf_bytes, (bytes, bytearray)), "PDF content must be bytes"
    assert pdf_bytes.startswith(b"%PDF-"), "File must start with %PDF- magic bytes"
    assert len(pdf_bytes) > 200, "PDF must not be truncated"

    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    page_count = len(reader.pages)
    assert page_count >= 1, "PDF must have at least one page"

    if expected_page_count is not None:
        assert page_count == expected_page_count, f"Expected {expected_page_count} pages, got {page_count}"

    full_text = ""
    for i, page in enumerate(reader.pages):
        # 1. Check A4 dimensions (595.28 x 841.89 points)
        if check_a4:
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            assert abs(width - A4[0]) < 3.0, f"Page {i+1} width {width} does not match A4 ({A4[0]})"
            assert abs(height - A4[1]) < 3.0, f"Page {i+1} height {height} does not match A4 ({A4[1]})"

        page_text = page.extract_text() or ""
        full_text += "\n" + page_text

        # 2. Check no completely blank pages
        if check_non_empty_pages:
            assert len(page_text.strip()) > 0, f"Page {i+1} is completely blank (no extractable text)"

        # 3. Check font embedding if requested
        if check_fonts_embedded:
            resources = page.get('/Resources', {})
            fonts = resources.get('/Font', {})
            for font_id, font_obj in fonts.items():
                base_font = str(font_obj.get('/BaseFont', ''))
                # TrueType fonts in ReportLab have subset prefix (e.g. /AAAAAA+...) or descriptor
                desc = font_obj.get('/FontDescriptor')
                if desc:
                    has_font_file = bool(desc.get('/FontFile') or desc.get('/FontFile2') or desc.get('/FontFile3'))
                    assert has_font_file or 'Helvetica' in base_font or 'Times' in base_font, (
                        f"Font {base_font} is not embedded"
                    )

    # 4. Check expected substrings (supports non-ASCII like ₹, A$, Hindi characters)
    if expected_substrings:
        for sub in expected_substrings:
            assert sub in full_text, f"Expected substring '{sub}' was not found in extracted PDF text"

    return reader


def assert_private_pdf_response(response, expected_filename_substr: str | None = None) -> bytes:
    """
    Asserts that a Django / DRF HTTP response is an authenticated, private, non-cached PDF
    with RFC 5987 compliant Content-Disposition.
    """
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
    assert response['Content-Type'] == 'application/pdf', f"Expected application/pdf, got {response['Content-Type']}"

    # Cache-Control: must be private, no-store
    cc = response.get('Cache-Control', '').lower()
    assert 'no-store' in cc, f"Cache-Control must contain 'no-store': {cc}"
    assert 'private' in cc, f"Cache-Control must contain 'private': {cc}"

    # RFC 5987 Content-Disposition
    cd = response.get('Content-Disposition', '')
    assert 'attachment' in cd, f"Content-Disposition must be attachment: {cd}"

    if expected_filename_substr:
        assert expected_filename_substr in cd, f"Expected '{expected_filename_substr}' in Content-Disposition"

    # Verify RFC 5987 encoding if filename* is present
    if "filename*=" in cd:
        match = re.search(r"filename\*=UTF-8''([^;\s]+)", cd)
        assert match, f"filename*= was present but not valid RFC 5987: {cd}"
        decoded_name = unquote(match.group(1))
        assert len(decoded_name) > 0, "Decoded filename must not be empty"

    content = response.content if hasattr(response, 'content') else b"".join(response.streaming_content)
    assert_pdf_valid(content)
    return content
