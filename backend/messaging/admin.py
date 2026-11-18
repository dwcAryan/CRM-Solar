from django.contrib import admin

from .models import MessageLog, MessageTemplate


@admin.register(MessageTemplate)
class MessageTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'region', 'channel', 'description', 'is_active', 'created_at')
    list_filter = ('region', 'channel', 'is_active', 'created_at')
    search_fields = ('name', 'description', 'body')


@admin.register(MessageLog)
class MessageLogAdmin(admin.ModelAdmin):
    list_display = ('phone', 'channel', 'lead', 'template_name', 'status', 'created_at')
    list_filter = ('channel', 'status', 'template_name', 'created_at')
    search_fields = ('phone', 'message_text', 'lead__name')
    readonly_fields = ('created_at',)
