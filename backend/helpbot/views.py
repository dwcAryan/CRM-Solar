import logging
import time

from django.core.management import call_command
from django.db.models import Avg, Count
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import HelpbotQueryLog, HelpbotUnanswered
from .nlp import Normalizer, get_helpbot_engine
from .serializers import (
    HelpbotAskInputSerializer,
    HelpbotFeedbackInputSerializer,
    HelpbotUnansweredSerializer,
)

logger = logging.getLogger(__name__)


def is_admin_or_manager(user) -> bool:
    role = getattr(user, 'role', '')
    return role in ['admin', 'manager'] or user.is_staff or user.is_superuser


class HelpbotAskView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = HelpbotAskInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        raw_query = serializer.validated_data['query']
        user_role = getattr(request.user, 'role', 'salesperson')
        user_region = getattr(request.user, 'primary_region_id', 'IN') or 'IN'

        t0 = time.time()
        engine = get_helpbot_engine()
        result = engine.process_query(raw_query, user_role=user_role, user_region=user_region)
        elapsed_ms = int((time.time() - t0) * 1000)

        # Log query with scrubbed PII
        scrubbed_question = Normalizer.scrub_pii(raw_query)[:500]
        query_log = HelpbotQueryLog.objects.create(
            user=request.user,
            question=scrubbed_question,
            topic=result['topic'],
            confidence=result['confidence'],
            in_scope=not result['is_refusal'],
            provider='local',
            answer=result['answer'],
            response_time_ms=elapsed_ms,
        )

        # Record unanswered if refusal or very low confidence
        if result['is_refusal'] or result['confidence'] < 0.35:
            HelpbotUnanswered.objects.create(
                question=scrubbed_question,
                user=request.user,
                topic_guess=result['topic'],
                confidence=result['confidence'],
            )

        return Response({
            'query_id': query_log.id,
            'answer': result['answer'],
            'topic': result['topic'],
            'confidence': result['confidence'],
            'is_refusal': result['is_refusal'],
            'suggested_questions': result['suggested_questions'],
            'tour': result['tour'],
            'response_time_ms': elapsed_ms,
        })


class HelpbotSuggestionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_role = getattr(request.user, 'role', 'salesperson')
        engine = get_helpbot_engine()
        starters = engine.get_contextual_starters(user_role)
        return Response({'suggestions': starters})


class HelpbotFeedbackView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = HelpbotFeedbackInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        query_id = serializer.validated_data['query_id']
        helpful = serializer.validated_data['helpful']
        comment = serializer.validated_data.get('comment', '')

        try:
            log_entry = HelpbotQueryLog.objects.get(id=query_id)
            log_entry.helpful = helpful
            log_entry.feedback_comment = comment
            log_entry.save(update_fields=['helpful', 'feedback_comment'])

            # If user voted unhelpful, track in HelpbotUnanswered
            if not helpful:
                HelpbotUnanswered.objects.get_or_create(
                    question=log_entry.question,
                    defaults={
                        'user': log_entry.user,
                        'topic_guess': log_entry.topic,
                        'confidence': log_entry.confidence,
                    }
                )

            return Response({'status': 'success', 'helpful': helpful})
        except HelpbotQueryLog.DoesNotExist:
            return Response({'error': 'Query log not found'}, status=status.HTTP_404_NOT_FOUND)


class HelpbotUnansweredView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_admin_or_manager(request.user):
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        status_filter = request.query_params.get('resolved')
        qs = HelpbotUnanswered.objects.select_related('user').all()
        if status_filter is not None:
            qs = qs.filter(resolved=(status_filter.lower() == 'true'))

        serializer = HelpbotUnansweredSerializer(qs[:100], many=True)
        return Response(serializer.data)

    def patch(self, request, pk=None):
        if not is_admin_or_manager(request.user):
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        try:
            entry = HelpbotUnanswered.objects.get(pk=pk)
            resolved = request.data.get('resolved')
            if resolved is not None:
                entry.resolved = bool(resolved)
                entry.save(update_fields=['resolved'])
            return Response({'status': 'success', 'resolved': entry.resolved})
        except HelpbotUnanswered.DoesNotExist:
            return Response({'error': 'Item not found'}, status=status.HTTP_404_NOT_FOUND)


class HelpbotStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_admin_or_manager(request.user):
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        total_queries = HelpbotQueryLog.objects.count()
        refusal_count = HelpbotQueryLog.objects.filter(in_scope=False).count()
        positive_feedback = HelpbotQueryLog.objects.filter(helpful=True).count()
        negative_feedback = HelpbotQueryLog.objects.filter(helpful=False).count()
        total_feedback = positive_feedback + negative_feedback
        helpful_rate = (positive_feedback / total_feedback * 100) if total_feedback > 0 else 100.0

        avg_latency = HelpbotQueryLog.objects.aggregate(Avg('response_time_ms'))['response_time_ms__avg'] or 0

        # Topic distribution
        topics = (
            HelpbotQueryLog.objects.values('topic')
            .annotate(count=Count('id'))
            .order_by('-count')[:8]
        )

        unresolved_count = HelpbotUnanswered.objects.filter(resolved=False).count()

        return Response({
            'total_queries': total_queries,
            'refusal_count': refusal_count,
            'refusal_rate': round(refusal_count / total_queries * 100, 1) if total_queries > 0 else 0.0,
            'positive_feedback': positive_feedback,
            'negative_feedback': negative_feedback,
            'helpful_rate': round(helpful_rate, 1),
            'avg_latency_ms': round(avg_latency, 1),
            'unresolved_count': unresolved_count,
            'top_topics': list(topics),
        })


class HelpbotRebuildIndexView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if getattr(request.user, 'role', '') != 'admin' and not request.user.is_superuser:
            return Response({'detail': 'Admin permission required'}, status=status.HTTP_403_FORBIDDEN)

        try:
            call_command('build_helpbot_index', force=True)
            return Response({'status': 'success', 'message': 'Helpbot knowledge index rebuilt successfully.'})
        except Exception as e:
            logger.error("Failed to rebuild index: %s", e)
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
