from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdmin

from .help_service import get_faq_list, query_help_assistant
from .models import (
    LeadSource,
    LostReason,
    NurtureReason,
    Outcome,
    PolicySettings,
    PropertyType,
    PublicHoliday,
    Region,
    RoofType,
    State,
)
from .serializers import (
    LeadSourceSerializer,
    LostReasonSerializer,
    NurtureReasonSerializer,
    OutcomeSerializer,
    PolicySettingsSerializer,
    PropertyTypeSerializer,
    PublicHolidaySerializer,
    RegionSerializer,
    RoofTypeSerializer,
    StateSerializer,
)


class RegionViewSet(viewsets.ModelViewSet):
    queryset = Region.objects.all().order_by('sort_order', 'code')
    serializer_class = RegionSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active', 'calling_hours_policy', 'currency']
    search_fields = ['code', 'name', 'currency', 'default_timezone']
    ordering_fields = ['sort_order', 'code', 'name']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdmin()]
        return [permissions.IsAuthenticated()]


class StateViewSet(viewsets.ModelViewSet):
    queryset = State.objects.all().order_by('region', 'sort_order', 'name')
    serializer_class = StateSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['region', 'is_active']
    search_fields = ['code', 'name', 'default_timezone']
    ordering_fields = ['sort_order', 'name', 'code']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdmin()]
        return [permissions.IsAuthenticated()]


class PublicHolidayViewSet(viewsets.ModelViewSet):
    queryset = PublicHoliday.objects.all().order_by('region', 'date')
    serializer_class = PublicHolidaySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['region', 'date']
    search_fields = ['name']
    ordering_fields = ['date', 'name']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdmin()]
        return [permissions.IsAuthenticated()]


class RoofTypeViewSet(viewsets.ModelViewSet):
    queryset = RoofType.objects.all().order_by('region', 'sort_order', 'name')
    serializer_class = RoofTypeSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['region', 'is_active']
    search_fields = ['name']
    ordering_fields = ['sort_order', 'name']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdmin()]
        return [permissions.IsAuthenticated()]


class PropertyTypeViewSet(viewsets.ModelViewSet):
    queryset = PropertyType.objects.all().order_by('region', 'sort_order', 'name')
    serializer_class = PropertyTypeSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['region', 'is_active']
    search_fields = ['name']
    ordering_fields = ['sort_order', 'name']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdmin()]
        return [permissions.IsAuthenticated()]


class OutcomeViewSet(viewsets.ModelViewSet):
    queryset = Outcome.objects.all().order_by('stage', 'sort_order', 'id')
    serializer_class = OutcomeSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['stage', 'is_terminal', 'is_active', 'requires_lost_reason', 'requires_nurture_reason']
    search_fields = ['name', 'default_status', 'default_next_action']
    ordering_fields = ['sort_order', 'id', 'name', 'stage']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdmin()]
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
            return [IsAdmin()]
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
            return [IsAdmin()]
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
            return [IsAdmin()]
        return [permissions.IsAuthenticated()]


class PolicySettingsViewSet(viewsets.ModelViewSet):
    queryset = PolicySettings.objects.all()
    serializer_class = PolicySettingsSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdmin()]
        return [permissions.IsAuthenticated()]


class HelpQueryView(APIView):
    """
    Endpoint for querying the Solar CRM in-app assistant regarding
    system policies, workflows, retry rules, and features.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        query = request.data.get('query', '').strip()
        if not query:
            return Response(
                {"error": "Query string is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        result = query_help_assistant(query)
        return Response(result, status=status.HTTP_200_OK)


class HelpFaqListView(APIView):
    """
    Returns grouped list of available frequently asked questions and guides.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        faqs = get_faq_list()
        return Response({"faqs": faqs}, status=status.HTTP_200_OK)
