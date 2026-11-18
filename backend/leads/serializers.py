from rest_framework import serializers

from .models import AISuggestion, ImportBatch, Lead, LeadStatusHistory
from .utils import find_duplicate_lead


class LeadStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source='changed_by.get_full_name', read_only=True)

    class Meta:
        model = LeadStatusHistory
        fields = [
            'id',
            'lead',
            'old_status',
            'new_status',
            'changed_by',
            'changed_by_name',
            'changed_at',
            'note',
            'remark',
        ]
        read_only_fields = ['id', 'changed_at']


class LeadSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source='source.name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    lost_reason_name = serializers.CharField(source='lost_reason.name', read_only=True)
    nurture_reason_name = serializers.CharField(source='nurture_reason.name', read_only=True)
    status_history = LeadStatusHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Lead
        fields = [
            'id',
            'name',
            'phone',
            'alt_phone',
            'email',
            'address',
            'city',
            'pincode',
            'source',
            'source_name',
            'property_type',
            'monthly_bill',
            'roof_type',
            'owner_or_tenant',
            'assigned_to',
            'assigned_to_name',
            'status',
            'next_action',
            'next_followup_at',
            'lost_reason',
            'lost_reason_name',
            'nurture_reason',
            'nurture_reason_name',
            'do_not_contact',
            'attempt_count',
            'won_at',
            'import_batch',
            'remark',
            'status_history',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'won_at']

    def validate(self, attrs):
        phone = attrs.get('phone')
        instance_id = self.instance.id if self.instance else None

        # Check for duplicate on create (or if phone is updated)
        if phone:
            duplicate = find_duplicate_lead(phone, exclude_id=instance_id)
            # Allow force_create flag if needed
            force_create = self.context.get('request') and self.context['request'].query_params.get('force') == 'true'
            if duplicate and not force_create and not instance_id:
                raise serializers.ValidationError({
                    'phone': 'A lead with this phone number already exists.',
                    'duplicate': True,
                    'existing_lead': {
                        'id': duplicate.id,
                        'name': duplicate.name,
                        'phone': duplicate.phone,
                        'status': duplicate.status,
                        'assigned_to': duplicate.assigned_to.username if duplicate.assigned_to else None,
                    }
                })

        return attrs


class LogActivityInputSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=['call', 'whatsapp', 'visit', 'note'])
    outcome_id = serializers.IntegerField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, default='')
    remark = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')
    status = serializers.CharField(required=False, allow_blank=True)
    next_action = serializers.CharField(required=False, allow_blank=True)
    next_followup_at = serializers.DateTimeField(required=False, allow_null=True)
    lost_reason_id = serializers.IntegerField(required=False, allow_null=True)
    nurture_reason_id = serializers.IntegerField(required=False, allow_null=True)


class MergeLeadInputSerializer(serializers.Serializer):
    target_lead_id = serializers.IntegerField(required=True)
    note = serializers.CharField(required=False, allow_blank=True, default='')
    remark = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')


class AddRemarkInputSerializer(serializers.Serializer):
    remark = serializers.CharField(max_length=500, required=True, allow_blank=False)


class BulkActionSerializer(serializers.Serializer):
    lead_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
    )
    action = serializers.ChoiceField(choices=['assign', 'change_source'])
    value = serializers.IntegerField(required=True)
    remark = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')


class ImportBatchSerializer(serializers.ModelSerializer):
    imported_by_name = serializers.CharField(source='imported_by.get_full_name', read_only=True)
    reverted_by_name = serializers.CharField(source='reverted_by.get_full_name', read_only=True)

    class Meta:
        model = ImportBatch
        fields = [
            'id',
            'file_name',
            'imported_by',
            'imported_by_name',
            'imported_at',
            'total_rows',
            'imported_count',
            'skipped_count',
            'duplicate_count',
            'failed_count',
            'is_reverted',
            'reverted_at',
            'reverted_by',
            'reverted_by_name',
            'failed_rows_json',
        ]
        read_only_fields = ['id', 'imported_at', 'reverted_at', 'reverted_by']


class AISuggestionSerializer(serializers.ModelSerializer):
    generated_by_name = serializers.CharField(source='generated_by.get_full_name', read_only=True)

    class Meta:
        model = AISuggestion
        fields = [
            'id',
            'lead',
            'generated_by',
            'generated_by_name',
            'generated_at',
            'provider',
            'model',
            'input_hash',
            'output_json',
            'tokens_used',
            'is_fallback',
            'error_message',
        ]
        read_only_fields = fields
