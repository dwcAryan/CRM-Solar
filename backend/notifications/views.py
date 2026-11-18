from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from accounts.permissions import can

from .email_service import run_smtp_diagnostics, send_test_email
from .models import EmailLog, Notification, NotificationPreference, PushSubscription
from .serializers import (
    EmailLogSerializer,
    NotificationPreferenceSerializer,
    NotificationSerializer,
    PushSubscriptionSerializer,
)


class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all().order_by('-created_at')
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['is_read']
    ordering_fields = ['created_at', 'id']

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Notification.objects.none()
        return Notification.objects.filter(user=user)

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response(NotificationSerializer(notification).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        updated_count = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response(
            {"message": f"{updated_count} notifications marked as read.", "count": updated_count},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({"unread_count": count}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='vapid-public-key')
    def vapid_public_key(self, request):
        """Returns VAPID public key for web push subscription."""
        pub_key = getattr(settings, 'VAPID_PUBLIC_KEY', '')
        return Response({"public_key": pub_key}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='push-subscribe')
    def push_subscribe(self, request):
        """Registers or updates a Web Push subscription for the authenticated user."""
        serializer = PushSubscriptionSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"status": "subscribed", "endpoint": serializer.data.get('endpoint')},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='push-unsubscribe')
    def push_unsubscribe(self, request):
        """Removes a Web Push subscription for the authenticated user."""
        endpoint = request.data.get('endpoint')
        if not endpoint:
            return Response({"error": "endpoint is required"}, status=status.HTTP_400_BAD_REQUEST)
        deleted_count, _ = PushSubscription.objects.filter(user=request.user, endpoint=endpoint).delete()
        return Response({"status": "unsubscribed", "deleted": deleted_count}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get', 'put', 'patch'], url_path='preferences')
    def preferences(self, request):
        """Get or update notification delivery and quiet hours preferences for the authenticated user."""
        pref, _ = NotificationPreference.objects.get_or_create(user=request.user)
        if request.method in ('PUT', 'PATCH'):
            serializer = NotificationPreferenceSerializer(
                pref,
                data=request.data,
                partial=(request.method == 'PATCH'),
            )
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer = NotificationPreferenceSerializer(pref)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='email-settings')
    def email_settings(self, request):
        """Admin-only endpoint returning active SMTP configuration, connection status, and last 50 email logs."""
        if not request.user.is_superuser and getattr(request.user, 'role', '') != 'admin' and not can(request.user, 'policy.manage'):
            return Response({"error": "Admin permission required to access email settings."}, status=status.HTTP_403_FORBIDDEN)

        raw_pw = getattr(settings, 'EMAIL_HOST_PASSWORD', '')
        masked_pw = ("*" * len(raw_pw)) if raw_pw else ""

        config_data = {
            "backend": getattr(settings, 'EMAIL_BACKEND', ''),
            "host": getattr(settings, 'EMAIL_HOST', ''),
            "port": getattr(settings, 'EMAIL_PORT', 587),
            "use_tls": getattr(settings, 'EMAIL_USE_TLS', False),
            "use_ssl": getattr(settings, 'EMAIL_USE_SSL', False),
            "host_user": getattr(settings, 'EMAIL_HOST_USER', ''),
            "host_password_masked": masked_pw,
            "default_from_email": getattr(settings, 'DEFAULT_FROM_EMAIL', ''),
            "timeout": getattr(settings, 'EMAIL_TIMEOUT', 15),
        }

        diagnostics = run_smtp_diagnostics()
        recent_logs = EmailLog.objects.select_related('related_lead').all().order_by('-created_at')[:50]

        return Response({
            "settings": config_data,
            "diagnostics": diagnostics,
            "logs": EmailLogSerializer(recent_logs, many=True).data,
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='email-test')
    def email_test(self, request):
        """Admin-only endpoint to dispatch a live test email and report exact delivery outcome."""
        if not request.user.is_superuser and getattr(request.user, 'role', '') != 'admin' and not can(request.user, 'policy.manage'):
            return Response({"error": "Admin permission required to send test email."}, status=status.HTTP_403_FORBIDDEN)

        to_email = request.data.get('to') or request.user.email
        if not to_email:
            return Response({"error": "Recipient email address ('to') is required."}, status=status.HTTP_400_BAD_REQUEST)

        log = send_test_email(to_email=to_email, user=request.user)
        if log.status == EmailLog.Status.SENT:
            return Response({
                "status": "sent",
                "message": f"Test email successfully sent to {to_email}.",
                "log": EmailLogSerializer(log).data,
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "status": "failed",
                "error": log.error or "Failed to deliver test email.",
                "log": EmailLogSerializer(log).data,
            }, status=status.HTTP_400_BAD_REQUEST)

