import re
from django.utils import translation
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings

# Whitelist of valid language code patterns: e.g. en, hi, en-AU, en-IN
LANG_CODE_PATTERN = re.compile(r'^[a-zA-Z]{2,3}(-[a-zA-Z0-9]{2,4})?$')
SUPPORTED_LANGUAGES = {'en', 'hi', 'en-au', 'en-in', 'en-AU', 'en-IN'}


def sanitize_language_code(lang_str: str | None) -> str | None:
    if not lang_str:
        return None
    # Strip quality factor like en-US,en;q=0.9
    raw_code = lang_str.split(',')[0].split(';')[0].strip()
    if not LANG_CODE_PATTERN.match(raw_code):
        return None
    normalized = raw_code.lower()
    # Normalize variants
    if normalized in ('en', 'en-us'):
        return 'en'
    if normalized == 'hi':
        return 'hi'
    if normalized == 'en-au':
        return 'en-AU'
    if normalized == 'en-in':
        return 'en-IN'
    return None


class AppLanguageMiddleware(MiddlewareMixin):
    """
    Resolves request language using:
      1. Explicit header: X-App-Language
      2. Authenticated user preference: user.preferred_language
      3. Accept-Language header
      4. Default 'en'
    Ensures safe whitelisting and sets Vary: Accept-Language header on all responses.
    """

    def process_request(self, request):
        chosen_lang = None

        # 1. Check explicit X-App-Language header
        header_lang = request.headers.get('X-App-Language')
        if header_lang:
            chosen_lang = sanitize_language_code(header_lang)

        # 2. Check authenticated user's saved preference
        if not chosen_lang and getattr(request, 'user', None) and request.user.is_authenticated:
            user_pref = getattr(request.user, 'preferred_language', None)
            if user_pref:
                chosen_lang = sanitize_language_code(user_pref)

        # 3. Check browser Accept-Language header
        if not chosen_lang:
            accept_lang = request.headers.get('Accept-Language')
            if accept_lang:
                for candidate in accept_lang.split(','):
                    sanitized = sanitize_language_code(candidate)
                    if sanitized:
                        chosen_lang = sanitized
                        break

        # 4. Fallback to default
        if not chosen_lang:
            chosen_lang = 'en'

        # Map to django language code (django uses lowercase for locale directory matching)
        django_lang = chosen_lang.lower()
        if django_lang in ('en-au', 'en-in'):
            django_lang = 'en'  # django base fallback

        translation.activate(django_lang)
        request.LANGUAGE_CODE = chosen_lang

    def process_response(self, request, response):
        # Add Vary: Accept-Language for proper HTTP caching
        response.headers['Vary'] = 'Accept-Language'
        # Include current active language in header for inspection
        active_lang = getattr(request, 'LANGUAGE_CODE', 'en')
        response.headers['Content-Language'] = active_lang
        return response
