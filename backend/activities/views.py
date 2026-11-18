from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from accounts.models import User
from accounts.permissions import DynamicRBACPermission, can

from .models import Activity
from .serializers import ActivitySerializer


class ActivityViewSet(viewsets.ModelViewSet):
    queryset = Activity.objects.all().select_related('lead', 'outcome', 'created_by', 'correction_added_by').order_by('-created_at')
    serializer_class = ActivitySerializer
    permission_classes = [DynamicRBACPermission]
    permission_map = {
        'list': 'activity.view',
        'retrieve': 'activity.view',
        'create': 'activity.log',
        'add_correction': 'activity.correct',
    }
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['lead', 'type', 'created_by', 'status_after']
    search_fields = ['notes', 'next_action', 'lead__name', 'lead__phone']
    ordering_fields = ['created_at', 'id']

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if not user.is_authenticated:
            return qs.none()
        if not can(user, 'activity.view'):
            return qs.none()
        if not user.is_superuser:
            qs = qs.filter(lead__region__in=user.allowed_regions.all())
        if user.role == User.Role.SALESPERSON and not user.is_superuser:
            return qs.filter(lead__assigned_to=user)

        region_param = self.request.query_params.get('region')
        if region_param:
            qs = qs.filter(lead__region_id=region_param.upper().strip())
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def update(self, request, *args, **kwargs):
        raise PermissionDenied("Activities are immutable and cannot be updated.")

    def partial_update(self, request, *args, **kwargs):
        raise PermissionDenied("Activities are immutable and cannot be updated.")

    def destroy(self, request, *args, **kwargs):
        raise PermissionDenied("Activities are immutable and cannot be deleted.")

    @action(detail=True, methods=['post'], url_path='add-correction')
    def add_correction(self, request, pk=None):
        activity = self.get_object()
        if not can(request.user, 'activity.correct'):
            raise PermissionDenied("Only administrators can add correction notes to activities.")
        note = request.data.get('admin_correction_note', '').strip()
        if not note:
            return Response(
                {"admin_correction_note": "A correction note is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        activity.admin_correction_note = note
        activity.correction_added_by = request.user
        activity.correction_added_at = timezone.now()
        activity.save(update_fields=['admin_correction_note', 'correction_added_by', 'correction_added_at'])
        return Response(ActivitySerializer(activity).data, status=status.HTTP_200_OK)
