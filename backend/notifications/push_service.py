import json
import logging

import pywebpush
from django.conf import settings
from django.utils import timezone
from pywebpush import WebPushException

from notifications.models import NotificationPreference, PushSubscription

logger = logging.getLogger(__name__)


def send_push_notification(user, title: str, body: str, lead_id: int | None = None, url: str | None = None) -> dict:
    """
    Sends a Web Push notification to all active browser subscriptions for a user.
    Enforces:
      1. NotificationPreference check (push_enabled)
      2. Quiet hours check in user's default timezone
      3. Strict Privacy: Payload contains ONLY title, body (short message), lead_id, url.
         NEVER contains customer phone numbers, names, or private customer details.
      4. Auto-cleanup of expired/unregistered push subscriptions on HTTP 404 or 410.
    """
    pref, _ = NotificationPreference.objects.get_or_create(user=user)
    if not pref.push_enabled:
        return {"sent": 0, "failed": 0, "skipped": "push_disabled"}

    if pref.is_in_quiet_hours():
        return {"sent": 0, "failed": 0, "skipped": "quiet_hours"}

    subscriptions = PushSubscription.objects.filter(user=user)
    if not subscriptions.exists():
        return {"sent": 0, "failed": 0, "skipped": "no_subscriptions"}

    # Strict privacy payload: only title, message, lead_id, link
    payload = {
        "title": title,
        "body": body,
        "lead_id": lead_id,
        "url": url or (f"/leads/{lead_id}" if lead_id else "/"),
        "timestamp": timezone.now().isoformat(),
    }
    payload_json = json.dumps(payload)

    vapid_private = getattr(settings, 'VAPID_PRIVATE_KEY', '')
    vapid_claims = {
        "sub": f"mailto:{getattr(settings, 'VAPID_ADMIN_EMAIL', 'admin@solarcrm.com')}"
    }

    sent = 0
    failed = 0
    expired = 0

    for sub in list(subscriptions):
        sub_info = {
            "endpoint": sub.endpoint,
            "keys": {
                "p256dh": sub.p256dh,
                "auth": sub.auth,
            }
        }
        try:
            pywebpush.webpush(
                subscription_info=sub_info,
                data=payload_json,
                vapid_private_key=vapid_private,
                vapid_claims=vapid_claims,
                ttl=86400,
            )
            sent += 1
        except WebPushException as ex:
            status_code = getattr(ex.response, 'status_code', None) if getattr(ex, 'response', None) else None
            if status_code in (404, 410):
                logger.info(f"Removing expired PushSubscription {sub.id} (HTTP {status_code})")
                sub.delete()
                expired += 1
            else:
                logger.warning(f"WebPush delivery error for {sub.id}: {ex}")
                failed += 1
        except Exception as e:
            logger.warning(f"Unexpected WebPush error for {sub.id}: {e}")
            failed += 1

    return {"sent": sent, "failed": failed, "expired": expired}
