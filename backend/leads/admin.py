from django.contrib import admin

from .models import Lead, LeadStatusHistory


class LeadStatusHistoryInline(admin.TabularInline):
    model = LeadStatusHistory
    extra = 0
    readonly_fields = ('old_status', 'new_status', 'changed_by', 'changed_at', 'note')
    can_delete = False


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'phone',
        'city',
        'status',
        'next_action',
        'next_followup_at',
        'assigned_to',
        'source',
        'attempt_count',
        'created_at',
    )
    list_filter = ('status', 'assigned_to', 'source', 'do_not_contact', 'created_at')
    search_fields = ('name', 'phone', 'alt_phone', 'email', 'city', 'pincode')
    inlines = [LeadStatusHistoryInline]
    readonly_fields = ('created_at', 'updated_at', 'won_at')


@admin.register(LeadStatusHistory)
class LeadStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('lead', 'old_status', 'new_status', 'changed_by', 'changed_at')
    list_filter = ('old_status', 'new_status', 'changed_at')
    search_fields = ('lead__name', 'lead__phone', 'note')
    readonly_fields = ('lead', 'old_status', 'new_status', 'changed_by', 'changed_at', 'note')
