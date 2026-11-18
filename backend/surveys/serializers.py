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
    lead_phone = serializers.CharField(source='lead.phone', read_only=True)
    lead_phone_e164 = serializers.CharField(source='lead.phone_e164', read_only=True)
    lead_address = serializers.CharField(source='lead.address', read_only=True)
    lead_city = serializers.CharField(source='lead.city', read_only=True)
    lead_pincode = serializers.CharField(source='lead.pincode', read_only=True)
    lead_roof_type = serializers.CharField(source='lead.roof_type.name', read_only=True, default='')
    lead_property_type = serializers.CharField(source='lead.property_type.name', read_only=True, default='')
    surveyor_name = serializers.CharField(source='surveyor.get_full_name', read_only=True)

    class Meta:
        model = Survey
        fields = [
            'id',
            'lead',
            'lead_name',
            'lead_phone',
            'lead_phone_e164',
            'lead_address',
            'lead_city',
            'lead_pincode',
            'lead_roof_type',
            'lead_property_type',
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

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get('request')
        if request and getattr(request, 'user', None) and getattr(request.user, 'role', None) == 'surveyor':
            # Strip sales remarks for surveyor
            ret.pop('remark', None)
        return ret


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
