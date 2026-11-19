from rest_framework import serializers

from .models import Activity


class ActivitySerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    correction_added_by_name = serializers.CharField(source='correction_added_by.get_full_name', read_only=True)
    outcome_name = serializers.CharField(source='outcome.name', read_only=True)
    lead_name = serializers.CharField(source='lead.name', read_only=True)
    rendered_text = serializers.SerializerMethodField()

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
            'admin_correction_note',
            'correction_added_by',
            'correction_added_by_name',
            'correction_added_at',
            'message_code',
            'params',
            'rendered_text',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'correction_added_at', 'correction_added_by']

    def get_rendered_text(self, obj):
        from leads.history_renderer import render_history_text
        request = self.context.get('request')
        lang = getattr(request, 'LANGUAGE_CODE', 'en') if request else 'en'
        fallback = obj.notes or obj.remark or (f"{obj.type}: {obj.outcome.name if obj.outcome else ''}")
        return render_history_text(obj.message_code, obj.params, language=lang, fallback_text=fallback)
