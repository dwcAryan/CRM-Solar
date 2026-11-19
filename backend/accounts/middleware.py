from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.authentication import JWTAuthentication


class MustChangePasswordMiddleware(MiddlewareMixin):
    """
    Enforces forced password change for accounts created by an admin or flagged with must_change_password=True.
    Until the password is changed via /api/auth/change-password/, all other CRM action requests return 403 Forbidden.
    """
    EXEMPT_PATHS = [
        '/api/auth/change-password/',
        '/api/auth/password-reset/',
        '/api/auth/password-reset/confirm/',
        '/api/token/',
        '/api/token/refresh/',
        '/api/auth/logout/',
        '/api/me/',
        '/api/health/',
        '/api/schema/',
        '/api/docs/',
        '/admin/',
        '/static/',
        '/media/',
    ]

    def process_view(self, request, view_func, view_args, view_kwargs):
        path = request.path_info
        if any(path.startswith(exempt) for exempt in self.EXEMPT_PATHS):
            return None

        user = getattr(request, '_force_auth_user', None) or getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            # Check for JWT Bearer token in headers if user is not yet populated by session
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                try:
                    jwt_auth = JWTAuthentication()
                    validated_token = jwt_auth.get_validated_token(auth_header.split(' ')[1])
                    user = jwt_auth.get_user(validated_token)
                except Exception:
                    return None

        if user and getattr(user, 'is_authenticated', False):
            if getattr(user, 'must_change_password', False):
                return JsonResponse(
                    {
                        "detail": "Password change is required before performing any actions.",
                        "error": "Password change is required before performing any actions.",
                        "code": "password_change_required",
                        "must_change_password": True,
                    },
                    status=403,
                )

        return None
