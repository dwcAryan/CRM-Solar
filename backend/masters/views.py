from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from accounts.permissions import IsAdminOrManager

from .models import LeadSource, LostReason, NurtureReason, Outcome, PolicySettings
from .serializers import (
    LeadSourceSerializer,
    LostReasonSerializer,
    NurtureReasonSerializer,
    OutcomeSerializer,
    PolicySettingsSerializer,
)


class OutcomeViewSet(viewsets.ModelViewSet):
    queryset = Outcome.objects.all().order_by('stage', 'sort_order', 'id')
    serializer_class = OutcomeSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['stage', 'is_terminal', 'is_active', 'requires_lost_reason', 'requires_nurture_reason']
    search_fields = ['name', 'default_status', 'default_next_action']
    ordering_fields = ['sort_order', 'id', 'name', 'stage']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminOrManager()]
        return [permissions.IsAuthenticated()]


class LostReasonViewSet(viewsets.ModelViewSet):
    queryset = LostReason.objects.all().order_by('sort_order', 'name')
    serializer_class = LostReasonSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name']
    ordering_fields = ['sort_order', 'name', 'id']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminOrManager()]
        return [permissions.IsAuthenticated()]


class NurtureReasonViewSet(viewsets.ModelViewSet):
    queryset = NurtureReason.objects.all().order_by('sort_order', 'name')
    serializer_class = NurtureReasonSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name']
    ordering_fields = ['sort_order', 'name', 'id']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminOrManager()]
        return [permissions.IsAuthenticated()]


class LeadSourceViewSet(viewsets.ModelViewSet):
    queryset = LeadSource.objects.all().order_by('sort_order', 'name')
    serializer_class = LeadSourceSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name']
    ordering_fields = ['sort_order', 'name', 'id']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminOrManager()]
        return [permissions.IsAuthenticated()]


class PolicySettingsViewSet(viewsets.ModelViewSet):
    queryset = PolicySettings.objects.all()
    serializer_class = PolicySettingsSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminOrManager()]
        return [permissions.IsAuthenticated()]
