from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from .models import Notification, NotificationPreference, PushSubscription
from .serializers import (
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
