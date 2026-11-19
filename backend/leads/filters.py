"""
Lead filtering and date range query mixin for Solar CRM.
Supports:
1. Reusable Date Range Filter mixin (date_field, date_from, date_to).
2. Inclusive end-of-day boundaries in requesting user's local timezone converted to UTC.
3. Whitelisted field enforcement and bounds checking (1900-2100).
4. Stable error codes for malformed parameters and inverted ranges.
"""

import datetime
import zoneinfo
from typing import Optional, Set

import django_filters
from django.db.models import QuerySet
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework.exceptions import ValidationError

from .models import Lead

WHITELISTED_DATE_FIELDS: Set[str] = {
    'created_at',
    'next_followup_at',
    'updated_at',
    'last_activity_at',
    'won_at',
}


def get_request_user_timezone(request) -> zoneinfo.ZoneInfo:
    """Derives user's configured timezone or falls back to Asia/Kolkata."""
    if request and hasattr(request, 'user') and getattr(request.user, 'is_authenticated', False):
        tz_str = getattr(request.user, 'default_timezone', None)
        if tz_str:
            try:
                return zoneinfo.ZoneInfo(tz_str)
            except Exception:
                pass
        reg = getattr(request.user, 'default_region', None)
        if reg and getattr(reg, 'default_timezone', None):
            try:
                return zoneinfo.ZoneInfo(reg.default_timezone)
            except Exception:
                pass
    return zoneinfo.ZoneInfo('Asia/Kolkata')


class LeadDateFilterMixin:
    """
    Reusable django-filter mixin providing timezone-aware inclusive date range filtering.
    """

    @classmethod
    def apply_date_filter(cls, request, queryset: QuerySet) -> QuerySet:
        if not request:
            return queryset

        params = request.query_params if hasattr(request, 'query_params') else request.GET
        date_from_str = params.get('date_from')
        date_to_str = params.get('date_to')
        date_field = params.get('date_field', 'created_at')

        if not date_from_str and not date_to_str:
            # If no date filter params passed, return untouched queryset
            return queryset

        # 1. Whitelist validation
        if date_field not in WHITELISTED_DATE_FIELDS:
            raise ValidationError({
                "code": "invalid_date_field",
                "error": f"Invalid date_field '{date_field}'. Whitelisted fields: {sorted(WHITELISTED_DATE_FIELDS)}",
                "detail": f"Invalid date_field '{date_field}'. Whitelisted fields: {sorted(WHITELISTED_DATE_FIELDS)}",
            })

        user_tz = get_request_user_timezone(request)
        d_from: Optional[datetime.date] = None
        d_to: Optional[datetime.date] = None

        # 2. Parse date_from
        if date_from_str:
            dt_from = parse_datetime(date_from_str) or parse_date(date_from_str)
            if not dt_from:
                raise ValidationError({
                    "code": "invalid_date_format",
                    "error": "Invalid date_from format. Use ISO format (YYYY-MM-DD).",
                    "detail": "Invalid date_from format. Use ISO format (YYYY-MM-DD).",
                })
            d_from = dt_from.date() if isinstance(dt_from, datetime.datetime) else dt_from
            if d_from.year < 1900 or d_from.year > 2100:
                raise ValidationError({
                    "code": "date_out_of_bounds",
                    "error": "date_from year out of range (1900-2100).",
                    "detail": "date_from year out of range (1900-2100).",
                })

        # 3. Parse date_to
        if date_to_str:
            dt_to = parse_datetime(date_to_str) or parse_date(date_to_str)
            if not dt_to:
                raise ValidationError({
                    "code": "invalid_date_format",
                    "error": "Invalid date_to format. Use ISO format (YYYY-MM-DD).",
                    "detail": "Invalid date_to format. Use ISO format (YYYY-MM-DD).",
                })
            d_to = dt_to.date() if isinstance(dt_to, datetime.datetime) else dt_to
            if d_to.year < 1900 or d_to.year > 2100:
                raise ValidationError({
                    "code": "date_out_of_bounds",
                    "error": "date_to year out of range (1900-2100).",
                    "detail": "date_to year out of range (1900-2100).",
                })

        # 4. Inverted range validation
        if d_from and d_to and d_from > d_to:
            raise ValidationError({
                "code": "invalid_date_range",
                "error": "From date cannot be after To date.",
                "detail": "From date cannot be after To date.",
            })

        # 5. Convert to user's timezone boundaries and then to UTC
        if d_from:
            start_local = datetime.datetime.combine(d_from, datetime.time.min, tzinfo=user_tz)
            start_utc = start_local.astimezone(datetime.timezone.utc)
            queryset = queryset.filter(**{f"{date_field}__gte": start_utc})

        if d_to:
            end_local = datetime.datetime.combine(d_to, datetime.time.max, tzinfo=user_tz)
            end_utc = end_local.astimezone(datetime.timezone.utc)
            queryset = queryset.filter(**{f"{date_field}__lte": end_utc})

        return queryset


class LeadFilterSet(django_filters.FilterSet, LeadDateFilterMixin):
    """
    Standard FilterSet for Lead querysets combining attribute filters with date range mixin.
    """
    class Meta:
        model = Lead
        fields = [
            'status',
            'assigned_to',
            'source',
            'city',
            'state',
            'region',
            'consent_status',
            'dncr_status',
            'do_not_contact',
            'property_type',
        ]

    def filter_queryset(self, queryset):
        # 1. Apply standard django-filter fields
        qs = super().filter_queryset(queryset)
        # 2. Apply timezone-aware inclusive date range filter
        qs = self.apply_date_filter(self.request, qs)
        return qs
