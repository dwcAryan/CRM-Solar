import re
from rest_framework import serializers

from .models import AISuggestion, AuditLog, ImportBatch, Lead, LeadStatusHistory
from .phone_utils import normalize_phone_number
from .timezone_utils import check_calling_hours, format_datetime_in_timezone, get_default_timezone_for_state
from .utils import find_duplicate_lead


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = [
            'id',
            'user',
            'user_name',
            'action',
            'timestamp',
            'lead',
            'lead_id_recorded',
            'reason',
            'details',
            'ip_address',
        ]
        read_only_fields = ['id', 'timestamp']


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
    region_code = serializers.CharField(source='region.code', read_only=True)
    region_name = serializers.CharField(source='region.name', read_only=True)
    currency = serializers.CharField(source='region.currency', read_only=True)
    currency_symbol = serializers.CharField(source='region.currency_symbol', read_only=True)
    status_history = LeadStatusHistorySerializer(many=True, read_only=True)

    phone_display = serializers.SerializerMethodField()
    alt_phone_display = serializers.SerializerMethodField()
    is_within_calling_hours = serializers.SerializerMethodField()
    calling_hours_reason = serializers.SerializerMethodField()
    next_followup_display = serializers.SerializerMethodField()
    user_next_followup_display = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = [
            'id',
            'region',
            'region_code',
            'region_name',
            'currency',
            'currency_symbol',
            'state_ref',
            'state',
            'timezone',
            'name',
            'phone',
            'phone_e164',
            'phone_display',
            'alt_phone',
            'alt_phone_e164',
            'alt_phone_display',
            'email',
            'address',
            'city',
            'suburb',
            'pincode',
            'postcode',
            'source',
            'source_name',
            'property_type',
            'roof_type',
            'owner_or_tenant',
            'bill_amount',
            'bill_period',
            'normalized_monthly_bill',
            'monthly_bill',
            'electricity_provider',
            'consent_status',
            'consent_source',
            'consent_date',
            'opt_out_calls',
            'opt_out_sms',
            'opt_out_whatsapp',
            'opt_out_email',
            'dncr_status',
            'dncr_checked_at',
            'assigned_to',
            'assigned_to_name',
            'status',
            'next_action',
            'next_followup_at',
            'next_followup_display',
            'user_next_followup_display',
            'is_within_calling_hours',
            'calling_hours_reason',
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
        read_only_fields = [
            'id',
            'phone_e164',
            'phone_display',
            'alt_phone_e164',
            'alt_phone_display',
            'normalized_monthly_bill',
            'created_at',
            'updated_at',
            'won_at',
        ]

    def get_phone_display(self, obj) -> str:
        if obj.phone_e164:
            _, disp, _ = normalize_phone_number(obj.phone_e164, obj.region_id or 'IN')
            return disp or obj.phone_e164
        return obj.phone

    def get_alt_phone_display(self, obj) -> str:
        if obj.alt_phone_e164:
            _, disp, _ = normalize_phone_number(obj.alt_phone_e164, obj.region_id or 'IN')
            return disp or obj.alt_phone_e164
        return obj.alt_phone or ""

    def get_is_within_calling_hours(self, obj) -> bool:
        allowed, _ = check_calling_hours(obj)
        return allowed

    def get_calling_hours_reason(self, obj) -> str:
        _, reason = check_calling_hours(obj)
        return reason

    def get_next_followup_display(self, obj) -> str:
        if not obj.next_followup_at:
            return ""
        return format_datetime_in_timezone(obj.next_followup_at, obj.timezone)

    def get_user_next_followup_display(self, obj) -> str:
        if not obj.next_followup_at:
            return ""
        request = self.context.get('request')
        user_tz = request.user.default_timezone if request and request.user and request.user.is_authenticated else None
        return format_datetime_in_timezone(obj.next_followup_at, user_tz or 'Asia/Kolkata')

    def validate(self, attrs):
        request = self.context.get('request')
        user = request.user if request else None

        # 1. Resolve region
        region = attrs.get('region')
        if not region and self.instance:
            region = self.instance.region
        if not region and user and getattr(user, 'default_region', None):
            region = user.default_region
            attrs['region'] = region

        region_code = region.code if region else 'IN'

        # 2. Validate phone number
        phone = attrs.get('phone')
        if phone:
            e164, disp, err = normalize_phone_number(phone, region_code)
            if err or not e164:
                raise serializers.ValidationError({'phone': err or 'Invalid phone number format.'})
            attrs['phone_e164'] = e164
            attrs['phone'] = e164
            if not self.instance or not self.instance.phone_raw_backup:
                attrs['phone_raw_backup'] = str(phone)

        # 3. Validate alt_phone
        alt_phone = attrs.get('alt_phone')
        if alt_phone:
            alt_e164, _, alt_err = normalize_phone_number(alt_phone, region_code)
            if alt_err or not alt_e164:
                raise serializers.ValidationError({'alt_phone': alt_err or 'Invalid alternate phone format.'})
            attrs['alt_phone_e164'] = alt_e164
            attrs['alt_phone'] = alt_e164

        # 4. Address validation per region
        if region_code == 'AU':
            postcode = attrs.get('postcode') or attrs.get('pincode')
            if postcode:
                clean_postcode = re.sub(r'\D', '', str(postcode))
                if len(clean_postcode) != 4:
                    raise serializers.ValidationError({'postcode': 'Australian postcodes must be exactly 4 digits.'})
                attrs['postcode'] = clean_postcode
                attrs['pincode'] = clean_postcode
        elif region_code == 'IN':
            pincode = attrs.get('pincode')
            if pincode:
                clean_pincode = re.sub(r'\D', '', str(pincode))
                if len(clean_pincode) != 6:
                    raise serializers.ValidationError({'pincode': 'Indian pincodes must be exactly 6 digits.'})
                attrs['pincode'] = clean_pincode

        # 5. Timezone derivation
        if not attrs.get('timezone'):
            state_val = attrs.get('state') or (self.instance.state if self.instance else "")
            derived_tz = get_default_timezone_for_state(region_code, state_val)
            attrs['timezone'] = derived_tz

        # 6. Duplicate check across regions using E.164
        instance_id = self.instance.id if self.instance else None
        phone_to_check = attrs.get('phone_e164') or attrs.get('phone')
        if phone_to_check:
            duplicate = find_duplicate_lead(phone_to_check, exclude_id=instance_id, region=region_code)
            force_create = request and request.query_params.get('force') == 'true'
            if duplicate and not force_create and not instance_id:
                raise serializers.ValidationError({
                    'phone': f"A lead with this phone number already exists in {duplicate.region_id or 'CRM'}: #{duplicate.id} ({duplicate.name}).",
                    'duplicate': True,
                    'existing_lead': {
                        'id': duplicate.id,
                        'name': duplicate.name,
                        'phone': duplicate.phone_e164 or duplicate.phone,
                        'region': duplicate.region_id,
                        'status': duplicate.status,
                        'assigned_to': duplicate.assigned_to.username if duplicate.assigned_to else None,
                    }
                })

        return attrs


class LogActivityInputSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=['call', 'whatsapp', 'sms', 'visit', 'note'])
    outcome_id = serializers.IntegerField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, default='')
    remark = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')
    status = serializers.CharField(required=False, allow_blank=True)
    next_action = serializers.CharField(required=False, allow_blank=True)
    next_followup_at = serializers.DateTimeField(required=False, allow_null=True)
    lost_reason_id = serializers.IntegerField(required=False, allow_null=True)
    nurture_reason_id = serializers.IntegerField(required=False, allow_null=True)
    calling_hours_override_reason = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')


class AnonymizeLeadInputSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, min_length=3)


class PrivacyCorrectInputSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, min_length=3)
    updates = serializers.DictField(required=True)


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
