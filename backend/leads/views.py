import csv
import io

from django.db.models import Count
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import LeadPermission
from masters.models import LeadSource

from .models import Lead, LeadStatusHistory
from .serializers import (
    LeadSerializer,
    LeadStatusHistorySerializer,
    LogActivityInputSerializer,
    MergeLeadInputSerializer,
)
from .services import process_log_activity
from .utils import find_duplicate_lead, normalize_phone


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
            return qs.filter(assigned_to=user)
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

    @action(detail=True, methods=['post'], url_path='merge')
    def merge(self, request, pk=None):
        duplicate_lead = self.get_object()
        serializer = MergeLeadInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_lead_id = serializer.validated_data['target_lead_id']
        note = serializer.validated_data.get('note', '')

        if duplicate_lead.id == target_lead_id:
            return Response(
                {"error": "Cannot merge a lead into itself."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            target_lead = Lead.objects.get(id=target_lead_id)
        except Lead.DoesNotExist:
            return Response(
                {"target_lead_id": "Target lead does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Mark duplicate lead as Merged (terminal status)
        old_status = duplicate_lead.status
        duplicate_lead.status = Lead.Status.MERGED
        duplicate_lead.next_followup_at = None
        duplicate_lead.next_action = f"Merged into Lead #{target_lead.id} ({target_lead.name})"
        duplicate_lead.save()

        # Write status history
        LeadStatusHistory.objects.create(
            lead=duplicate_lead,
            old_status=old_status,
            new_status=Lead.Status.MERGED,
            changed_by=request.user,
            note=note or f"Merged into primary Lead #{target_lead.id} ({target_lead.name})",
        )

        # Link activities and surveys to target lead or record note on target lead
        LeadStatusHistory.objects.create(
            lead=target_lead,
            old_status=target_lead.status,
            new_status=target_lead.status,
            changed_by=request.user,
            note=f"Merged secondary lead #{duplicate_lead.id} ({duplicate_lead.name}, {duplicate_lead.phone}). Note: {note}",
        )

        return Response(
            {
                "message": f"Lead #{duplicate_lead.id} successfully merged into Lead #{target_lead.id}.",
                "duplicate_lead": LeadSerializer(duplicate_lead, context={'request': request}).data,
                "target_lead": LeadSerializer(target_lead, context={'request': request}).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=['get'], url_path='today')
    def today(self, request):
        qs = self.get_queryset().exclude(status__in=Lead.TERMINAL_STATUSES)

        # Follow-ups due today or overdue
        today_end = timezone.localtime().replace(hour=23, minute=59, second=59, microsecond=999999)
        qs = qs.filter(next_followup_at__isnull=False, next_followup_at__lte=today_end)
        qs = qs.order_by('next_followup_at')

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='import-csv')
    def import_csv(self, request):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"error": "No file uploaded. Please upload a CSV file with key 'file'."}, status=400)

        try:
            decoded_file = file_obj.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(decoded_file))
        except Exception as e:
            return Response({"error": f"Invalid CSV file format: {str(e)}"}, status=400)

        created_count = 0
        errors = []

        for row_idx, row in enumerate(reader, start=2):
            try:
                name = row.get('name', '').strip()
                phone = row.get('phone', '').strip()
                if not name or not phone:
                    errors.append({"row": row_idx, "error": "Both 'name' and 'phone' are required fields."})
                    continue

                # Duplicate check
                normalized = normalize_phone(phone)
                if find_duplicate_lead(normalized):
                    errors.append({"row": row_idx, "error": f"Duplicate phone number '{phone}' already exists."})
                    continue

                # Optional source resolution
                source_obj = None
                source_name = row.get('source', '').strip()
                if source_name:
                    source_obj, _ = LeadSource.objects.get_or_create(name=source_name)

                # Assigned user
                assigned_to = None
                assigned_username = row.get('assigned_to', '').strip()
                if assigned_username:
                    assigned_to = User.objects.filter(username=assigned_username).first()
                elif request.user.role == User.Role.SALESPERSON:
                    assigned_to = request.user

                monthly_bill = None
                bill_str = row.get('monthly_bill', '').strip()
                if bill_str:
                    try:
                        monthly_bill = float(bill_str)
                    except ValueError:
                        pass

                Lead.objects.create(
                    name=name,
                    phone=phone,
                    alt_phone=row.get('alt_phone', '').strip(),
                    email=row.get('email', '').strip(),
                    address=row.get('address', '').strip(),
                    city=row.get('city', '').strip(),
                    pincode=row.get('pincode', '').strip(),
                    property_type=row.get('property_type', '').strip(),
                    monthly_bill=monthly_bill,
                    roof_type=row.get('roof_type', '').strip(),
                    owner_or_tenant=row.get('owner_or_tenant', '').strip(),
                    source=source_obj,
                    assigned_to=assigned_to,
                    status=row.get('status', '').strip() or Lead.Status.NEW,
                    next_action="Initial contact required",
                    next_followup_at=timezone.now() + timezone.timedelta(days=1),
                )
                created_count += 1
            except Exception as e:
                errors.append({"row": row_idx, "error": str(e)})

        return Response(
            {
                "created_count": created_count,
                "error_count": len(errors),
                "errors": errors,
            },
            status=status.HTTP_201_CREATED if created_count > 0 else status.HTTP_400_BAD_REQUEST,
        )


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

        now = timezone.now()
        local_now = timezone.localtime()

        # 1. Counts by status
        status_counts = {item['status']: item['count'] for item in qs.values('status').annotate(count=Count('id'))}

        # 2. Funnel counts
        funnel = {
            'new': qs.filter(status=Lead.Status.NEW).count(),
            'interested': qs.filter(
                status__in=[
                    Lead.Status.INTERESTED,
                    Lead.Status.FOLLOW_UP,
                    Lead.Status.CALLBACK_SCHEDULED,
                    Lead.Status.ATTEMPTING_CONTACT,
                ]
            ).count(),
            'survey': qs.filter(
                status__in=[
                    Lead.Status.SURVEY_TO_SCHEDULE,
                    Lead.Status.SURVEY_SCHEDULED,
                    Lead.Status.SURVEY_RESCHEDULED,
                    Lead.Status.SURVEY_MISSED,
                    Lead.Status.DESIGN_PENDING,
                    Lead.Status.ALTERNATIVE,
                ]
            ).count(),
            'quote_sent': qs.filter(
                status__in=[
                    Lead.Status.QUOTE_SENT,
                    Lead.Status.REVISING_QUOTE,
                    Lead.Status.NEGOTIATION,
                ]
            ).count(),
            'won': qs.filter(status=Lead.Status.WON).count(),
        }

        # 3. Overdue follow-ups
        overdue_followups = qs.filter(
            next_followup_at__isnull=False,
            next_followup_at__lt=now,
        ).exclude(status__in=Lead.TERMINAL_STATUSES).count()

        # 4. Leads per source
        source_counts = [
            {
                'source': item['source__name'] or 'Unspecified',
                'count': item['count']
            }
            for item in qs.values('source__name').annotate(count=Count('id')).order_by('-count')
        ]

        # 5. Won count for this month
        won_this_month = qs.filter(
            status=Lead.Status.WON,
            won_at__year=local_now.year,
            won_at__month=local_now.month,
        ).count()

        return Response({
            'status_counts': status_counts,
            'funnel': funnel,
            'overdue_followups': overdue_followups,
            'leads_per_source': source_counts,
            'won_this_month': won_this_month,
            'total_active_leads': qs.exclude(status__in=Lead.TERMINAL_STATUSES).count(),
        })
