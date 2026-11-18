from rest_framework import serializers

from .models import HelpbotQueryLog, HelpbotUnanswered


class HelpbotAskInputSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=500, required=True, trim_whitespace=True)
    context = serializers.DictField(required=False, default=dict)


class HelpbotFeedbackInputSerializer(serializers.Serializer):
    query_id = serializers.IntegerField(required=True)
    helpful = serializers.BooleanField(required=True)
    comment = serializers.CharField(required=False, allow_blank=True, default='', max_length=1000)


class HelpbotQueryLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = HelpbotQueryLog
        fields = [
            'id',
            'user',
            'user_name',
            'user_email',
            'question',
            'topic',
            'confidence',
            'in_scope',
            'provider',
            'answer',
            'response_time_ms',
            'helpful',
            'feedback_comment',
            'created_at',
        ]


class HelpbotUnansweredSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = HelpbotUnanswered
        fields = [
            'id',
            'question',
            'user',
            'user_name',
            'topic_guess',
            'confidence',
            'resolved',
            'created_at',
        ]
