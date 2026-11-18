from rest_framework import serializers

from .models import Survey, SurveyPhoto


class SurveyPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyPhoto
        fields = ['id', 'survey', 'image', 'caption', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']


class SurveySerializer(serializers.ModelSerializer):
    photos = SurveyPhotoSerializer(many=True, read_only=True)
    lead_name = serializers.CharField(source='lead.name', read_only=True)
    surveyor_name = serializers.CharField(source='surveyor.get_full_name', read_only=True)

    class Meta:
        model = Survey
        fields = [
            'id',
            'lead',
            'lead_name',
            'scheduled_at',
            'surveyor',
            'surveyor_name',
            'status',
            'site_suitable',
            'notes',
            'remark',
            'reschedule_count',
            'photos',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'reschedule_count', 'created_at', 'updated_at']


class BookSurveyInputSerializer(serializers.Serializer):
    lead_id = serializers.IntegerField(required=True)
    scheduled_at = serializers.DateTimeField(required=True)
    surveyor_id = serializers.IntegerField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, default='')
    remark = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')


class RescheduleSurveyInputSerializer(serializers.Serializer):
    scheduled_at = serializers.DateTimeField(required=True)
    notes = serializers.CharField(required=False, allow_blank=True, default='')
    remark = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')


class MarkDoneSurveyInputSerializer(serializers.Serializer):
    site_suitable = serializers.BooleanField(required=True)
    notes = serializers.CharField(required=False, allow_blank=True, default='')
    remark = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')
    lost_reason_id = serializers.IntegerField(required=False, allow_null=True)
