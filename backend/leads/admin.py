from django.contrib import admin

from .models import AISuggestion, AuditLog, ImportBatch, Lead, LeadStatusHistory


class LeadStatusHistoryInline(admin.TabularInline):
    model = LeadStatusHistory
    extra = 0
    readonly_fields = ('old_status', 'new_status', 'changed_by', 'changed_at', 'note')
    can_delete = False


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'region',
        'phone_e164',
        'city',
        'state',
        'timezone',
        'status',
        'next_action',
        'next_followup_at',
        'assigned_to',
        'consent_status',
        'attempt_count',
        'created_at',
    )
    list_filter = ('region', 'status', 'assigned_to', 'source', 'consent_status', 'dncr_status', 'do_not_contact', 'created_at')
    search_fields = ('name', 'phone', 'phone_e164', 'alt_phone', 'email', 'city', 'pincode', 'postcode')
    inlines = [LeadStatusHistoryInline]
    readonly_fields = ('created_at', 'updated_at', 'won_at', 'phone_raw_backup', 'alt_phone_raw_backup')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'action', 'user_name', 'lead_id_recorded', 'ip_address')
    list_filter = ('action', 'timestamp')
    search_fields = ('user_name', 'action', 'reason')
    readonly_fields = ('user', 'user_name', 'action', 'timestamp', 'lead', 'lead_id_recorded', 'reason', 'details', 'ip_address')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LeadStatusHistory)
class LeadStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('lead', 'old_status', 'new_status', 'changed_by', 'changed_at')
    list_filter = ('old_status', 'new_status', 'changed_at')
    search_fields = ('lead__name', 'lead__phone', 'note')
    readonly_fields = ('lead', 'old_status', 'new_status', 'changed_by', 'changed_at', 'note')


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'file_name',
        'imported_by',
        'imported_count',
        'skipped_count',
        'duplicate_count',
        'failed_count',
        'is_reverted',
        'imported_at',
    )
    list_filter = ('is_reverted', 'imported_at')
    search_fields = ('file_name', 'imported_by__username')
    readonly_fields = ('imported_at', 'reverted_at', 'reverted_by')


@admin.register(AISuggestion)
class AISuggestionAdmin(admin.ModelAdmin):
    list_display = ('lead', 'provider', 'model', 'tokens_used', 'is_fallback', 'generated_at')
    list_filter = ('provider', 'is_fallback', 'generated_at')
    search_fields = ('lead__name', 'lead__city', 'model')
    readonly_fields = ('generated_at', 'input_hash', 'output_json')
