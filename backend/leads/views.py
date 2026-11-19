import defusedcsv
import json
import logging
from datetime import timedelta
from typing import Dict

from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.renderers import BaseRenderer, BrowsableAPIRenderer, JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import HasPermission, LeadPermission, can
from activities.models import Activity
from activities.serializers import ActivitySerializer
from ai_assist.service import get_or_generate_ai_suggestion
from masters.models import LeadSource

from .import_service import (
    auto_match_headers,
    execute_csv_import,
    generate_failed_rows_csv,
    parse_file_rows,
    sanitize_csv_cell,
    undo_import_batch,
)
from .models import AuditLog, ImportBatch, Lead, LeadStatusHistory
from .privacy_service import (
    anonymize_lead_data,
    correct_lead_data,
    generate_lead_dossier_dict,
    generate_lead_dossier_pdf,
)
from .serializers import (
    AddRemarkInputSerializer,
    AISuggestionSerializer,
    AnonymizeLeadInputSerializer,
    AuditLogSerializer,
    BulkActionSerializer,
    ImportBatchSerializer,
    LeadSerializer,
    LeadStatusHistorySerializer,
    LogActivityInputSerializer,
    MergeLeadInputSerializer,
    PrivacyCorrectInputSerializer,
)
from .services import process_log_activity


class PassthroughPdfRenderer(BaseRenderer):
    media_type = 'application/pdf'
    format = 'pdf'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


logger = logging.getLogger(__name__)



class LeadViewSet(viewsets.ModelViewSet):
    queryset = Lead.objects.all().select_related('source', 'assigned_to', 'lost_reason', 'nurture_reason', 'region')
    serializer_class = LeadSerializer
    permission_classes = [LeadPermission]
    permission_map = {
        'list': 'lead.view',
        'retrieve': 'lead.view',
        'create': 'lead.create',
        'update': 'lead.edit',
        'partial_update': 'lead.edit',
        'destroy': 'lead.delete',
        'assign': 'lead.assign',
        'bulk_assign': 'lead.assign',
        'auto_distribute': 'lead.assign',
        'unassigned': 'lead.unassigned_queue',
        'lost_approvals': 'lead.lost_approval',
        'approve_lost': 'lead.lost_approval',
        'reject_lost': 'lead.lost_approval',
        'soft_delete': 'lead.delete',
        'manual_status': 'lead.manual_status_change',
        'merge': 'lead.merge',
        'export_csv': 'lead.export',
        'preview_csv': 'lead.import',
        'import_csv': 'lead.import',
        'import_sample_csv': 'lead.import',
        'today_queue': 'lead.view',
        'bulk_action': 'lead.bulk_action',
        'ai_suggestions': 'ai.suggest',
        'privacy_export': 'privacy.manage',
        'anonymize': 'privacy.manage',
        'rectify': 'privacy.manage',
        'log_activity': 'activity.log',
        'add_remark': 'lead.bulk_action',
    }
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'assigned_to', 'source', 'city', 'state', 'region', 'consent_status', 'dncr_status', 'do_not_contact', 'property_type']
    search_fields = ['name', 'phone', 'alt_phone', 'phone_e164', 'alt_phone_e164', 'email', 'city', 'suburb', 'postcode', 'pincode']
    ordering_fields = ['created_at', 'updated_at', 'next_followup_at', 'name', 'status']

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset().filter(is_deleted=False)
        if not user.is_authenticated:
            return qs.none()

        # Surveyor cannot list leads directly
        if user.role == User.Role.SURVEYOR and not user.is_superuser:
            return qs.none()

        # Multi-country region scoping: sales & managers restricted to allowed regions
        if not user.is_superuser:
            allowed = user.allowed_regions.all()
            if allowed.exists():
                qs = qs.filter(region__in=allowed)

        # Region query filter (?region=IN or ?region=AU)
        region_param = self.request.query_params.get('region')
        if region_param:
            qs = qs.filter(region_id=region_param.upper().strip())

        # Role scoping: salesperson sees only own assigned leads
        if user.role == User.Role.SALESPERSON and not user.is_superuser:
            qs = qs.filter(assigned_to=user)

        # Tab filtering
        tab = self.request.query_params.get('tab')
        now = timezone.now()
        today = now.date()

        if tab == 'my':
            qs = qs.filter(assigned_to=user)
        elif tab == 'due_today':
            qs = qs.filter(
                next_followup_at__date=today,
            ).exclude(status__in=Lead.TERMINAL_STATUSES)
        elif tab == 'overdue':
            qs = qs.filter(
                next_followup_at__lt=now,
            ).exclude(status__in=Lead.TERMINAL_STATUSES)
        elif tab == 'no_followup':
            qs = qs.filter(
                next_followup_at__isnull=True,
            ).exclude(status__in=Lead.TERMINAL_STATUSES)
        elif tab == 'interested':
            qs = qs.filter(status='Interested')
        elif tab == 'quote_sent':
            qs = qs.filter(status='Quote sent')

        # Safe Whitelisted Date Filtering
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        date_field = self.request.query_params.get('date_field', 'created_at')

        if date_from or date_to:
            WHITELISTED_DATE_FIELDS = {'created_at', 'updated_at', 'next_followup_at', 'won_at', 'deleted_at'}
            if date_field not in WHITELISTED_DATE_FIELDS:
                from rest_framework.exceptions import ValidationError as DRFValidationError
                raise DRFValidationError(f"Invalid date_field '{date_field}'. Permitted fields: {sorted(WHITELISTED_DATE_FIELDS)}")

            import datetime
            from django.utils.dateparse import parse_date, parse_datetime

            if date_from:
                parsed_from = parse_datetime(date_from) or parse_date(date_from)
                if not parsed_from:
                    from rest_framework.exceptions import ValidationError as DRFValidationError
                    raise DRFValidationError("Invalid 'date_from' format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ).")
                if isinstance(parsed_from, datetime.date) and not isinstance(parsed_from, datetime.datetime):
                    parsed_from = timezone.make_aware(datetime.datetime.combine(parsed_from, datetime.time.min))
                elif timezone.is_naive(parsed_from):
                    parsed_from = timezone.make_aware(parsed_from)
                if parsed_from.year < 1900 or parsed_from.year > 2100:
                    from rest_framework.exceptions import ValidationError as DRFValidationError
                    raise DRFValidationError("date_from year out of range (1900-2100).")
                qs = qs.filter(**{f"{date_field}__gte": parsed_from})

            if date_to:
                parsed_to = parse_datetime(date_to) or parse_date(date_to)
                if not parsed_to:
                    from rest_framework.exceptions import ValidationError as DRFValidationError
                    raise DRFValidationError("Invalid 'date_to' format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ).")
                if isinstance(parsed_to, datetime.date) and not isinstance(parsed_to, datetime.datetime):
                    parsed_to = timezone.make_aware(datetime.datetime.combine(parsed_to, datetime.time.max))
                elif timezone.is_naive(parsed_to):
                    parsed_to = timezone.make_aware(parsed_to)
                if parsed_to.year < 1900 or parsed_to.year > 2100:
                    from rest_framework.exceptions import ValidationError as DRFValidationError
                    raise DRFValidationError("date_to year out of range (1900-2100).")
                qs = qs.filter(**{f"{date_field}__lte": parsed_to})

        return qs

    def list(self, request, *args, **kwargs):
        if getattr(request.user, 'role', None) == User.Role.SURVEYOR and not request.user.is_superuser:
            return Response(
                {"error": "Surveyors do not have permission to view the leads list. Access your assigned surveys via My Surveys."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        user = self.request.user
        if user.role == User.Role.SURVEYOR and not user.is_superuser:
            raise PermissionDenied("Surveyors cannot create leads.")

        extra = {'created_by': user}
        # Multi-country default region assignment
        if not serializer.validated_data.get('region'):
            if user.default_region:
                extra['region'] = user.default_region
            elif user.allowed_regions.exists():
                extra['region'] = user.allowed_regions.first()

        # Auto-assign to creating salesperson; salesperson cannot pick assignee
        if user.role == User.Role.SALESPERSON and not user.is_superuser:
            extra['assigned_to'] = user

        serializer.save(**extra)

    def perform_update(self, serializer):
        user = self.request.user
        instance = serializer.instance

        if user.role == User.Role.SALESPERSON and not user.is_superuser:
            # Salesperson cannot reassign
            new_assigned_to = serializer.validated_data.get('assigned_to')
            if new_assigned_to and new_assigned_to != instance.assigned_to:
                raise PermissionDenied("Salespeople cannot reassign leads. Manager or Admin action required.")

            # Salesperson cannot change status directly (only through outcome logging)
            new_status = serializer.validated_data.get('status')
            if new_status and new_status != instance.status:
                raise PermissionDenied("Salespeople cannot change status directly. Log an outcome to update status.")

            # Salesperson cannot reverse Do Not Contact
            if instance.do_not_contact and serializer.validated_data.get('do_not_contact') is False:
                raise PermissionDenied("Salespeople cannot reverse Do Not Contact. Manager or Admin action required.")

            # Salesperson cannot change region
            new_region = serializer.validated_data.get('region')
            if new_region and new_region != instance.region:
                raise PermissionDenied("Salespeople cannot change the lead region.")

        new_status = serializer.validated_data.get('status')
        if new_status == Lead.Status.WON:
            from quotes.models import Quote
            if not instance.quotes.filter(status=Quote.Status.ACCEPTED).exists():
                raise DRFValidationError("A lead cannot be marked as 'Won' without an accepted quote.")

        serializer.save()

    def destroy(self, request, *args, **kwargs):
        if not can(request.user, 'lead.delete'):
            return Response(
                {"error": "Only Administrators can delete leads."},
                status=status.HTTP_403_FORBIDDEN,
            )
        lead = self.get_object()
        reason = (request.data.get('reason') if isinstance(request.data, dict) else None) or request.query_params.get('reason')
        if not reason or not str(reason).strip():
            return Response(
                {"reason": "A deletion reason is required for soft deletion."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reason = str(reason).strip()
        with transaction.atomic():
            lead.is_deleted = True
            lead.deleted_at = timezone.now()
            lead.deleted_by = request.user
            lead.deleted_reason = reason
            lead.save()

            AuditLog.objects.create(
                user=request.user,
                action='lead_delete',
                lead=lead,
                reason=reason,
                details={'lead_id': lead.id, 'lead_name': lead.name},
            )

        return Response({"message": f"Lead '{lead.name}' soft-deleted.", "id": lead.id}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='log-activity')
    def log_activity(self, request, pk=None):
        lead = self.get_object()
        serializer = LogActivityInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        activity, updated_lead = process_log_activity(
            lead=lead,
            user=request.user,
            data=serializer.validated_data,
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        return Response(
            {
                "message": "Activity logged and lead status updated successfully.",
                "activity_id": activity.id,
                "lead": LeadSerializer(updated_lead, context={'request': request}).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='add-remark')
    def add_remark(self, request, pk=None):
        """
        Quick note / remark without changing lead status or next action.
        Creates an Activity with type='note'.
        """
        lead = self.get_object()
        serializer = AddRemarkInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        remark_text = serializer.validated_data['remark'].strip()

        with transaction.atomic():
            activity = Activity.objects.create(
                lead=lead,
                type=Activity.Type.NOTE,
                notes=remark_text,
                remark=remark_text,
                status_after=lead.status,
                next_action=lead.next_action,
                next_followup_at=lead.next_followup_at,
                created_by=request.user,
            )
            lead.remark = remark_text
            lead.save()

        return Response(
            {
                "message": "Remark added successfully.",
                "activity": ActivitySerializer(activity).data,
                "lead": LeadSerializer(lead, context={'request': request}).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'], url_path='merge')
    def merge(self, request, pk=None):
        if not can(request.user, 'lead.merge'):
            return Response({"error": "You do not have permission to merge leads."}, status=status.HTTP_403_FORBIDDEN)
        duplicate_lead = self.get_object()
        serializer = MergeLeadInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_lead_id = serializer.validated_data['target_lead_id']
        note = serializer.validated_data.get('note', '')
        remark = serializer.validated_data.get('remark', '') or note

        if duplicate_lead.id == target_lead_id:
            return Response(
                {"error": "Cannot merge a lead into itself."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            target_lead = self.get_queryset().get(id=target_lead_id)
        except Lead.DoesNotExist:
            return Response(
                {"target_lead_id": "Target lead not found or not accessible within your permitted regions."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if duplicate_lead.region_id != target_lead.region_id:
            return Response(
                {"error": "Cannot merge leads across different regions/countries."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            duplicate_lead.activities.all().update(lead=target_lead)
            duplicate_lead.surveys.all().update(lead=target_lead)
            duplicate_lead.quotes.all().update(lead=target_lead)

            old_status = duplicate_lead.status
            duplicate_lead.status = Lead.Status.MERGED
            duplicate_lead.next_action = f"Merged into lead #{target_lead.id} ({target_lead.name})"
            duplicate_lead.next_followup_at = None
            if remark:
                duplicate_lead.remark = remark[:500]
            duplicate_lead.save()

            LeadStatusHistory.objects.create(
                lead=duplicate_lead,
                old_status=old_status,
                new_status=Lead.Status.MERGED,
                changed_by=request.user,
                note=f"Merged into lead #{target_lead.id}. {note}".strip(),
                remark=remark[:500],
            )

            Activity.objects.create(
                lead=target_lead,
                type=Activity.Type.NOTE,
                notes=f"Merged with duplicate lead #{duplicate_lead.id} ({duplicate_lead.name}, {duplicate_lead.phone}). {note}".strip(),
                remark=remark[:500],
                status_after=target_lead.status,
                next_action=target_lead.next_action,
                next_followup_at=target_lead.next_followup_at,
                created_by=request.user,
            )

        return Response(
            {
                "message": f"Lead #{duplicate_lead.id} merged into #{target_lead.id} successfully.",
                "target_lead": LeadSerializer(target_lead, context={'request': request}).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['get', 'post'], url_path='ai-suggestions')
    def ai_suggestions(self, request, pk=None):
        """
        Retrieves or generates AI sales coaching recommendations for a lead.
        GET: Returns cached suggestion or generates one if none exists.
        POST: Force regenerates if refresh=True or data has changed.
        """
        lead = self.get_object()
        force_refresh = (
            request.method == 'POST' and (
                str(request.data.get('refresh', '')).lower() in ['true', '1'] or
                str(request.query_params.get('refresh', '')).lower() in ['true', '1']
            )
        )
        suggestion, is_new = get_or_generate_ai_suggestion(
            lead=lead,
            user=request.user,
            force_refresh=force_refresh,
        )
        serializer = AISuggestionSerializer(suggestion)
        return Response(
            {
                "suggestion": serializer.data,
                "is_new": is_new,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=['get'], url_path='today')
    def today_queue(self, request):
        now = timezone.now()
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_today = start_of_today + timedelta(days=1)

        qs = self.get_queryset().exclude(status__in=Lead.TERMINAL_STATUSES)

        due_today_or_overdue = qs.filter(
            Q(next_followup_at__lt=end_of_today) & Q(next_followup_at__isnull=False)
        ).order_by('next_followup_at')

        serializer = LeadSerializer(due_today_or_overdue, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='assign')
    def assign(self, request, pk=None):
        """
        Assigns or reassigns a lead to a salesperson or manager.
        Allowed for Managers and Admins only.
        """
        if not can(request.user, 'lead.assign'):
            return Response({"error": "You do not have permission to assign leads."}, status=status.HTTP_403_FORBIDDEN)

        lead = self.get_object()
        assigned_to_id = request.data.get('assigned_to_id')
        reason = request.data.get('reason', 'Lead assigned by manager')

        if not assigned_to_id:
            return Response({"error": "assigned_to_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_user = User.objects.get(id=assigned_to_id, is_active=True)
        except User.DoesNotExist:
            return Response({"error": "Target user not found."}, status=status.HTTP_404_NOT_FOUND)

        if target_user.role not in [User.Role.SALESPERSON, User.Role.MANAGER]:
            return Response({"error": "Can only assign to salespersons or managers."}, status=status.HTTP_400_BAD_REQUEST)

        old_user = lead.assigned_to
        with transaction.atomic():
            lead.assigned_to = target_user
            lead.save()

            LeadStatusHistory.objects.create(
                lead=lead,
                old_status=lead.status,
                new_status=lead.status,
                changed_by=request.user,
                note=f"Assigned to {target_user.get_full_name() or target_user.username}. Reason: {reason}",
            )

            AuditLog.objects.create(
                user=request.user,
                action='lead_assign',
                lead=lead,
                reason=reason,
                details={
                    'lead_id': lead.id,
                    'old_assigned_to_id': old_user.id if old_user else None,
                    'new_assigned_to_id': target_user.id,
                    'new_assigned_to_username': target_user.username,
                },
            )

            from notifications.models import Notification
            Notification.objects.create(
                user=target_user,
                message=f"You have been assigned lead '{lead.name}' ({lead.phone_e164 or lead.phone}).",
                link=f"/leads/{lead.id}",
            )
            try:
                from notifications.email_service import send_lead_assigned_notification
                send_lead_assigned_notification(lead, target_user)
            except Exception as e:
                logger.warning(f"Failed to send lead assigned email for lead {lead.id}: {e}")

        return Response({
            "message": f"Lead '{lead.name}' successfully assigned to {target_user.username}.",
            "lead": LeadSerializer(lead, context={'request': request}).data,
        })

    @action(detail=False, methods=['post'], url_path='bulk-assign')
    def bulk_assign(self, request):
        if not can(request.user, 'lead.assign'):
            return Response({"error": "You do not have permission to assign leads."}, status=status.HTTP_403_FORBIDDEN)

        lead_ids = request.data.get('lead_ids', [])
        assigned_to_id = request.data.get('assigned_to_id')
        reason = request.data.get('reason', 'Bulk assignment by manager')

        if not lead_ids or not assigned_to_id:
            return Response({"error": "lead_ids and assigned_to_id are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_user = User.objects.get(id=assigned_to_id, is_active=True)
        except User.DoesNotExist:
            return Response({"error": "Target user not found."}, status=status.HTTP_404_NOT_FOUND)

        qs = self.get_queryset().filter(id__in=lead_ids)
        updated_count = 0
        with transaction.atomic():
            for lead in qs:
                lead.assigned_to = target_user
                lead.save()
                LeadStatusHistory.objects.create(
                    lead=lead,
                    old_status=lead.status,
                    new_status=lead.status,
                    changed_by=request.user,
                    note=f"Bulk assigned to {target_user.username}. Reason: {reason}",
                )
                updated_count += 1

            AuditLog.objects.create(
                user=request.user,
                action='lead_bulk_assign',
                reason=reason,
                details={
                    'target_user_id': target_user.id,
                    'target_username': target_user.username,
                    'updated_count': updated_count,
                    'lead_ids': lead_ids,
                },
            )

            from notifications.models import Notification
            Notification.objects.create(
                user=target_user,
                message=f"You have been assigned {updated_count} leads via bulk assignment.",
                link="/leads",
            )
            try:
                from notifications.email_service import send_lead_assigned_notification
                for lead in qs[:5]:  # Send notification for primary batch leads
                    send_lead_assigned_notification(lead, target_user)
            except Exception as e:
                logger.warning(f"Failed to send bulk lead assigned email: {e}")

        return Response({
            "message": f"Successfully assigned {updated_count} leads to {target_user.username}.",
            "updated_count": updated_count,
        })

    @action(detail=False, methods=['post'], url_path='auto-distribute')
    def auto_distribute(self, request):
        if not can(request.user, 'lead.assign'):
            return Response({"error": "You do not have permission to auto-distribute leads."}, status=status.HTTP_403_FORBIDDEN)

        lead_ids = request.data.get('lead_ids', [])
        salesperson_ids = request.data.get('salesperson_ids', [])
        reason = request.data.get('reason', 'Manager auto-distribution (round-robin)')

        if not lead_ids or not salesperson_ids:
            return Response({"error": "lead_ids and salesperson_ids are required."}, status=status.HTTP_400_BAD_REQUEST)

        salespeople = list(User.objects.filter(id__in=salesperson_ids, is_active=True, role__in=[User.Role.SALESPERSON, User.Role.MANAGER]))
        if not salespeople:
            return Response({"error": "No valid active salespeople selected."}, status=status.HTTP_400_BAD_REQUEST)

        import itertools
        cycle = itertools.cycle(salespeople)
        leads = list(self.get_queryset().filter(id__in=lead_ids))
        distributed_count = 0

        with transaction.atomic():
            for lead in leads:
                assigned_rep = next(cycle)
                lead.assigned_to = assigned_rep
                lead.save()
                distributed_count += 1

            AuditLog.objects.create(
                user=request.user,
                action='lead_auto_distribute',
                reason=reason,
                details={
                    'distributed_count': distributed_count,
                    'salesperson_ids': salesperson_ids,
                    'lead_ids': lead_ids,
                },
            )

        return Response({
            "message": f"Successfully distributed {distributed_count} leads across {len(salespeople)} salespersons.",
            "distributed_count": distributed_count,
        })

    @action(detail=False, methods=['get'], url_path='unassigned')
    def unassigned(self, request):
        if not can(request.user, 'lead.unassigned_queue'):
            return Response({"error": "You do not have permission to access the unassigned leads queue."}, status=status.HTTP_403_FORBIDDEN)

        qs = Lead.objects.filter(assigned_to__isnull=True, is_deleted=False)
        if not request.user.is_superuser:
            qs = qs.filter(region__in=request.user.allowed_regions.all())
        serializer = LeadSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='lost-approvals')
    def lost_approvals(self, request):
        if not can(request.user, 'lead.lost_approval'):
            return Response({"error": "You do not have permission to view Lost approvals."}, status=status.HTTP_403_FORBIDDEN)

        qs = Lead.objects.filter(status=Lead.Status.LOST_APPROVAL_PENDING, is_deleted=False)
        if not request.user.is_superuser:
            qs = qs.filter(region__in=request.user.allowed_regions.all())
        serializer = LeadSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='approve-lost')
    def approve_lost(self, request, pk=None):
        if not can(request.user, 'lead.lost_approval'):
            return Response({"error": "You do not have permission to approve Lost leads."}, status=status.HTTP_403_FORBIDDEN)

        lead = self.get_object()
        if lead.status != Lead.Status.LOST_APPROVAL_PENDING:
            return Response({"error": f"Lead is not pending Lost approval (current status: {lead.status})."}, status=status.HTTP_400_BAD_REQUEST)

        lost_reason_id = request.data.get('lost_reason_id')
        reason = request.data.get('reason', 'Manager approved Lost request')

        from masters.models import LostReason
        final_lost_reason = None
        if lost_reason_id:
            final_lost_reason = LostReason.objects.filter(id=lost_reason_id).first()
        if not final_lost_reason:
            final_lost_reason = lead.lost_pending_reason

        with transaction.atomic():
            old_status = lead.status
            lead.status = Lead.Status.LOST
            lead.lost_reason = final_lost_reason
            lead.lost_pending_reason = None
            lead.lost_pending_notes = ""
            lead.next_action = "Closed - Lost"
            lead.next_followup_at = None
            lead.won_at = None
            lead.save()

            LeadStatusHistory.objects.create(
                lead=lead,
                old_status=old_status,
                new_status=Lead.Status.LOST,
                changed_by=request.user,
                note=f"Lost approved by {request.user.get_full_name() or request.user.username}. {reason}",
            )

            AuditLog.objects.create(
                user=request.user,
                action='lead_lost_approve',
                lead=lead,
                reason=reason,
                details={'lead_id': lead.id, 'lost_reason_id': final_lost_reason.id if final_lost_reason else None},
            )

            if lead.assigned_to:
                from notifications.models import Notification
                Notification.objects.create(
                    user=lead.assigned_to,
                    message=f"Lost status for lead '{lead.name}' was approved by manager.",
                    link=f"/leads/{lead.id}",
                )

        return Response({
            "message": f"Lead '{lead.name}' successfully closed as Lost.",
            "lead": LeadSerializer(lead, context={'request': request}).data,
        })

    @action(detail=True, methods=['post'], url_path='reject-lost')
    def reject_lost(self, request, pk=None):
        if not can(request.user, 'lead.lost_approval'):
            return Response({"error": "You do not have permission to reject Lost requests."}, status=status.HTTP_403_FORBIDDEN)

        lead = self.get_object()
        if lead.status != Lead.Status.LOST_APPROVAL_PENDING:
            return Response({"error": f"Lead is not pending Lost approval (current status: {lead.status})."}, status=status.HTTP_400_BAD_REQUEST)

        reason = request.data.get('reason')
        next_followup_at = request.data.get('next_followup_at')

        if not reason or not next_followup_at:
            return Response({"error": "Both 'reason' and 'next_followup_at' are required to reject Lost request."}, status=status.HTTP_400_BAD_REQUEST)

        target_status = lead.previous_status_before_lost or Lead.Status.FOLLOW_UP
        with transaction.atomic():
            old_status = lead.status
            lead.status = target_status
            lead.lost_pending_reason = None
            lead.lost_pending_notes = ""
            lead.next_action = f"Lost rejected by manager: {reason}"
            lead.next_followup_at = next_followup_at
            lead.save()

            LeadStatusHistory.objects.create(
                lead=lead,
                old_status=old_status,
                new_status=target_status,
                changed_by=request.user,
                note=f"Lost rejected by manager. Reason: {reason}",
            )

            AuditLog.objects.create(
                user=request.user,
                action='lead_lost_reject',
                lead=lead,
                reason=reason,
                details={'lead_id': lead.id, 'reverted_status': target_status, 'next_followup_at': str(next_followup_at)},
            )

            if lead.assigned_to:
                from notifications.models import Notification
                Notification.objects.create(
                    user=lead.assigned_to,
                    message=f"Lost request for lead '{lead.name}' was rejected by manager: {reason}",
                    link=f"/leads/{lead.id}",
                )

        return Response({
            "message": f"Lead '{lead.name}' returned to status '{target_status}'.",
            "lead": LeadSerializer(lead, context={'request': request}).data,
        })

    @action(detail=True, methods=['post'], url_path='manual-status')
    def manual_status(self, request, pk=None):
        if not can(request.user, 'lead.manual_status_change'):
            return Response({"error": "Only Managers and Admins can manually change lead status without an outcome."}, status=status.HTTP_403_FORBIDDEN)

        lead = self.get_object()
        new_status = request.data.get('status')
        reason = request.data.get('reason')
        next_action = request.data.get('next_action', lead.next_action)
        next_followup_at = request.data.get('next_followup_at')

        if not new_status or not reason:
            return Response({"error": "Both 'status' and 'reason' are required for manual status change."}, status=status.HTTP_400_BAD_REQUEST)

        if new_status not in Lead.Status.values:
            return Response({"error": f"Invalid status '{new_status}'."}, status=status.HTTP_400_BAD_REQUEST)

        if new_status == Lead.Status.WON:
            from quotes.models import Quote
            if not lead.quotes.filter(status=Quote.Status.ACCEPTED).exists():
                return Response(
                    {"error": "A lead cannot be marked as 'Won' without an accepted quote."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        from accounts.permissions import can_user_mark_lost
        if new_status == Lead.Status.LOST and not can_user_mark_lost(request.user):
            return Response(
                {"error": "You do not have permission to mark leads as Lost directly."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Enforce follow-up rule
        if new_status not in Lead.TERMINAL_STATUSES and not next_followup_at and not lead.next_followup_at:
            return Response({"error": "Next follow-up date is required for non-terminal statuses."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            old_status = lead.status
            lead.status = new_status
            lead.next_action = next_action
            if next_followup_at:
                lead.next_followup_at = next_followup_at
            if new_status in Lead.TERMINAL_STATUSES:
                lead.next_followup_at = None
            if new_status == Lead.Status.WON:
                lead.won_at = timezone.now()
            lead.save()

            LeadStatusHistory.objects.create(
                lead=lead,
                old_status=old_status,
                new_status=new_status,
                changed_by=request.user,
                note=f"Manual status change: {reason}",
            )

            AuditLog.objects.create(
                user=request.user,
                action='lead_manual_status',
                lead=lead,
                reason=reason,
                details={'old_status': old_status, 'new_status': new_status},
            )

        return Response({
            "message": f"Lead status updated to '{new_status}' manually.",
            "lead": LeadSerializer(lead, context={'request': request}).data,
        })

    @action(detail=False, methods=['post'], url_path='preview-csv')
    def preview_csv(self, request):
        if not can(request.user, 'lead.import'):
            return Response({"error": "You do not have permission to import leads."}, status=status.HTTP_403_FORBIDDEN)
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"error": "No file uploaded. Please upload a file with key 'file'."}, status=400)

        try:
            headers, data_rows = parse_file_rows(file_obj)
        except DjangoValidationError as e:
            return Response({"error": e.message}, status=400)
        except Exception as e:
            return Response({"error": f"Failed to parse file: {str(e)}"}, status=400)

        suggested_mapping = auto_match_headers(headers)
        preview_rows = []
        for row in data_rows[:10]:
            row_dict = {}
            for idx, h in enumerate(headers):
                val = row[idx] if idx < len(row) else ""
                row_dict[h] = val
            preview_rows.append(row_dict)

        return Response({
            "headers": headers,
            "suggested_mapping": suggested_mapping,
            "preview_rows": preview_rows,
            "total_rows": len(data_rows),
        })

    @action(detail=False, methods=['post'], url_path='import-csv')
    def import_csv(self, request):
        if not can(request.user, 'lead.import'):
            return Response({"error": "You do not have permission to import leads."}, status=status.HTTP_403_FORBIDDEN)
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"error": "No file uploaded. Please upload a file with key 'file'."}, status=400)

        mapping_raw = request.data.get('mapping')
        mapping: Dict[str, str] = {}
        if mapping_raw:
            if isinstance(mapping_raw, str):
                try:
                    mapping = json.loads(mapping_raw)
                except Exception:
                    pass
            elif isinstance(mapping_raw, dict):
                mapping = mapping_raw

        duplicate_action = request.data.get('duplicate_action', 'skip')
        assignment_mode = request.data.get('assignment_mode', 'unassigned')

        single_user_id = request.data.get('assigned_to_id')
        if single_user_id:
            try:
                single_user_id = int(single_user_id)
            except ValueError:
                single_user_id = None

        rr_raw = request.data.get('round_robin_user_ids')
        round_robin_user_ids = []
        if rr_raw:
            if isinstance(rr_raw, str):
                try:
                    round_robin_user_ids = [int(x.strip()) for x in rr_raw.split(',') if x.strip()]
                except ValueError:
                    pass
            elif isinstance(rr_raw, list):
                round_robin_user_ids = [int(x) for x in rr_raw]

        try:
            default_reg = request.data.get('region') or (request.user.default_region.code if request.user.default_region else 'IN')
            batch, results = execute_csv_import(
                uploaded_file=file_obj,
                mapping=mapping,
                duplicate_action=duplicate_action,
                assignment_mode=assignment_mode,
                single_user_id=single_user_id,
                round_robin_user_ids=round_robin_user_ids,
                user=request.user,
                default_region=default_reg,
            )
        except DjangoValidationError as e:
            return Response({"error": e.message}, status=400)
        except Exception as e:
            return Response({"error": f"Import failed: {str(e)}"}, status=400)

        return Response(results, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='import-sample-csv')
    def import_sample_csv(self, request):
        if not can(request.user, 'lead.import'):
            return Response({"error": "You do not have permission to download sample CSV."}, status=status.HTTP_403_FORBIDDEN)
        reg = (request.query_params.get('region') or (request.user.default_region.code if request.user.default_region else 'IN')).upper()

        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="solar_leads_sample_{reg.lower()}.csv"'

        writer = defusedcsv.writer(response)

        if reg == 'AU':
            headers = [
                'Name',
                'Phone',
                'Email',
                'Region',
                'State',
                'City',
                'Suburb',
                'Postcode',
                'Address',
                'Source',
                'Monthly Bill',
                'Bill Period',
                'Electricity Provider',
                'Roof Type',
                'Property Type',
                'Owner or Tenant',
                'Consent Source',
                'Remark',
            ]
            writer.writerow(headers)
            sample_rows = [
                [
                    'Liam O\'Connor',
                    '0412345678',
                    'liam.oconnor@example.com.au',
                    'AU',
                    'NSW',
                    'Sydney',
                    'Parramatta',
                    '2150',
                    '45 Church St',
                    'Website Form',
                    '850',
                    'quarterly',
                    'Origin Energy',
                    'Colorbond',
                    'residential',
                    'owner',
                    'Website Form',
                    'Interested in 6.6 kW system with STC incentive',
                ],
                [
                    'Sarah Miller',
                    '0423456789',
                    'sarah.miller@example.com.au',
                    'AU',
                    'VIC',
                    'Melbourne',
                    'Richmond',
                    '3121',
                    '12 Bridge Rd',
                    'Referral',
                    '720',
                    'quarterly',
                    'AGL',
                    'Tile',
                    'residential',
                    'owner',
                    'Referral',
                    'Wants battery storage quote along with 10 kW panels',
                ],
            ]
        else:
            headers = [
                'Name',
                'Phone',
                'Email',
                'Region',
                'State',
                'City',
                'Pincode',
                'Address',
                'Source',
                'Monthly Bill',
                'Bill Period',
                'Electricity Provider',
                'Roof Type',
                'Property Type',
                'Owner or Tenant',
                'Consent Source',
                'Remark',
            ]
            writer.writerow(headers)
            sample_rows = [
                [
                    'Ramesh Patel',
                    '9825012345',
                    'ramesh.patel@example.com',
                    'IN',
                    'Gujarat',
                    'Ahmedabad',
                    '380054',
                    '12 Shantivan Bungalows, Bodakdev',
                    'Cold Call',
                    '4500',
                    'monthly',
                    'UGVCL',
                    'RCC flat',
                    'residential',
                    'owner',
                    'Web Form',
                    'Interested in 3 kW rooftop solar with PM Surya Ghar subsidy',
                ],
                [
                    'Sunita Sharma',
                    '9825098765',
                    'sunita.sharma@example.com',
                    'IN',
                    'Gujarat',
                    'Surat',
                    '395007',
                    '402 Royal Palms, Vesu',
                    'Website Form',
                    '7800',
                    'monthly',
                    'DGVCL',
                    'tin shade',
                    'commercial',
                    'owner',
                    'Solar Expo',
                    'Looking for 5 kW system for textile office',
                ],
            ]

        for row in sample_rows:
            writer.writerow([sanitize_csv_cell(c) for c in row])

        return response
        for row in sample_rows:
            writer.writerow([sanitize_csv_cell(c) for c in row])

        return response

    @action(detail=False, methods=['post'], url_path='bulk-action')
    def bulk_action(self, request):
        """
        Performs bulk assignment or source update across selected leads.
        """
        serializer = BulkActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        lead_ids = serializer.validated_data['lead_ids']
        action_name = serializer.validated_data['action']
        value = serializer.validated_data['value']
        remark = serializer.validated_data.get('remark', '')

        user = request.user
        if user.role == User.Role.SALESPERSON and not user.is_superuser:
            if action_name != 'add_remark':
                return Response(
                    {"error": "Salespeople are only permitted to execute 'add_remark' bulk actions on their own leads."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        if action_name == 'assign' and not can(user, 'lead.assign'):
            return Response({"error": "You do not have permission to assign leads."}, status=status.HTTP_403_FORBIDDEN)

        qs = self.get_queryset().filter(id__in=lead_ids)
        if user.role == User.Role.SALESPERSON and not user.is_superuser:
            qs = qs.filter(assigned_to=user)

        updated_count = 0

        with transaction.atomic():
            if action_name == 'assign':
                assigned_user = User.objects.filter(id=value).first()
                if not assigned_user:
                    return Response({"error": "Selected user does not exist."}, status=400)

                for lead in qs:
                    lead.assigned_to = assigned_user
                    if remark:
                        lead.remark = remark[:500]
                    lead.save()
                    LeadStatusHistory.objects.create(
                        lead=lead,
                        old_status=lead.status,
                        new_status=lead.status,
                        changed_by=user,
                        note=f"Bulk re-assigned to {assigned_user.get_full_name() or assigned_user.username}",
                        remark=remark[:500] if remark else '',
                    )
                    updated_count += 1

            elif action_name == 'change_source':
                new_source = LeadSource.objects.filter(id=value).first()
                if not new_source:
                    return Response({"error": "Selected lead source does not exist."}, status=400)

                for lead in qs:
                    lead.source = new_source
                    if remark:
                        lead.remark = remark[:500]
                    lead.save()
                    updated_count += 1

            elif action_name == 'add_remark':
                for lead in qs:
                    if remark:
                        lead.remark = remark[:500]
                        lead.save()
                        Activity.objects.create(
                            lead=lead,
                            type=Activity.Type.NOTE,
                            notes=remark,
                            remark=remark[:500],
                            status_after=lead.status,
                            next_action=lead.next_action,
                            next_followup_at=lead.next_followup_at,
                            created_by=user,
                        )
                        updated_count += 1

        return Response({
            "message": f"Successfully updated {updated_count} leads.",
            "updated_count": updated_count,
        })

    @action(
        detail=True,
        methods=['get'],
        url_path='privacy-export',
        renderer_classes=[JSONRenderer, BrowsableAPIRenderer, PassthroughPdfRenderer],
    )
    def privacy_export(self, request, pk=None):
        """
        Exports a complete Data Subject Access Request (DSAR) dossier for the lead.
        Supports JSON (default) or PDF (?format=pdf). Restricted to Administrators.
        """
        if request.user.role != User.Role.ADMIN and not request.user.is_superuser:
            return Response(
                {"detail": "Access restricted: Only system administrators can export privacy dossiers."},
                status=status.HTTP_403_FORBIDDEN,
            )

        lead = self.get_object()
        fmt = request.query_params.get('format', 'json').lower()
        ip_addr = request.META.get('REMOTE_ADDR')

        AuditLog.objects.create(
            user=request.user,
            action='privacy_export',
            lead=lead,
            reason=f"Privacy DSAR dossier exported in {fmt.upper()} format",
            details={'format': fmt, 'region': lead.region_id},
            ip_address=ip_addr,
        )

        if fmt == 'pdf':
            pdf_bytes = generate_lead_dossier_pdf(lead)
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="privacy_dossier_lead_{lead.id}.pdf"'
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
            response['Pragma'] = 'no-cache'
            return response

        dossier = generate_lead_dossier_dict(lead)
        response = Response(dossier, status=status.HTTP_200_OK)
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
        response['Pragma'] = 'no-cache'
        return response

    @action(detail=True, methods=['post'], url_path='anonymize')
    def anonymize(self, request, pk=None):
        """
        Permanently and irreversibly anonymizes personal data of the lead for 'Right to be Forgotten'.
        Restricted to Administrators with a mandatory justification reason.
        """
        if request.user.role != User.Role.ADMIN and not request.user.is_superuser:
            return Response(
                {"detail": "Access restricted: Only system administrators can anonymize lead records."},
                status=status.HTTP_403_FORBIDDEN,
            )

        lead = self.get_object()
        serializer = AnonymizeLeadInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reason = serializer.validated_data['reason']
        ip_addr = request.META.get('REMOTE_ADDR')

        try:
            updated_lead = anonymize_lead_data(lead, reason=reason, user=request.user, ip_address=ip_addr)
        except DjangoValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "message": f"Lead #{lead.id} personal information has been irreversibly anonymized.",
                "lead": LeadSerializer(updated_lead, context={'request': request}).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='privacy-correct')
    def privacy_correct(self, request, pk=None):
        """
        Rectifies inaccurate personal information with an explicit justification reason and audit trail.
        Restricted to Administrators.
        """
        if request.user.role != User.Role.ADMIN and not request.user.is_superuser:
            return Response(
                {"detail": "Access restricted: Only system administrators can perform privacy corrections."},
                status=status.HTTP_403_FORBIDDEN,
            )

        lead = self.get_object()
        serializer = PrivacyCorrectInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reason = serializer.validated_data['reason']
        updates = serializer.validated_data['updates']
        ip_addr = request.META.get('REMOTE_ADDR')

        try:
            updated_lead = correct_lead_data(lead, updates=updates, reason=reason, user=request.user, ip_address=ip_addr)
        except DjangoValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "message": f"Lead #{lead.id} personal records corrected successfully.",
                "lead": LeadSerializer(updated_lead, context={'request': request}).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='check-dncr')
    def check_dncr(self, request, pk=None):
        """
        Updates the Australian Do Not Call Register (DNCR) status check for the lead.
        """
        lead = self.get_object()
        dncr_status = request.data.get('dncr_status')
        if dncr_status not in ['on_register', 'not_on_register', 'exempt']:
            dncr_status = 'on_register' if lead.dncr_status != 'on_register' else 'not_on_register'

        notes = (request.data.get('notes') or '').strip()
        ip_addr = request.META.get('REMOTE_ADDR')

        lead.dncr_status = dncr_status
        lead.dncr_checked_at = timezone.now()
        lead.dncr_checked_by = request.user
        lead.save(update_fields=['dncr_status', 'dncr_checked_at', 'dncr_checked_by'])

        AuditLog.objects.create(
            user=request.user,
            action='dncr_check',
            lead=lead,
            reason=notes or f"DNCR status set to {dncr_status}",
            details={'dncr_status': dncr_status, 'phone': lead.phone_e164 or lead.phone},
            ip_address=ip_addr,
        )

        return Response(
            {
                "message": f"Lead #{lead.id} DNCR status updated to '{dncr_status}'.",
                "lead": LeadSerializer(lead, context={'request': request}).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=['get'], url_path='export-csv')
    def export_csv(self, request):
        """
        Exports leads to CSV with current filters applied,
        protected against formula injection, encoded as utf-8-sig.
        Logs bulk export action into the compliance AuditLog.
        """
        if not can(request.user, 'lead.export'):
            return Response(
                {"error": "You do not have permission to export leads."},
                status=status.HTTP_403_FORBIDDEN,
            )
        queryset = self.filter_queryset(self.get_queryset())

        lead_ids_param = request.query_params.get('lead_ids')
        if lead_ids_param:
            try:
                ids = [int(i.strip()) for i in lead_ids_param.split(',') if i.strip()]
                queryset = queryset.filter(id__in=ids)
            except ValueError:
                pass

        total_count = queryset.count()
        AuditLog.objects.create(
            user=request.user,
            action='bulk_export',
            reason=f"Exported {total_count} leads to CSV",
            details={
                'exported_count': total_count,
                'query_params': dict(request.query_params),
            },
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="solar_crm_leads_{timestamp}.csv"'

        writer = defusedcsv.writer(response)
        headers = [
            'ID',
            'Name',
            'Region',
            'State',
            'City',
            'Suburb',
            'Pincode / Postcode',
            'Address',
            'Phone (E.164)',
            'Raw Phone Backup',
            'Alt Phone',
            'Email',
            'Source',
            'Status',
            'Consent Status',
            'Consent Source',
            'Consent Date',
            'DNCR Status',
            'Do Not Contact',
            'Next Action',
            'Next Followup At',
            'Bill Amount',
            'Bill Period',
            'Normalized Monthly Bill',
            'Electricity Provider',
            'Roof Type',
            'Property Type',
            'Owner or Tenant',
            'Assigned To',
            'Attempt Count',
            'Won At',
            'Remark',
            'Created At',
        ]
        writer.writerow(headers)

        for lead in queryset.iterator():
            writer.writerow([
                sanitize_csv_cell(lead.id),
                sanitize_csv_cell(lead.name),
                sanitize_csv_cell(lead.region_id or ''),
                sanitize_csv_cell(lead.state or ''),
                sanitize_csv_cell(lead.city or ''),
                sanitize_csv_cell(lead.suburb or ''),
                sanitize_csv_cell(lead.postcode or lead.pincode or ''),
                sanitize_csv_cell(lead.address or ''),
                sanitize_csv_cell(lead.phone_e164 or lead.phone or ''),
                sanitize_csv_cell(lead.phone_raw_backup or ''),
                sanitize_csv_cell(lead.alt_phone_e164 or lead.alt_phone or ''),
                sanitize_csv_cell(lead.email or ''),
                sanitize_csv_cell(lead.source.name if lead.source else ''),
                sanitize_csv_cell(lead.status),
                sanitize_csv_cell(lead.consent_status or ''),
                sanitize_csv_cell(lead.consent_source or ''),
                sanitize_csv_cell(lead.consent_date.isoformat() if lead.consent_date else ''),
                sanitize_csv_cell(lead.dncr_status or ''),
                sanitize_csv_cell('Yes' if lead.do_not_contact else 'No'),
                sanitize_csv_cell(lead.next_action or ''),
                sanitize_csv_cell(lead.next_followup_at.strftime('%Y-%m-%d %H:%M') if lead.next_followup_at else ''),
                sanitize_csv_cell(lead.bill_amount if lead.bill_amount is not None else ''),
                sanitize_csv_cell(lead.bill_period or ''),
                sanitize_csv_cell(lead.normalized_monthly_bill if lead.normalized_monthly_bill is not None else (lead.monthly_bill or '')),
                sanitize_csv_cell(lead.electricity_provider or ''),
                sanitize_csv_cell(lead.roof_type or ''),
                sanitize_csv_cell(lead.property_type or ''),
                sanitize_csv_cell(lead.owner_or_tenant or ''),
                sanitize_csv_cell(lead.assigned_to.get_full_name() if lead.assigned_to else 'Unassigned'),
                sanitize_csv_cell(lead.attempt_count),
                sanitize_csv_cell(lead.won_at.strftime('%Y-%m-%d %H:%M') if lead.won_at else ''),
                sanitize_csv_cell(lead.remark or ''),
                sanitize_csv_cell(lead.created_at.strftime('%Y-%m-%d %H:%M')),
            ])

        return response


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only audit log endpoint for compliance and tamper-evident tracking.
    """
    queryset = AuditLog.objects.all().select_related('user', 'lead').order_by('-timestamp')
    serializer_class = AuditLogSerializer
    permission_classes = [HasPermission('audit.view')]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['action', 'user', 'lead_id_recorded']
    search_fields = ['reason', 'user_name']
    ordering_fields = ['timestamp', 'action']

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return self.queryset.none()
        if not can(user, 'audit.view'):
            return self.queryset.none()
        if user.role == User.Role.MANAGER and not user.is_superuser:
            allowed = user.allowed_regions.all()
            if allowed.exists():
                return self.queryset.filter(Q(lead__region__in=allowed) | Q(lead__isnull=True))
        return self.queryset


class ImportBatchViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ImportBatch.objects.all().select_related('imported_by', 'reverted_by').order_by('-imported_at')
    serializer_class = ImportBatchSerializer
    permission_classes = [HasPermission('lead.import')]

    @action(detail=True, methods=['post'], url_path='undo')
    def undo(self, request, pk=None):
        if not can(request.user, 'lead.import'):
            return Response({"error": "You do not have permission to undo import batches."}, status=status.HTTP_403_FORBIDDEN)
        batch = self.get_object()
        success, message, deleted_count = undo_import_batch(batch.id, user=request.user)
        if not success:
            return Response({"error": message}, status=400)
        return Response({
            "message": message,
            "deleted_count": deleted_count,
            "batch": ImportBatchSerializer(batch).data,
        })

    @action(detail=True, methods=['get'], url_path='failed-rows-csv')
    def failed_rows_csv(self, request, pk=None):
        batch = self.get_object()
        csv_text = generate_failed_rows_csv(batch.failed_rows_json or [])
        response = HttpResponse(csv_text, content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="failed_rows_batch_{batch.id}.csv"'
        return response


class LeadStatusHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LeadStatusHistory.objects.all().select_related('lead', 'changed_by').order_by('-changed_at')
    serializer_class = LeadStatusHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['lead', 'old_status', 'new_status', 'changed_by']
    ordering_fields = ['changed_at', 'id']

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if not user.is_authenticated:
            return qs.none()
        if not user.is_superuser:
            allowed = user.allowed_regions.all()
            if allowed.exists():
                qs = qs.filter(lead__region__in=allowed)
            else:
                qs = qs.none()
            if user.role == User.Role.SALESPERSON:
                qs = qs.filter(lead__assigned_to=user)
            elif user.role == User.Role.SURVEYOR:
                qs = qs.none()
        return qs


class DashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if not can(user, 'dashboard.view'):
            return Response({"error": "You do not have permission to view dashboard."}, status=status.HTTP_403_FORBIDDEN)

        # Surveyor role: role-specific survey statistics
        if user.role == User.Role.SURVEYOR and not user.is_superuser:
            from surveys.models import Survey
            surveys_qs = Survey.objects.filter(surveyor=user)
            today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            return Response({
                "role": "surveyor",
                "surveys_today_count": surveys_qs.filter(scheduled_at__gte=today_start, scheduled_at__lt=today_end).count(),
                "surveys_completed_count": surveys_qs.filter(status=Survey.Status.DONE).count(),
                "surveys_pending_count": surveys_qs.filter(status__in=[Survey.Status.BOOKED, Survey.Status.RESCHEDULED]).count(),
                "total_assigned": surveys_qs.count(),
            }, status=status.HTTP_200_OK)

        qs = Lead.objects.filter(is_deleted=False)

        # Multi-country region scoping
        if not user.is_superuser:
            allowed = user.allowed_regions.all()
            if allowed.exists():
                region_param = request.query_params.get('region')
                if region_param:
                    region_code = region_param.upper().strip()
                    if not allowed.filter(code=region_code).exists():
                        return Response({"error": "You do not have access to the requested region."}, status=status.HTTP_403_FORBIDDEN)
                    qs = qs.filter(region_id=region_code)
                else:
                    qs = qs.filter(region__in=allowed)
            else:
                qs = qs.none()
        else:
            region_param = request.query_params.get('region')
            if region_param:
                qs = qs.filter(region_id=region_param.upper().strip())

        if user.role == User.Role.SALESPERSON and not user.is_superuser:
            qs = qs.filter(assigned_to=user)

        # Safe Date Filtering on Dashboard
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        date_field = request.query_params.get('date_field', 'created_at')

        if date_from or date_to:
            WHITELISTED_DATE_FIELDS = {'created_at', 'updated_at', 'next_followup_at', 'won_at'}
            if date_field not in WHITELISTED_DATE_FIELDS:
                return Response({"error": f"Invalid date_field '{date_field}'."}, status=status.HTTP_400_BAD_REQUEST)

            import datetime
            from django.utils.dateparse import parse_date, parse_datetime

            if date_from:
                parsed_from = parse_datetime(date_from) or parse_date(date_from)
                if not parsed_from:
                    return Response({"error": "Invalid date_from format."}, status=status.HTTP_400_BAD_REQUEST)
                if isinstance(parsed_from, datetime.date) and not isinstance(parsed_from, datetime.datetime):
                    parsed_from = timezone.make_aware(datetime.datetime.combine(parsed_from, datetime.time.min))
                elif timezone.is_naive(parsed_from):
                    parsed_from = timezone.make_aware(parsed_from)
                if parsed_from.year < 1900 or parsed_from.year > 2100:
                    return Response({"error": "date_from year out of range."}, status=status.HTTP_400_BAD_REQUEST)
                qs = qs.filter(**{f"{date_field}__gte": parsed_from})

            if date_to:
                parsed_to = parse_datetime(date_to) or parse_date(date_to)
                if not parsed_to:
                    return Response({"error": "Invalid date_to format."}, status=status.HTTP_400_BAD_REQUEST)
                if isinstance(parsed_to, datetime.date) and not isinstance(parsed_to, datetime.datetime):
                    parsed_to = timezone.make_aware(datetime.datetime.combine(parsed_to, datetime.time.max))
                elif timezone.is_naive(parsed_to):
                    parsed_to = timezone.make_aware(parsed_to)
                if parsed_to.year < 1900 or parsed_to.year > 2100:
                    return Response({"error": "date_to year out of range."}, status=status.HTTP_400_BAD_REQUEST)
                qs = qs.filter(**{f"{date_field}__lte": parsed_to})

        total_active_leads = qs.exclude(status__in=Lead.TERMINAL_STATUSES).count()

        status_counts = {}
        for row in qs.values('status').annotate(c=Count('id')):
            status_counts[row['status']] = row['c']

        funnel = {
            'new': status_counts.get(Lead.Status.NEW, 0),
            'interested': status_counts.get(Lead.Status.INTERESTED, 0),
            'survey': (
                status_counts.get(Lead.Status.SURVEY_TO_SCHEDULE, 0)
                + status_counts.get(Lead.Status.SURVEY_SCHEDULED, 0)
                + status_counts.get(Lead.Status.SURVEY_RESCHEDULED, 0)
                + status_counts.get(Lead.Status.DESIGN_PENDING, 0)
            ),
            'quote_sent': (
                status_counts.get(Lead.Status.QUOTE_SENT, 0)
                + status_counts.get(Lead.Status.REVISING_QUOTE, 0)
                + status_counts.get(Lead.Status.NEGOTIATION, 0)
            ),
            'won': status_counts.get(Lead.Status.WON, 0),
        }

        now = timezone.now()
        overdue_followups = qs.exclude(status__in=Lead.TERMINAL_STATUSES).filter(
            next_followup_at__lt=now,
            next_followup_at__isnull=False,
        ).count()

        leads_per_source = []
        source_counts = qs.values('source__name').annotate(c=Count('id')).order_by('-c')
        for sc in source_counts:
            name = sc['source__name'] or 'Unassigned'
            leads_per_source.append({'source': name, 'count': sc['c']})

        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        won_this_month = qs.filter(status=Lead.Status.WON, won_at__gte=start_of_month).count()

        # Multi-currency won value tracking (never mix or sum different currencies!)
        from quotes.models import Quote
        won_leads_subquery = qs.filter(status=Lead.Status.WON)
        accepted_quotes = Quote.objects.filter(lead__in=won_leads_subquery, status=Quote.Status.ACCEPTED)
        won_value_by_currency = {'INR': 0.0, 'AUD': 0.0}
        for q in accepted_quotes:
            c = q.currency or ('INR' if q.region_id == 'IN' else 'AUD')
            won_value_by_currency[c] = won_value_by_currency.get(c, 0.0) + float(q.price)

        # Needs attention list (rule-based, high risk leads, zero API calls)
        needs_attention_qs = qs.exclude(status__in=Lead.TERMINAL_STATUSES).filter(
            Q(attempt_count__gte=3) |
            Q(status=Lead.Status.QUOTE_SENT, updated_at__lt=now - timedelta(days=3)) |
            Q(status=Lead.Status.SURVEY_MISSED) |
            Q(next_followup_at__lt=now - timedelta(days=2)) |
            Q(next_followup_at__isnull=True)
        ).select_related('assigned_to', 'source', 'region').order_by('-updated_at')[:10]

        needs_attention = []
        for lead_item in needs_attention_qs:
            reason = "No next follow-up date set"
            risk = "high"
            if lead_item.attempt_count >= 3:
                reason = f"{lead_item.attempt_count} consecutive failed call attempts"
                risk = "high"
            elif lead_item.status == Lead.Status.SURVEY_MISSED:
                reason = "Site survey was missed by customer"
                risk = "high"
            elif lead_item.status == Lead.Status.QUOTE_SENT and lead_item.updated_at < now - timedelta(days=3):
                reason = "Quotation sent > 3 days ago with no response"
                risk = "medium"
            elif lead_item.next_followup_at and lead_item.next_followup_at < now - timedelta(days=2):
                days_overdue = (now - lead_item.next_followup_at).days
                reason = f"Follow-up severely overdue by {days_overdue} days"
                risk = "high"

            needs_attention.append({
                "id": lead_item.id,
                "name": lead_item.name,
                "phone": lead_item.phone_e164 or lead_item.phone,
                "city": lead_item.city,
                "region": lead_item.region_id,
                "status": lead_item.status,
                "risk_level": risk,
                "reason": reason,
                "next_followup_at": lead_item.next_followup_at.isoformat() if lead_item.next_followup_at else None,
                "assigned_to_name": lead_item.assigned_to.get_full_name() if lead_item.assigned_to else "Unassigned",
            })

        return Response(
            {
                "status_counts": status_counts,
                "funnel": funnel,
                "overdue_followups": overdue_followups,
                "leads_per_source": leads_per_source,
                "won_this_month": won_this_month,
                "won_value_by_currency": won_value_by_currency,
                "total_active_leads": total_active_leads,
                "needs_attention": needs_attention,
            },
            status=status.HTTP_200_OK,
        )
