import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.email_service import send_password_reset_email

logger = logging.getLogger(__name__)
User = get_user_model()


class PasswordResetRequestView(APIView):
    """
    Initiates password reset by issuing a single-use token expiring in 1 hour.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        if not email:
            return Response({"error": "Email address is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Look up active user(s) with this email
        users = User.objects.filter(email__iexact=email, is_active=True)
        frontend_origin = request.headers.get('Origin') or 'http://localhost:5173'

        for user in users:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = f"{frontend_origin}/reset-password?uid={uid}&token={token}"

            try:
                send_password_reset_email(user, reset_url)
            except Exception as e:
                logger.error(f"Failed to deliver password reset email to {email}: {e}")

        # Always return 200 to protect against user enumeration
        return Response(
            {
                "message": "If an account with this email address exists, a password reset link has been dispatched.",
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """
    Validates single-use token (1-hour window) and sets a new password.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        uidb64 = request.data.get('uid', '').strip()
        token = request.data.get('token', '').strip()
        new_password = request.data.get('new_password', '').strip()

        if not uidb64 or not token or not new_password:
            return Response(
                {"error": "uid, token, and new_password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(new_password) < 6:
            return Response(
                {"error": "Password must be at least 6 characters long."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid, is_active=True)
        except Exception:
            return Response(
                {"error": "Invalid or expired password reset link."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify token validity and 1-hour expiration
        if not default_token_generator.check_token(user, token):
            return Response(
                {"error": "Invalid or expired password reset token. Tokens expire in 1 hour and can only be used once."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save()

        logger.info(f"Password successfully reset for user {user.username} via reset token.")
        return Response(
            {"message": "Your password has been successfully reset. You may now log in."},
            status=status.HTTP_200_OK,
        )
