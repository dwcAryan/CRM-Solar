from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from accounts.models import User

from .models import Activity
from .serializers import ActivitySerializer


class ActivityViewSet(viewsets.ModelViewSet):
    queryset = Activity.objects.all().select_related('lead', 'outcome', 'created_by').order_by('-created_at')
    serializer_class = ActivitySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['lead', 'type', 'created_by', 'status_after']
    search_fields = ['notes', 'next_action', 'lead__name', 'lead__phone']
    ordering_fields = ['created_at', 'id']

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if not user.is_authenticated:
            return qs.none()
        if user.role == User.Role.SALESPERSON and not user.is_superuser:
            return qs.filter(lead__assigned_to=user)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
