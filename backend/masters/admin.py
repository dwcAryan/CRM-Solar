from django.contrib import admin

from .models import LeadSource, LostReason, NurtureReason, Outcome, PolicySettings


@admin.register(Outcome)
class OutcomeAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'stage',
        'default_status',
        'default_next_action',
        'default_followup_days',
        'followup_date_required_manually',
        'is_terminal',
        'requires_lost_reason',
        'requires_nurture_reason',
        'sort_order',
        'is_active',
    )
    list_filter = ('stage', 'is_terminal', 'is_active')
    search_fields = ('name', 'default_status', 'default_next_action')
    ordering = ('stage', 'sort_order')


@admin.register(LostReason)
class LostReasonAdmin(admin.ModelAdmin):
    list_display = ('name', 'sort_order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    ordering = ('sort_order', 'name')


@admin.register(NurtureReason)
class NurtureReasonAdmin(admin.ModelAdmin):
    list_display = ('name', 'sort_order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    ordering = ('sort_order', 'name')


@admin.register(LeadSource)
class LeadSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'sort_order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    ordering = ('sort_order', 'name')


@admin.register(PolicySettings)
class PolicySettingsAdmin(admin.ModelAdmin):
    list_display = (
        'max_call_attempts_before_unreachable',
        'unreachable_followup_days',
        'nurture_default_days',
        'who_can_mark_lost',
    )

    def has_add_permission(self, request):
        # Prevent creating multiple policy settings rows
        return not PolicySettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
