from django.contrib import admin

from .models import Survey, SurveyPhoto


class SurveyPhotoInline(admin.TabularInline):
    model = SurveyPhoto
    extra = 1


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = (
        'lead',
        'scheduled_at',
        'surveyor',
        'status',
        'site_suitable',
        'reschedule_count',
        'created_at',
    )
    list_filter = ('status', 'site_suitable', 'surveyor', 'scheduled_at')
    search_fields = ('lead__name', 'lead__phone', 'notes')
    inlines = [SurveyPhotoInline]
    readonly_fields = ('created_at', 'updated_at')


@admin.register(SurveyPhoto)
class SurveyPhotoAdmin(admin.ModelAdmin):
    list_display = ('survey', 'caption', 'uploaded_at')
    search_fields = ('caption', 'survey__lead__name')
