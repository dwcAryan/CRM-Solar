from rest_framework import permissions

from accounts.models import User
from masters.models import PolicySettings

ROLE_HIERARCHY = {
    User.Role.ADMIN: 4,
    User.Role.MANAGER: 3,
    User.Role.SALESPERSON: 2,
    User.Role.SURVEYOR: 1,
}


def can_user_mark_lost(user: User) -> bool:
    """
    Checks if user role is equal to or higher than WHO_CAN_MARK_LOST policy.
    """
    if user.is_superuser or user.role == User.Role.ADMIN:
        return True

    policy = PolicySettings.load()
    required_role = policy.who_can_mark_lost.lower()

    user_level = ROLE_HIERARCHY.get(user.role, 0)
    required_level = ROLE_HIERARCHY.get(required_role, 3)  # default to manager level

    return user_level >= required_level


class IsAdminOrManager(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.role in [User.Role.ADMIN, User.Role.MANAGER] or request.user.is_superuser)
        )


class LeadPermission(permissions.BasePermission):
    """
    Salespeople and Surveyors can only view/edit leads in their allowed regions.
    Salespeople can only edit leads assigned to them.
    Managers and Admins can view/edit leads across allowed regions.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Region boundary check: non-superusers must have the lead's region in allowed_regions
        if obj.region and not user.is_superuser:
            if not user.allowed_regions.filter(code=obj.region_id).exists():
                return False

        if user.is_superuser or user.role in [User.Role.ADMIN, User.Role.MANAGER]:
            return True
        if user.role == User.Role.SALESPERSON:
            return obj.assigned_to_id == user.id
        if user.role == User.Role.SURVEYOR:
            # Surveyors have read-only access to leads they have surveys for
            return request.method in permissions.SAFE_METHODS
        return False


class SurveyPermission(permissions.BasePermission):
    """
    Surveyors can only view/edit surveys assigned to them in allowed regions.
    Managers and Admins can view/edit all surveys.
    Salespeople can view surveys for leads assigned to them.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        lead = getattr(obj, 'lead', None)
        if lead and lead.region and not user.is_superuser:
            if not user.allowed_regions.filter(code=lead.region_id).exists():
                return False

        if user.is_superuser or user.role in [User.Role.ADMIN, User.Role.MANAGER]:
            return True
        if user.role == User.Role.SURVEYOR:
            return obj.surveyor_id == user.id
        if user.role == User.Role.SALESPERSON:
            return lead and lead.assigned_to_id == user.id
        return False
