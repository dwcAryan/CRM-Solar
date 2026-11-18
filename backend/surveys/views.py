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
from accounts.permissions import SurveyPermission, can_user_mark_lost
from activities.models import Activity
from leads.models import Lead, LeadStatusHistory
from masters.models import LostReason, Outcome

from .models import Survey, SurveyPhoto
from .serializers import (
    BookSurveyInputSerializer,
    MarkDoneSurveyInputSerializer,
    RescheduleSurveyInputSerializer,
    SurveyPhotoSerializer,
    SurveySerializer,
)


class SurveyViewSet(viewsets.ModelViewSet):
    queryset = Survey.objects.all().select_related('lead', 'surveyor').prefetch_related('photos').order_by('-scheduled_at')
    serializer_class = SurveySerializer
    permission_classes = [SurveyPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'site_suitable', 'surveyor', 'lead']
    search_fields = ['lead__name', 'lead__phone', 'notes']
    ordering_fields = ['scheduled_at', 'created_at', 'id']

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if not user.is_authenticated:
            return qs.none()
        if user.role == User.Role.SURVEYOR and not user.is_superuser:
            return qs.filter(surveyor=user)
        if user.role == User.Role.SALESPERSON and not user.is_superuser:
            return qs.filter(lead__assigned_to=user)
        return qs

    @action(detail=False, methods=['post'], url_path='book')
    @transaction.atomic
    def book(self, request):
        serializer = BookSurveyInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        lead_id = serializer.validated_data['lead_id']
        scheduled_at = serializer.validated_data['scheduled_at']
        surveyor_id = serializer.validated_data.get('surveyor_id')
        notes = serializer.validated_data.get('notes', '')
        remark = serializer.validated_data.get('remark', '') or notes

        try:
            lead = Lead.objects.get(id=lead_id)
        except Lead.DoesNotExist:
            return Response({"lead_id": "Lead not found."}, status=status.HTTP_404_NOT_FOUND)

        surveyor = None
        if surveyor_id:
            surveyor = User.objects.filter(id=surveyor_id).first()

        survey = Survey.objects.create(
            lead=lead,
            scheduled_at=scheduled_at,
            surveyor=surveyor,
            status=Survey.Status.BOOKED,
            notes=notes,
            remark=remark[:500],
        )

        target_status = Lead.Status.SURVEY_SCHEDULED
        next_action_text = "Send reminder the day before"
        old_status = lead.status

        # Update lead
        lead.status = target_status
        lead.next_action = next_action_text
        lead.next_followup_at = scheduled_at
        if remark:
            lead.remark = remark[:500]
        lead.save()

        # Write history and activity
        LeadStatusHistory.objects.create(
            lead=lead,
            old_status=old_status,
            new_status=target_status,
            changed_by=request.user,
            note=notes or f"Survey booked for {scheduled_at.strftime('%Y-%m-%d %H:%M')}",
            remark=remark[:500],
        )

        outcome_obj = Outcome.objects.filter(stage=Outcome.Stage.SURVEY, name__icontains='Survey booked').first()
        Activity.objects.create(
            lead=lead,
            type=Activity.Type.VISIT,
            outcome=outcome_obj,
            notes=notes or f"Survey booked for {scheduled_at.strftime('%Y-%m-%d %H:%M')}",
            remark=remark[:500],
            status_after=target_status,
            next_action=next_action_text,
            next_followup_at=scheduled_at,
            created_by=request.user,
        )

        return Response(SurveySerializer(survey, context={'request': request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='reschedule')
    @transaction.atomic
    def reschedule(self, request, pk=None):
        survey = self.get_object()
        serializer = RescheduleSurveyInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        scheduled_at = serializer.validated_data['scheduled_at']
        notes = serializer.validated_data.get('notes', '')
        remark = serializer.validated_data.get('remark', '') or notes

        survey.reschedule_count += 1
        survey.scheduled_at = scheduled_at
        survey.status = Survey.Status.RESCHEDULED
        if notes:
            survey.notes = f"{survey.notes}\n[Rescheduled]: {notes}".strip()
        if remark:
            survey.remark = remark[:500]
        survey.save()

        lead = survey.lead
        old_status = lead.status
        target_status = Lead.Status.SURVEY_RESCHEDULED
        next_action_text = "Book a new date, update reminder"

        lead.status = target_status
        lead.next_action = next_action_text
        lead.next_followup_at = scheduled_at
        if remark:
            lead.remark = remark[:500]
        lead.save()

        LeadStatusHistory.objects.create(
            lead=lead,
            old_status=old_status,
            new_status=target_status,
            changed_by=request.user,
            note=notes or f"Survey rescheduled to {scheduled_at.strftime('%Y-%m-%d %H:%M')}",
            remark=remark[:500],
        )

        outcome_obj = Outcome.objects.filter(stage=Outcome.Stage.SURVEY, name__icontains='reschedule').first()
        Activity.objects.create(
            lead=lead,
            type=Activity.Type.VISIT,
            outcome=outcome_obj,
            notes=notes or f"Survey rescheduled (count: {survey.reschedule_count}) to {scheduled_at.strftime('%Y-%m-%d %H:%M')}",
            remark=remark[:500],
            status_after=target_status,
            next_action=next_action_text,
            next_followup_at=scheduled_at,
            created_by=request.user,
        )

        return Response(SurveySerializer(survey, context={'request': request}).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='mark-missed')
    @transaction.atomic
    def mark_missed(self, request, pk=None):
        survey = self.get_object()
        notes = request.data.get('notes', '')
        remark = request.data.get('remark', '') or notes

        survey.status = Survey.Status.MISSED
        if notes:
            survey.notes = f"{survey.notes}\n[Missed]: {notes}".strip()
        if remark:
            survey.remark = remark[:500]
        survey.save()

        lead = survey.lead
        old_status = lead.status
        target_status = Lead.Status.SURVEY_MISSED
        next_action_text = "Call, rebook, note the missed visit"
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
            note=notes or "Customer not at site or not reachable on the day",
            remark=remark[:500],
        )

        outcome_obj = Outcome.objects.filter(stage=Outcome.Stage.SURVEY, name__icontains='not at site').first()
        Activity.objects.create(
            lead=lead,
            type=Activity.Type.VISIT,
            outcome=outcome_obj,
            notes=notes or "Survey marked missed: customer unreachable at site",
            remark=remark[:500],
            status_after=target_status,
            next_action=next_action_text,
            next_followup_at=next_followup,
            created_by=request.user,
        )

        return Response(SurveySerializer(survey, context={'request': request}).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='cancel-by-surveyor')
    @transaction.atomic
    def cancel_by_surveyor(self, request, pk=None):
        survey = self.get_object()
        notes = request.data.get('notes', '')
        remark = request.data.get('remark', '') or notes

        survey.status = Survey.Status.RESCHEDULED
        if notes:
            survey.notes = f"{survey.notes}\n[Cancelled by surveyor]: {notes}".strip()
        if remark:
            survey.remark = remark[:500]
        survey.save()

        lead = survey.lead
        old_status = lead.status
        target_status = Lead.Status.SURVEY_RESCHEDULED
        next_action_text = "Inform the customer and rebook"
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
            note=notes or "Surveyor cancelled or delayed",
            remark=remark[:500],
        )

        outcome_obj = Outcome.objects.filter(stage=Outcome.Stage.SURVEY, name__icontains='Surveyor cancels').first()
        Activity.objects.create(
            lead=lead,
            type=Activity.Type.VISIT,
            outcome=outcome_obj,
            notes=notes or "Surveyor cancelled/delayed, reschedule needed",
            remark=remark[:500],
            status_after=target_status,
            next_action=next_action_text,
            next_followup_at=next_followup,
            created_by=request.user,
        )

        return Response(SurveySerializer(survey, context={'request': request}).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='mark-done')
    @transaction.atomic
    def mark_done(self, request, pk=None):
        survey = self.get_object()
        serializer = MarkDoneSurveyInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        site_suitable = serializer.validated_data['site_suitable']
        notes = serializer.validated_data.get('notes', '')
        remark = serializer.validated_data.get('remark', '') or notes
        lost_reason_id = serializer.validated_data.get('lost_reason_id')

        survey.status = Survey.Status.DONE
        survey.site_suitable = site_suitable
        if notes:
            survey.notes = f"{survey.notes}\n[Completed]: {notes}".strip()
        if remark:
            survey.remark = remark[:500]
        survey.save()

        lead = survey.lead
        old_status = lead.status
        now = timezone.now()

        if site_suitable:
            target_status = Lead.Status.DESIGN_PENDING
            next_action_text = "Prepare the design and quotation"
            next_followup = now + timedelta(days=2)
            outcome_obj = Outcome.objects.filter(stage=Outcome.Stage.SURVEY, name__icontains='site suitable').first()
        else:
            if lost_reason_id:
                if not can_user_mark_lost(request.user):
                    raise PermissionDenied("You do not have permission to mark this lead as Lost.")
                lost_reason = LostReason.objects.filter(id=lost_reason_id).first()
                target_status = Lead.Status.LOST
                lead.lost_reason = lost_reason
                next_action_text = "Record the reason: site not suitable"
                next_followup = None
                outcome_obj = Outcome.objects.filter(stage=Outcome.Stage.SURVEY, name__icontains='site not suitable').first()
            else:
                target_status = Lead.Status.ALTERNATIVE
                next_action_text = "Explain, offer a smaller system or another option, else record lost reason"
                next_followup = now + timedelta(days=2)
                outcome_obj = Outcome.objects.filter(stage=Outcome.Stage.SURVEY, name__icontains='site not suitable').first()

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
            note=notes or f"Survey marked done (Site suitable: {site_suitable})",
            remark=remark[:500],
        )

        Activity.objects.create(
            lead=lead,
            type=Activity.Type.VISIT,
            outcome=outcome_obj,
            notes=notes or f"Survey completed. Site suitable: {site_suitable}",
            remark=remark[:500],
            status_after=target_status,
            next_action=next_action_text,
            next_followup_at=next_followup,
            created_by=request.user,
        )

        return Response(SurveySerializer(survey, context={'request': request}).data, status=status.HTTP_200_OK)


class SurveyPhotoViewSet(viewsets.ModelViewSet):
    queryset = SurveyPhoto.objects.all().select_related('survey').order_by('-uploaded_at')
    serializer_class = SurveyPhotoSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['survey']
    ordering_fields = ['uploaded_at', 'id']
