from django.contrib import admin

from .models import MessageLog, MessageTemplate


@admin.register(MessageTemplate)
class MessageTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description', 'body')


@admin.register(MessageLog)
class MessageLogAdmin(admin.ModelAdmin):
    list_display = ('phone', 'lead', 'template_name', 'status', 'created_at')
    list_filter = ('status', 'template_name', 'created_at')
    search_fields = ('phone', 'message_text', 'lead__name')
    readonly_fields = ('created_at',)
