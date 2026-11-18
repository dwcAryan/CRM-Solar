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
from accounts.permissions import QuotePermission, can
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
    permission_classes = [QuotePermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['lead', 'status', 'brand']
    search_fields = ['lead__name', 'lead__phone', 'brand', 'notes']
    ordering_fields = ['version', 'price', 'created_at', 'id']

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if not user.is_authenticated:
            return qs.none()
        if not user.is_superuser:
            qs = qs.filter(lead__region__in=user.allowed_regions.all())
        if user.role == User.Role.SALESPERSON and not user.is_superuser:
            qs = qs.filter(lead__assigned_to=user)

        region_param = self.request.query_params.get('region')
        if region_param:
            qs = qs.filter(region_id=region_param.upper().strip())
        return qs

    def create(self, request, *args, **kwargs):
        serializer = CreateQuoteInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        lead_id = serializer.validated_data['lead_id']
        try:
            lead = Lead.objects.get(id=lead_id)
        except Lead.DoesNotExist:
            return Response({"lead_id": "Lead does not exist."}, status=status.HTTP_404_NOT_FOUND)

        # Check region permission
        if lead.region and not request.user.is_superuser and not request.user.allowed_regions.filter(code=lead.region_id).exists():
            raise PermissionDenied("You do not have permission to access leads in this region.")

        # Check salesperson ownership
        if request.user.role == User.Role.SALESPERSON and lead.assigned_to_id != request.user.id and not request.user.is_superuser:
            raise PermissionDenied("You do not have permission to create quotes for this lead.")

        # Compute next version
        latest_quote = Quote.objects.filter(lead=lead).order_by('-version').first()
        next_version = (latest_quote.version + 1) if latest_quote else 1

        notes = serializer.validated_data.get('notes', '')
        remark = serializer.validated_data.get('remark', '') or notes
        subsidy = serializer.validated_data.get('subsidy_amount')
        incentive = serializer.validated_data.get('incentive_amount')
        if incentive is None and subsidy is not None:
            incentive = subsidy

        quote = Quote.objects.create(
            lead=lead,
            version=next_version,
            system_size_kw=serializer.validated_data['system_size_kw'],
            battery_kwh=serializer.validated_data.get('battery_kwh'),
            brand=serializer.validated_data['brand'],
            price=serializer.validated_data['price'],
            tax_included=serializer.validated_data.get('tax_included', True),
            subsidy_amount=subsidy,
            incentive_amount=incentive or 0,
            status=Quote.Status.DRAFT,
            notes=notes,
            remark=remark[:500],
            created_by=request.user,
        )

        return Response(QuoteSerializer(quote, context={'request': request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='mark-sent')
    @transaction.atomic
    def mark_sent(self, request, pk=None):
        quote = self.get_object()
        notes = request.data.get('notes', '')
        remark = request.data.get('remark', '') or notes

        quote.status = Quote.Status.SENT
        if notes:
            quote.notes = f"{quote.notes}\n[Sent]: {notes}".strip()
        if remark:
            quote.remark = remark[:500]
        quote.save()

        lead = quote.lead
        old_status = lead.status
        target_status = Lead.Status.QUOTE_SENT
        next_action_text = "Follow up by call and WhatsApp on a set schedule"
        next_followup = timezone.now() + timedelta(days=2)

        lead.status = target_status
        lead.next_action = next_action_text
        lead.next_followup_at = next_followup
        if remark:
            lead.remark = remark[:500]
        lead.save()

        LeadStatusHistory.objects.create(
            lead=lead,
            old_status=old_status,
            new_status=target_status,
            changed_by=request.user,
            note=notes or f"Quote v{quote.version} sent ({quote.system_size_kw} kW - ₹{quote.price})",
            remark=remark[:500],
        )

        outcome_obj = Outcome.objects.filter(stage=Outcome.Stage.QUOTE, name__icontains='Quote sent').first()
        Activity.objects.create(
            lead=lead,
            type=Activity.Type.NOTE,
            outcome=outcome_obj,
            notes=notes or f"Quote v{quote.version} marked sent",
            remark=remark[:500],
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
        notes = serializer.validated_data.get('notes', '')
        remark = serializer.validated_data.get('remark', '') or notes

        subsidy = serializer.validated_data.get('subsidy_amount')
        incentive = serializer.validated_data.get('incentive_amount')
        if incentive is None and subsidy is not None:
            incentive = subsidy

        new_quote = Quote.objects.create(
            lead=lead,
            version=new_version,
            system_size_kw=serializer.validated_data['system_size_kw'],
            battery_kwh=serializer.validated_data.get('battery_kwh'),
            brand=serializer.validated_data['brand'],
            price=serializer.validated_data['price'],
            tax_included=serializer.validated_data.get('tax_included', True),
            subsidy_amount=subsidy,
            incentive_amount=incentive or 0,
            status=Quote.Status.REVISED,
            notes=notes,
            remark=remark[:500],
            created_by=request.user,
        )

        old_status = lead.status
        target_status = Lead.Status.REVISING_QUOTE
        next_action_text = "Send a revised quote and keep the old version"
        next_followup = timezone.now() + timedelta(days=1)

        lead.status = target_status
        lead.next_action = next_action_text
        lead.next_followup_at = next_followup
        if remark:
            lead.remark = remark[:500]
        lead.save()

        LeadStatusHistory.objects.create(
            lead=lead,
            old_status=old_status,
            new_status=target_status,
            changed_by=request.user,
            note=f"Revised Quote to v{new_quote.version}. {notes}".strip(),
            remark=remark[:500],
        )

        outcome_obj = Outcome.objects.filter(stage=Outcome.Stage.QUOTE, name__icontains='asks for changes').first()
        Activity.objects.create(
            lead=lead,
            type=Activity.Type.NOTE,
            outcome=outcome_obj,
            notes=f"Quote revised to v{new_quote.version}",
            remark=remark[:500],
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
        remark = request.data.get('remark', '') or notes

        quote.status = Quote.Status.ACCEPTED
        if notes:
            quote.notes = f"{quote.notes}\n[Accepted]: {notes}".strip()
        if remark:
            quote.remark = remark[:500]
        quote.save()

        lead = quote.lead
        old_status = lead.status
        target_status = Lead.Status.WON
        now = timezone.now()

        lead.status = target_status
        lead.won_at = now
        lead.next_action = "Process ends here"
        lead.next_followup_at = None
        if remark:
            lead.remark = remark[:500]
        lead.save()

        LeadStatusHistory.objects.create(
            lead=lead,
            old_status=old_status,
            new_status=target_status,
            changed_by=request.user,
            note=notes or f"Customer accepted Quote v{quote.version}. Deal Won!",
            remark=remark[:500],
        )

        outcome_obj = Outcome.objects.filter(stage=Outcome.Stage.QUOTE, name__icontains='Customer agrees').first()
        Activity.objects.create(
            lead=lead,
            type=Activity.Type.NOTE,
            outcome=outcome_obj,
            notes=notes or f"Customer agreed to Quote v{quote.version} (₹{quote.price})",
            remark=remark[:500],
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
        remark = serializer.validated_data.get('remark', '') or notes

        lost_reason = LostReason.objects.filter(id=lost_reason_id).first()
        if not lost_reason:
            return Response({"lost_reason_id": "Specified lost reason does not exist."}, status=status.HTTP_400_BAD_REQUEST)

        quote.status = Quote.Status.REJECTED
        if notes:
            quote.notes = f"{quote.notes}\n[Rejected]: {notes}".strip()
        if remark:
            quote.remark = remark[:500]
        quote.save()

        lead = quote.lead
        old_status = lead.status

        from django.db.models import Q
        from notifications.models import Notification

        if not can_user_mark_lost(request.user):
            if request.user.role == User.Role.SALESPERSON:
                target_status = Lead.Status.LOST_APPROVAL_PENDING
                lead.status = target_status
                lead.lost_pending_reason = lost_reason
                lead.lost_pending_notes = notes or remark
                lead.previous_status_before_lost = old_status
                lead.next_action = "Awaiting manager Lost approval"
                lead.next_followup_at = timezone.now() + timedelta(days=2)
                if remark:
                    lead.remark = remark[:500]
                lead.save()

                mgr_qs = User.objects.filter(role__in=[User.Role.MANAGER, User.Role.ADMIN], is_active=True)
                if lead.region_id:
                    mgr_qs = mgr_qs.filter(Q(allowed_regions__code=lead.region_id) | Q(is_superuser=True)).distinct()
                for mgr in mgr_qs:
                    Notification.objects.create(
                        user=mgr,
                        message=f"Lead '{lead.name}' submitted for Lost approval by {request.user.get_full_name() or request.user.username}.",
                        link=f"/leads/{lead.id}",
                    )
            else:
                raise PermissionDenied("You do not have permission to mark leads as Lost.")
        else:
            target_status = Lead.Status.LOST
            lead.status = target_status
            lead.lost_reason = lost_reason
            lead.next_action = f"Record lost reason: {lost_reason.name}"
            lead.next_followup_at = None
            if remark:
                lead.remark = remark[:500]
            lead.save()

        LeadStatusHistory.objects.create(
            lead=lead,
            old_status=old_status,
            new_status=target_status,
            changed_by=request.user,
            note=notes or f"Customer rejected quote v{quote.version}. Reason: {lost_reason.name}",
            remark=remark[:500],
        )

        outcome_obj = Outcome.objects.filter(stage=Outcome.Stage.QUOTE, name__icontains='Customer rejects').first()
        Activity.objects.create(
            lead=lead,
            type=Activity.Type.NOTE,
            outcome=outcome_obj,
            notes=notes or f"Quote v{quote.version} rejected. Lost reason: {lost_reason.name}",
            remark=remark[:500],
            status_after=target_status,
            next_action=f"Record lost reason: {lost_reason.name}",
            next_followup_at=None,
            created_by=request.user,
        )

        return Response(QuoteSerializer(quote, context={'request': request}).data, status=status.HTTP_200_OK)
