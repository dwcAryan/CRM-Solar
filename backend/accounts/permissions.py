from typing import Any, Dict, List, Optional

from rest_framework import permissions

from masters.models import PolicySettings

ROLE_HIERARCHY = {
    'admin': 4,
    'manager': 3,
    'salesperson': 2,
    'surveyor': 1,
}

# STEP 2 & 3: Central Permission Matrix (Single Source of Truth)
# Scopes:
#   "all"            - Unrestricted across all data and regions
#   "region"         - Restricted to user's allowed regions
#   "own"            - Restricted to records owned/assigned to the user in their allowed regions
#   "none"           - Completely denied (HTTP 403)
#   "read_only"      - Read-only access (GET/HEAD/OPTIONS)
#   "pending_only"   - Can initiate approval flow (e.g. Salesperson marking Lost)
#   "remark_only"    - Limited to adding remarks (e.g. Salesperson bulk actions)
#   "assigned_survey"- Restricted to surveys assigned to this surveyor
PERMISSION_MATRIX: Dict[str, Dict[str, str]] = {
    # --- LEADS ---
    "lead.view": {
        "admin": "all",
        "manager": "region",
        "salesperson": "own",
        "surveyor": "none",
    },
    "lead.create": {
        "admin": "all",
        "manager": "region",
        "salesperson": "own",  # Automatically self-assigned; cannot pick assignee
        "surveyor": "none",
    },
    "lead.edit": {
        "admin": "all",
        "manager": "region",
        "salesperson": "own",
        "surveyor": "none",
    },
    "lead.assign": {
        "admin": "all",
        "manager": "region",
        "salesperson": "none",
        "surveyor": "none",
    },
    "lead.unassigned_queue": {
        "admin": "all",
        "manager": "region",
        "salesperson": "none",
        "surveyor": "none",
    },
    "lead.delete": {
        "admin": "all",
        "manager": "none",
        "salesperson": "none",
        "surveyor": "none",
    },
    "lead.merge": {
        "admin": "all",
        "manager": "region",
        "salesperson": "none",
        "surveyor": "none",
    },
    "lead.manual_status_change": {
        "admin": "all",
        "manager": "region",
        "salesperson": "none",
        "surveyor": "none",
    },
    "lead.mark_lost": {
        "admin": "all",
        "manager": "region",
        "salesperson": "pending_only",  # Puts lead into Lost Approval Pending
        "surveyor": "none",
    },
    "lead.lost_approval": {
        "admin": "all",
        "manager": "region",
        "salesperson": "none",
        "surveyor": "none",
    },
    "lead.mark_dnc": {
        "admin": "all",
        "manager": "region",
        "salesperson": "own",
        "surveyor": "none",
    },
    "lead.unmark_dnc": {
        "admin": "all",
        "manager": "region",
        "salesperson": "none",
        "surveyor": "none",
    },
    "lead.export": {
        "admin": "all",
        "manager": "region",
        "salesperson": "none",
        "surveyor": "none",
    },
    "lead.import": {
        "admin": "all",
        "manager": "region",
        "salesperson": "none",
        "surveyor": "none",
    },
    "lead.bulk_action": {
        "admin": "all",
        "manager": "region",
        "salesperson": "remark_only",  # Can only add remark on own selected leads
        "surveyor": "none",
    },

    # --- ACTIVITIES, REMARKS, AI ---
    "activity.view": {
        "admin": "all",
        "manager": "region",
        "salesperson": "own",
        "surveyor": "none",
    },
    "activity.log": {
        "admin": "all",
        "manager": "region",
        "salesperson": "own",
        "surveyor": "assigned_survey",
    },
    "activity.correct": {
        "admin": "all",
        "manager": "none",
        "salesperson": "none",
        "surveyor": "none",
    },
    "ai.suggest": {
        "admin": "all",
        "manager": "region",
        "salesperson": "own",
        "surveyor": "none",
    },

    # --- SURVEYS ---
    "survey.view": {
        "admin": "all",
        "manager": "region",
        "salesperson": "own",
        "surveyor": "own",  # Sees only surveys assigned to them
    },
    "survey.book": {
        "admin": "all",
        "manager": "region",
        "salesperson": "own",
        "surveyor": "none",
    },
    "survey.assign": {
        "admin": "all",
        "manager": "region",
        "salesperson": "none",
        "surveyor": "none",
    },
    "survey.reschedule": {
        "admin": "all",
        "manager": "region",
        "salesperson": "own",
        "surveyor": "own",
    },
    "survey.complete": {
        "admin": "all",
        "manager": "region",
        "salesperson": "none",
        "surveyor": "own",
    },

    # --- QUOTES ---
    "quote.view": {
        "admin": "all",
        "manager": "region",
        "salesperson": "own",
        "surveyor": "none",
    },
    "quote.create": {
        "admin": "all",
        "manager": "region",
        "salesperson": "own",
        "surveyor": "none",
    },
    "quote.send": {
        "admin": "all",
        "manager": "region",
        "salesperson": "own",
        "surveyor": "none",
    },
    "quote.revise": {
        "admin": "all",
        "manager": "region",
        "salesperson": "own",
        "surveyor": "none",
    },
    "quote.accept": {
        "admin": "all",
        "manager": "region",
        "salesperson": "own",
        "surveyor": "none",
    },
    "quote.reject": {
        "admin": "all",
        "manager": "region",
        "salesperson": "own",
        "surveyor": "none",
    },

    # --- USERS, SETTINGS, SYSTEM ---
    "user.manage": {
        "admin": "all",
        "manager": "none",
        "salesperson": "none",
        "surveyor": "none",
    },
    "user.view_team": {
        "admin": "all",
        "manager": "region",
        "salesperson": "none",
        "surveyor": "none",
    },
    "masters.manage": {
        "admin": "all",
        "manager": "read_only",
        "salesperson": "none",
        "surveyor": "none",
    },
    "privacy.manage": {
        "admin": "all",
        "manager": "none",
        "salesperson": "none",
        "surveyor": "none",
    },
    "audit.view": {
        "admin": "all",
        "manager": "region",
        "salesperson": "none",
        "surveyor": "none",
    },
    "dashboard.view": {
        "admin": "all",
        "manager": "team",
        "salesperson": "own",
        "surveyor": "own",
    },
    "help.insights": {
        "admin": "all",
        "manager": "none",
        "salesperson": "none",
        "surveyor": "none",
    },
    "notification.manage": {
        "admin": "all",
        "manager": "own",
        "salesperson": "own",
        "surveyor": "own",
    },
    "i18n.manage": {
        "admin": "all",
        "manager": "none",
        "salesperson": "none",
        "surveyor": "none",
    },
    "i18n.view": {
        "admin": "all",
        "manager": "all",
        "salesperson": "none",
        "surveyor": "none",
    },
}


def can(user: Any, perm_key: str, obj: Any = None) -> bool:
    """
    Evaluates whether a user has permission to execute an action,
    optionally scoped to a specific object.
    Enforces strict default-deny.
    """
    if not user or not getattr(user, 'is_authenticated', False) or not getattr(user, 'is_active', True):
        return False

    # Check permission key in matrix; if absent, refuse by default
    if perm_key not in PERMISSION_MATRIX:
        return False

    user_role = getattr(user, 'role', None)
    if not user_role:
        return False

    # Superuser inherits admin level
    if getattr(user, 'is_superuser', False):
        user_role = 'admin'

    scope = PERMISSION_MATRIX[perm_key].get(user_role, "none")
    if scope == "none":
        return False

    # If no object provided, coarse permission is granted
    if obj is None:
        return True

    # 1. Multi-Country Region Scoping: non-superusers cannot access objects outside allowed_regions
    if not getattr(user, 'is_superuser', False):
        obj_region = getattr(obj, 'region_id', None)
        if obj_region is None and hasattr(obj, 'lead'):
            obj_region = getattr(obj.lead, 'region_id', None)

        if obj_region:
            allowed = getattr(user, 'allowed_regions', None)
            if allowed and allowed.exists() and not allowed.filter(code=obj_region).exists():
                return False

    # 2. Scope-specific object-level checks
    if scope in ("all", "region", "team"):
        return True

    if scope == "own":
        # Check ownership based on object type
        # For Lead
        if hasattr(obj, 'assigned_to_id'):
            if getattr(obj, 'assigned_to_id', None) == user.id:
                return True
            if getattr(obj, 'created_by_id', None) == user.id:
                return True
        # For Survey
        if hasattr(obj, 'surveyor_id'):
            if getattr(obj, 'surveyor_id', None) == user.id:
                return True
            if hasattr(obj, 'lead') and getattr(obj.lead, 'assigned_to_id', None) == user.id:
                return True
        # For Quote / Activity
        if hasattr(obj, 'created_by_id') and getattr(obj, 'created_by_id', None) == user.id:
            return True
        if hasattr(obj, 'lead') and getattr(obj.lead, 'assigned_to_id', None) == user.id:
            return True
        return False

    if scope == "assigned_survey":
        # Specific for surveyor completing / updating surveys
        if hasattr(obj, 'surveyor_id'):
            return getattr(obj, 'surveyor_id', None) == user.id
        if hasattr(obj, 'survey') and hasattr(obj.survey, 'surveyor_id'):
            return getattr(obj.survey, 'surveyor_id', None) == user.id
        return False

    if scope == "read_only":
        return True

    if scope in ("pending_only", "remark_only"):
        # Permitted to participate in this restricted mode
        return True

    return False


def get_user_permissions(user: Any) -> List[str]:
    """
    Returns list of all active permission keys for the user.
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return []

    user_role = getattr(user, 'role', None)
    if getattr(user, 'is_superuser', False):
        user_role = 'admin'

    if not user_role:
        return []

    granted = []
    for key, role_dict in PERMISSION_MATRIX.items():
        if role_dict.get(user_role, "none") != "none":
            granted.append(key)
    return sorted(granted)


def can_user_mark_lost(user: Any) -> bool:
    """
    Checks if user role is equal to or higher than WHO_CAN_MARK_LOST policy.
    Salespeople cannot finalize Lost; they submit for approval.
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return False

    if getattr(user, 'is_superuser', False) or getattr(user, 'role', None) == 'admin':
        return True

    policy = PolicySettings.load()
    required_role = policy.who_can_mark_lost.lower()

    user_level = ROLE_HIERARCHY.get(getattr(user, 'role', ''), 0)
    required_level = ROLE_HIERARCHY.get(required_role, 3)

    return user_level >= required_level


class HasPermission(permissions.BasePermission):
    """
    DRF Permission class for checking a specific permission key.
    Usage: permission_classes = [HasPermission('lead.view')]
    """
    def __init__(self, perm_key: str):
        self.perm_key = perm_key

    def __call__(self):
        return self

    def has_permission(self, request, view):
        return can(request.user, self.perm_key)

    def has_object_permission(self, request, view, obj):
        return can(request.user, self.perm_key, obj)


class DynamicRBACPermission(permissions.BasePermission):
    """
    Dynamic DRF Permission class that inspects `permission_map` on the viewset.
    Default Deny: If an action is not mapped, request is denied with 403.
    """
    def get_perm_key(self, request, view) -> Optional[str]:
        perm_map = getattr(view, 'permission_map', {})
        action = getattr(view, 'action', None)
        if action and action in perm_map:
            return perm_map[action]

        # Method fallback
        method = request.method.lower()
        if method in perm_map:
            return perm_map[method]

        return None

    def has_permission(self, request, view):
        perm_key = self.get_perm_key(request, view)
        if not perm_key:
            return False  # Strict Default Deny
        return can(request.user, perm_key)

    def has_object_permission(self, request, view, obj):
        perm_key = self.get_perm_key(request, view)
        if not perm_key:
            return False
        return can(request.user, perm_key, obj)


# Backwards compatibility / convenience classes
class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (request.user.role == 'admin' or request.user.is_superuser))


class IsAdminOrManager(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.role in ['admin', 'manager'] or request.user.is_superuser)
        )


class LeadPermission(DynamicRBACPermission):
    """Lead permission adapter implementing object checks via `can()`."""
    def get_perm_key(self, request, view):
        action = getattr(view, 'action', None)
        if action in ['list', 'retrieve']:
            return 'lead.view'
        if action == 'create':
            return 'lead.create'
        if action in ['update', 'partial_update']:
            return 'lead.edit'
        if action == 'destroy':
            return 'lead.delete'
        return super().get_perm_key(request, view)


class SurveyPermission(DynamicRBACPermission):
    """Survey permission adapter implementing object checks via `can()`."""
    def get_perm_key(self, request, view):
        action = getattr(view, 'action', None)
        if action in ['list', 'retrieve', 'my_surveys']:
            return 'survey.view'
        if action in ['create', 'book']:
            return 'survey.book'
        if action in ['reschedule', 'propose_reschedule']:
            return 'survey.reschedule'
        if action in ['mark_done', 'mark_missed', 'cancel_by_surveyor']:
            return 'survey.complete'
        if action in ['assign_surveyor']:
            return 'survey.assign'
        return super().get_perm_key(request, view)


class QuotePermission(DynamicRBACPermission):
    """Quote permission adapter implementing object checks via `can()`."""
    def get_perm_key(self, request, view):
        action = getattr(view, 'action', None)
        if action in ['list', 'retrieve', 'versions']:
            return 'quote.view'
        if action == 'create':
            return 'quote.create'
        if action in ['send', 'mark_sent']:
            return 'quote.send'
        if action == 'revise':
            return 'quote.revise'
        if action == 'accept':
            return 'quote.accept'
        if action == 'reject':
            return 'quote.reject'
        return super().get_perm_key(request, view)
