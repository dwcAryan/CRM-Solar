import datetime
import zoneinfo
from typing import Optional, Tuple

from django.utils import timezone

AU_STATE_TIMEZONES = {
    'NSW': 'Australia/Sydney',
    'VIC': 'Australia/Melbourne',
    'QLD': 'Australia/Brisbane',
    'WA': 'Australia/Perth',
    'SA': 'Australia/Adelaide',
    'TAS': 'Australia/Hobart',
    'ACT': 'Australia/Sydney',
    'NT': 'Australia/Darwin',
}

IN_DEFAULT_TIMEZONE = 'Asia/Kolkata'


def get_default_timezone_for_state(region_code: str, state_code_or_name: str) -> str:
    """
    Derives appropriate IANA timezone for a state within a region.
    """
    reg = (region_code or 'IN').upper()
    if reg == 'IN':
        return IN_DEFAULT_TIMEZONE

    if reg == 'AU':
        st_clean = (state_code_or_name or '').upper().strip()
        # Direct code match
        if st_clean in AU_STATE_TIMEZONES:
            return AU_STATE_TIMEZONES[st_clean]

        # Name match
        name_map = {
            'NEW SOUTH WALES': 'Australia/Sydney',
            'VICTORIA': 'Australia/Melbourne',
            'QUEENSLAND': 'Australia/Brisbane',
            'WESTERN AUSTRALIA': 'Australia/Perth',
            'SOUTH AUSTRALIA': 'Australia/Adelaide',
            'TASMANIA': 'Australia/Hobart',
            'AUSTRALIAN CAPITAL TERRITORY': 'Australia/Sydney',
            'NORTHERN TERRITORY': 'Australia/Darwin',
        }
        for name, tz in name_map.items():
            if name in st_clean or st_clean in name:
                return tz

        return 'Australia/Sydney'

    return 'Asia/Kolkata'


def format_datetime_in_timezone(dt: Optional[datetime.datetime], tz_name: str = 'Asia/Kolkata') -> str:
    """
    Renders datetime in target timezone with timezone abbreviation (e.g. '05:00 PM AEDT').
    """
    if not dt:
        return ""
    try:
        tz = zoneinfo.ZoneInfo(tz_name or 'Asia/Kolkata')
    except Exception:
        tz = zoneinfo.ZoneInfo('Asia/Kolkata')

    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, datetime.timezone.utc)

    local_dt = dt.astimezone(tz)
    return local_dt.strftime('%d/%m/%Y %I:%M %p %Z')


def check_calling_hours(lead, target_datetime: Optional[datetime.datetime] = None) -> Tuple[bool, str]:
    """
    Evaluates whether target_datetime (default now) is within allowed calling hours
    for the lead, evaluated strictly in the LEAD'S local timezone and region calendar.
    Returns:
        (is_allowed, reason_message)
    """
    if not lead:
        return True, "No lead provided."

    region = getattr(lead, 'region', None)
    if not region:
        return True, "No region restriction configured."

    tz_str = lead.timezone or region.default_timezone or 'Asia/Kolkata'
    try:
        lead_tz = zoneinfo.ZoneInfo(tz_str)
    except Exception:
        lead_tz = zoneinfo.ZoneInfo('Asia/Kolkata')

    dt = target_datetime or timezone.now()
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, datetime.timezone.utc)

    local_dt = dt.astimezone(lead_tz)
    local_date = local_dt.date()
    local_time = local_dt.time()
    weekday = local_dt.weekday()  # Monday=0, Sunday=6

    # 1. Check Public Holidays
    from masters.models import PublicHoliday
    holiday = PublicHoliday.objects.filter(region=region, date=local_date).first()
    if holiday:
        return False, f"Today ({local_date.strftime('%d/%m/%Y')}) is a recognized public holiday in {region.name}: '{holiday.name}'. Outbound calling is prohibited."

    # 2. Check Sunday (weekday == 6)
    if weekday == 6:
        if not region.sunday_calling_allowed:
            return False, f"Outbound telemarketing calls are strictly prohibited on Sundays in {region.name}."
        # If allowed, check Sunday specific hours if set
        start = region.sunday_hours_start or region.calling_hours_start
        end = region.sunday_hours_end or region.calling_hours_end_weekday
        if not (start <= local_time <= end):
            return (
                False,
                f"Outside Sunday calling hours in {region.name} ({start.strftime('%I:%M %p')} to {end.strftime('%I:%M %p')} {local_dt.strftime('%Z')}). Current local time: {local_time.strftime('%I:%M %p')}.",
            )
        return True, "Within allowed Sunday calling hours."

    # 3. Check Saturday (weekday == 5)
    if weekday == 5:
        start = region.calling_hours_start
        end = region.calling_hours_end_saturday
        if not (start <= local_time <= end):
            return (
                False,
                f"Outside Saturday calling hours in {region.name} ({start.strftime('%I:%M %p')} to {end.strftime('%I:%M %p')} {local_dt.strftime('%Z')}). Current local time: {local_time.strftime('%I:%M %p')}.",
            )
        return True, "Within allowed Saturday calling hours."

    # 4. Weekdays (Monday through Friday: weekday 0-4)
    start = region.calling_hours_start
    end = region.calling_hours_end_weekday
    if not (start <= local_time <= end):
        return (
            False,
            f"Outside weekday calling hours in {region.name} ({start.strftime('%I:%M %p')} to {end.strftime('%I:%M %p')} {local_dt.strftime('%Z')}). Current local time: {local_time.strftime('%I:%M %p')}.",
        )

    return True, "Within permitted calling hours."
