import csv
import json
from datetime import timedelta
from typing import Dict

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import LeadPermission
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
from .models import ImportBatch, Lead, LeadStatusHistory
from .serializers import (
    AddRemarkInputSerializer,
    AISuggestionSerializer,
    BulkActionSerializer,
    ImportBatchSerializer,
    LeadSerializer,
    LeadStatusHistorySerializer,
    LogActivityInputSerializer,
    MergeLeadInputSerializer,
)
from .services import process_log_activity


class LeadViewSet(viewsets.ModelViewSet):
    queryset = Lead.objects.all().select_related('source', 'assigned_to', 'lost_reason', 'nurture_reason')
    serializer_class = LeadSerializer
    permission_classes = [LeadPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'assigned_to', 'source', 'city', 'do_not_contact', 'property_type']
    search_fields = ['name', 'phone', 'alt_phone', 'email', 'city', 'pincode']
    ordering_fields = ['created_at', 'updated_at', 'next_followup_at', 'name', 'status']

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if not user.is_authenticated:
            return qs.none()

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

        return qs

    def perform_create(self, serializer):
        # Auto-assign to creating salesperson if not explicitly assigned
        if self.request.user.role == User.Role.SALESPERSON and not serializer.validated_data.get('assigned_to'):
            serializer.save(assigned_to=self.request.user)
        else:
            serializer.save()

    @action(detail=True, methods=['post'], url_path='log-activity')
    def log_activity(self, request, pk=None):
        lead = self.get_object()
        serializer = LogActivityInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        activity, updated_lead = process_log_activity(
            lead=lead,
            user=request.user,
            data=serializer.validated_data,
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
            target_lead = Lead.objects.get(id=target_lead_id)
        except Lead.DoesNotExist:
            return Response(
                {"target_lead_id": "Target lead not found."},
                status=status.HTTP_404_NOT_FOUND,
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
        user = request.user
        now = timezone.now()
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_today = start_of_today + timedelta(days=1)

        qs = Lead.objects.exclude(status__in=Lead.TERMINAL_STATUSES)
        if user.role == User.Role.SALESPERSON and not user.is_superuser:
            qs = qs.filter(assigned_to=user)

        due_today_or_overdue = qs.filter(
            Q(next_followup_at__lt=end_of_today) & Q(next_followup_at__isnull=False)
        ).order_by('next_followup_at')

        serializer = LeadSerializer(due_today_or_overdue, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='preview-csv')
    def preview_csv(self, request):
        """
        Parses uploaded file and returns 5-10 row preview with auto-matched column mapping.
        """
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
        """
        Performs full CSV / Excel import with column mapping, duplicate options, and assignment.
        """
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
            batch, results = execute_csv_import(
                uploaded_file=file_obj,
                mapping=mapping,
                duplicate_action=duplicate_action,
                assignment_mode=assignment_mode,
                single_user_id=single_user_id,
                round_robin_user_ids=round_robin_user_ids,
                user=request.user,
            )
        except DjangoValidationError as e:
            return Response({"error": e.message}, status=400)
        except Exception as e:
            return Response({"error": f"Import failed: {str(e)}"}, status=400)

        return Response(results, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='import-sample-csv')
    def import_sample_csv(self, request):
        """
        Generates and serves a clean, formula-injection-safe sample CSV template.
        """
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename="solar_leads_sample_template.csv"'

        writer = csv.writer(response)
        headers = [
            'Name',
            'Phone',
            'Email',
            'City',
            'Address',
            'Source',
            'Monthly Bill',
            'Roof Type',
            'Property Type',
            'Owner or Tenant',
            'Remark',
        ]
        writer.writerow(headers)

        sample_rows = [
            [
                'Ramesh Patel',
                '9825012345',
                'ramesh.patel@example.com',
                'Ahmedabad',
                '12 Shantivan Bungalows, Bodakdev',
                'Cold Call',
                '4500',
                'RCC flat',
                'residential',
                'owner',
                'Interested in 3 kW rooftop solar with PM Surya Ghar subsidy',
            ],
            [
                'Sunita Sharma',
                '9825098765',
                'sunita.sharma@example.com',
                'Surat',
                '402 Royal Palms, Vesu',
                'Website Form',
                '7800',
                'tin shade',
                'commercial',
                'owner',
                'Looking for 5 kW system for textile office',
            ],
        ]
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
        qs = Lead.objects.filter(id__in=lead_ids)
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

        return Response({
            "message": f"Successfully updated {updated_count} leads.",
            "updated_count": updated_count,
        })

    @action(detail=False, methods=['get'], url_path='export-csv')
    def export_csv(self, request):
        """
        Exports leads to CSV with current filters applied,
        protected against formula injection, encoded as utf-8-sig.
        """
        # Use filtered queryset from self.filter_queryset(self.get_queryset())
        queryset = self.filter_queryset(self.get_queryset())

        # If specific lead_ids given in query params, respect them
        lead_ids_param = request.query_params.get('lead_ids')
        if lead_ids_param:
            try:
                ids = [int(i.strip()) for i in lead_ids_param.split(',') if i.strip()]
                queryset = queryset.filter(id__in=ids)
            except ValueError:
                pass

        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="solar_crm_leads_{timestamp}.csv"'

        writer = csv.writer(response)
        headers = [
            'ID',
            'Name',
            'Phone',
            'Alt Phone',
            'Email',
            'City',
            'Pincode',
            'Address',
            'Source',
            'Status',
            'Next Action',
            'Next Followup At',
            'Monthly Bill',
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
                sanitize_csv_cell(lead.phone),
                sanitize_csv_cell(lead.alt_phone or ''),
                sanitize_csv_cell(lead.email or ''),
                sanitize_csv_cell(lead.city or ''),
                sanitize_csv_cell(lead.pincode or ''),
                sanitize_csv_cell(lead.address or ''),
                sanitize_csv_cell(lead.source.name if lead.source else ''),
                sanitize_csv_cell(lead.status),
                sanitize_csv_cell(lead.next_action or ''),
                sanitize_csv_cell(lead.next_followup_at.strftime('%Y-%m-%d %H:%M') if lead.next_followup_at else ''),
                sanitize_csv_cell(lead.monthly_bill if lead.monthly_bill is not None else ''),
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


class ImportBatchViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ImportBatch.objects.all().select_related('imported_by', 'reverted_by').order_by('-imported_at')
    serializer_class = ImportBatchSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['post'], url_path='undo')
    def undo(self, request, pk=None):
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


class DashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        qs = Lead.objects.all()

        if user.role == User.Role.SALESPERSON and not user.is_superuser:
            qs = qs.filter(assigned_to=user)

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

        # Needs attention list (rule-based, high risk leads, zero API calls)
        needs_attention_qs = qs.exclude(status__in=Lead.TERMINAL_STATUSES).filter(
            Q(attempt_count__gte=3) |
            Q(status=Lead.Status.QUOTE_SENT, updated_at__lt=now - timedelta(days=3)) |
            Q(status=Lead.Status.SURVEY_MISSED) |
            Q(next_followup_at__lt=now - timedelta(days=2)) |
            Q(next_followup_at__isnull=True)
        ).select_related('assigned_to', 'source').order_by('-updated_at')[:10]

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
                "phone": lead_item.phone,
                "city": lead_item.city,
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
                "total_active_leads": total_active_leads,
                "needs_attention": needs_attention,
            },
            status=status.HTTP_200_OK,
        )
