from datetime import timedelta

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from accounts.models import User
from accounts.permissions import can_user_mark_lost
from activities.models import Activity
from leads.models import Lead, LeadStatusHistory
from masters.models import LostReason, Outcome

from .models import Quote
from .serializers import (
    CreateQuoteInputSerializer,
    QuoteSerializer,
    RejectQuoteInputSerializer,
    ReviseQuoteInputSerializer,
)


class QuoteViewSet(viewsets.ModelViewSet):
    queryset = Quote.objects.all().select_related('lead', 'created_by').order_by('lead', '-version')
    serializer_class = QuoteSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['lead', 'status', 'brand']
    search_fields = ['lead__name', 'lead__phone', 'brand', 'notes']
    ordering_fields = ['version', 'price', 'created_at', 'id']

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if not user.is_authenticated:
            return qs.none()
        if user.role == User.Role.SALESPERSON and not user.is_superuser:
            return qs.filter(lead__assigned_to=user)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = CreateQuoteInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        lead_id = serializer.validated_data['lead_id']
        try:
            lead = Lead.objects.get(id=lead_id)
        except Lead.DoesNotExist:
            return Response({"lead_id": "Lead does not exist."}, status=status.HTTP_404_NOT_FOUND)

        # Check salesperson ownership
        if request.user.role == User.Role.SALESPERSON and lead.assigned_to_id != request.user.id and not request.user.is_superuser:
            raise PermissionDenied("You do not have permission to create quotes for this lead.")

        # Compute next version
        latest_quote = Quote.objects.filter(lead=lead).order_by('-version').first()
        next_version = (latest_quote.version + 1) if latest_quote else 1

        quote = Quote.objects.create(
            lead=lead,
            version=next_version,
            system_size_kw=serializer.validated_data['system_size_kw'],
            brand=serializer.validated_data['brand'],
            price=serializer.validated_data['price'],
            subsidy_amount=serializer.validated_data.get('subsidy_amount'),
            status=Quote.Status.DRAFT,
            notes=serializer.validated_data.get('notes', ''),
            created_by=request.user,
        )

        return Response(QuoteSerializer(quote, context={'request': request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='mark-sent')
    @transaction.atomic
    def mark_sent(self, request, pk=None):
        quote = self.get_object()
        notes = request.data.get('notes', '')

        quote.status = Quote.Status.SENT
        if notes:
            quote.notes = f"{quote.notes}\n[Sent]: {notes}".strip()
        quote.save()

        lead = quote.lead
        old_status = lead.status
        target_status = Lead.Status.QUOTE_SENT
        next_action_text = "Follow up by call and WhatsApp on a set schedule"
        next_followup = timezone.now() + timedelta(days=2)

        lead.status = target_status
        lead.next_action = next_action_text
        lead.next_followup_at = next_followup
        lead.save()

        LeadStatusHistory.objects.create(
            lead=lead,
            old_status=old_status,
            new_status=target_status,
            changed_by=request.user,
            note=notes or f"Quote v{quote.version} sent ({quote.system_size_kw} kW - ₹{quote.price})",
        )

        outcome_obj = Outcome.objects.filter(stage=Outcome.Stage.QUOTE, name__icontains='Quote sent').first()
        Activity.objects.create(
            lead=lead,
            type=Activity.Type.NOTE,
            outcome=outcome_obj,
            notes=notes or f"Quote v{quote.version} marked sent",
            status_after=target_status,
            next_action=next_action_text,
            next_followup_at=next_followup,
            created_by=request.user,
        )

        return Response(QuoteSerializer(quote, context={'request': request}).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='revise')
    @transaction.atomic
    def revise(self, request, pk=None):
        old_quote = self.get_object()
        serializer = ReviseQuoteInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Mark old quote as revised
        old_quote.status = Quote.Status.REVISED
        old_quote.save()

        lead = old_quote.lead

        # Create new version (never overwrite old quote)
        latest_quote = Quote.objects.filter(lead=lead).order_by('-version').first()
        new_version = (latest_quote.version + 1) if latest_quote else (old_quote.version + 1)

        new_quote = Quote.objects.create(
            lead=lead,
            version=new_version,
            system_size_kw=serializer.validated_data['system_size_kw'],
            brand=serializer.validated_data['brand'],
            price=serializer.validated_data['price'],
            subsidy_amount=serializer.validated_data.get('subsidy_amount'),
            status=Quote.Status.REVISED,
            notes=serializer.validated_data.get('notes', ''),
            created_by=request.user,
        )

        old_status = lead.status
        target_status = Lead.Status.REVISING_QUOTE
        next_action_text = "Send a revised quote and keep the old version"
        next_followup = timezone.now() + timedelta(days=1)

        lead.status = target_status
        lead.next_action = next_action_text
        lead.next_followup_at = next_followup
        lead.save()

        LeadStatusHistory.objects.create(
            lead=lead,
            old_status=old_status,
            new_status=target_status,
            changed_by=request.user,
            note=f"Revised Quote to v{new_quote.version}. {serializer.validated_data.get('notes', '')}",
        )

        outcome_obj = Outcome.objects.filter(stage=Outcome.Stage.QUOTE, name__icontains='asks for changes').first()
        Activity.objects.create(
            lead=lead,
            type=Activity.Type.NOTE,
            outcome=outcome_obj,
            notes=f"Quote revised to v{new_quote.version}",
            status_after=target_status,
            next_action=next_action_text,
            next_followup_at=next_followup,
            created_by=request.user,
        )

        return Response(QuoteSerializer(new_quote, context={'request': request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='accept')
    @transaction.atomic
    def accept(self, request, pk=None):
        quote = self.get_object()
        notes = request.data.get('notes', '')

        quote.status = Quote.Status.ACCEPTED
        if notes:
            quote.notes = f"{quote.notes}\n[Accepted]: {notes}".strip()
        quote.save()

        lead = quote.lead
        old_status = lead.status
        target_status = Lead.Status.WON
        now = timezone.now()

        lead.status = target_status
        lead.won_at = now
        lead.next_action = "Process ends here"
        lead.next_followup_at = None
        lead.save()

        LeadStatusHistory.objects.create(
            lead=lead,
            old_status=old_status,
            new_status=target_status,
            changed_by=request.user,
            note=notes or f"Customer accepted Quote v{quote.version}. Deal Won!",
        )

        outcome_obj = Outcome.objects.filter(stage=Outcome.Stage.QUOTE, name__icontains='Customer agrees').first()
        Activity.objects.create(
            lead=lead,
            type=Activity.Type.NOTE,
            outcome=outcome_obj,
            notes=notes or f"Customer agreed to Quote v{quote.version} (₹{quote.price})",
            status_after=target_status,
            next_action="Process ends here",
            next_followup_at=None,
            created_by=request.user,
        )

        return Response(QuoteSerializer(quote, context={'request': request}).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='reject')
    @transaction.atomic
    def reject(self, request, pk=None):
        quote = self.get_object()
        serializer = RejectQuoteInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        lost_reason_id = serializer.validated_data['lost_reason_id']
        notes = serializer.validated_data.get('notes', '')

        if not can_user_mark_lost(request.user):
            raise PermissionDenied("You do not have permission to mark leads as Lost.")

        lost_reason = LostReason.objects.filter(id=lost_reason_id).first()
        if not lost_reason:
            return Response({"lost_reason_id": "Specified lost reason does not exist."}, status=status.HTTP_400_BAD_REQUEST)

        quote.status = Quote.Status.REJECTED
        if notes:
            quote.notes = f"{quote.notes}\n[Rejected]: {notes}".strip()
        quote.save()

        lead = quote.lead
        old_status = lead.status
        target_status = Lead.Status.LOST

        lead.status = target_status
        lead.lost_reason = lost_reason
        lead.next_action = f"Record lost reason: {lost_reason.name}"
        lead.next_followup_at = None
        lead.save()

        LeadStatusHistory.objects.create(
            lead=lead,
            old_status=old_status,
            new_status=target_status,
            changed_by=request.user,
            note=notes or f"Customer rejected quote v{quote.version}. Reason: {lost_reason.name}",
        )

        outcome_obj = Outcome.objects.filter(stage=Outcome.Stage.QUOTE, name__icontains='Customer rejects').first()
        Activity.objects.create(
            lead=lead,
            type=Activity.Type.NOTE,
            outcome=outcome_obj,
            notes=notes or f"Quote v{quote.version} rejected. Lost reason: {lost_reason.name}",
            status_after=target_status,
            next_action=f"Record lost reason: {lost_reason.name}",
            next_followup_at=None,
            created_by=request.user,
        )

        return Response(QuoteSerializer(quote, context={'request': request}).data, status=status.HTTP_200_OK)
