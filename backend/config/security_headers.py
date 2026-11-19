from django.utils.deprecation import MiddlewareMixin
from django.conf import settings


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Enforces modern defensive HTTP security headers:
    - Content-Security-Policy (CSP)
    - X-Content-Type-Options: nosniff
    - Referrer-Policy
    - Permissions-Policy
    """

    def process_response(self, request, response):
        if 'Content-Security-Policy' not in response.headers:
            csp = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' http://localhost:5173 http://localhost:8000 http://127.0.0.1:5173 http://127.0.0.1:8000 ws://localhost:5173 ws://127.0.0.1:5173; "
                "frame-ancestors 'none'; "
                "base-uri 'self';"
            )
            response.headers['Content-Security-Policy'] = csp

        if 'X-Content-Type-Options' not in response.headers:
            response.headers['X-Content-Type-Options'] = 'nosniff'

        if 'Referrer-Policy' not in response.headers:
            response.headers['Referrer-Policy'] = 'same-origin'

        if 'Permissions-Policy' not in response.headers:
            response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=(self)'

        return response
