from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'default_region', 'default_timezone', 'is_staff', 'is_active')
    list_filter = ('role', 'default_region', 'is_staff', 'is_active')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('CRM Profile', {'fields': ('role', 'phone', 'default_region', 'default_timezone', 'allowed_regions')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('CRM Profile', {'fields': ('role', 'phone', 'default_region', 'default_timezone', 'allowed_regions')}),
    )
    search_fields = ('username', 'first_name', 'last_name', 'email', 'phone')
