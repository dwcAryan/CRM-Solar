from django.contrib import admin

from .models import Activity


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = (
        'lead',
        'type',
        'outcome',
        'status_after',
        'next_action',
        'next_followup_at',
        'created_by',
        'created_at',
    )
    list_filter = ('type', 'outcome__stage', 'created_at')
    search_fields = ('lead__name', 'lead__phone', 'notes', 'next_action')
    readonly_fields = ('created_at',)
