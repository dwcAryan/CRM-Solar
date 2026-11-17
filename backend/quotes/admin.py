from django.contrib import admin

from .models import Quote


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = (
        'lead',
        'version',
        'system_size_kw',
        'brand',
        'price',
        'subsidy_amount',
        'status',
        'created_by',
        'created_at',
    )
    list_filter = ('status', 'brand', 'created_at')
    search_fields = ('lead__name', 'lead__phone', 'brand', 'notes')
    readonly_fields = ('created_at',)

    def has_delete_permission(self, request, obj=None):
        # Enforce business rule: historical quotes must never be deleted
        return False
