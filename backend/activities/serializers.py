from rest_framework import serializers

from .models import Activity


class ActivitySerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    outcome_name = serializers.CharField(source='outcome.name', read_only=True)
    lead_name = serializers.CharField(source='lead.name', read_only=True)

    class Meta:
        model = Activity
        fields = [
            'id',
            'lead',
            'lead_name',
            'type',
            'outcome',
            'outcome_name',
            'notes',
            'remark',
            'status_after',
            'next_action',
            'next_followup_at',
            'created_by',
            'created_by_name',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']
