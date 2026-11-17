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
    Salespeople can only view/edit leads assigned to them.
    Managers and Admins can view/edit all leads.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser or request.user.role in [User.Role.ADMIN, User.Role.MANAGER]:
            return True
        if request.user.role == User.Role.SALESPERSON:
            return obj.assigned_to_id == request.user.id
        return False


class SurveyPermission(permissions.BasePermission):
    """
    Surveyors can only view/edit surveys assigned to them.
    Managers and Admins can view/edit all surveys.
    Salespeople can view surveys for leads assigned to them.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser or request.user.role in [User.Role.ADMIN, User.Role.MANAGER]:
            return True
        if request.user.role == User.Role.SURVEYOR:
            return obj.surveyor_id == request.user.id
        if request.user.role == User.Role.SALESPERSON:
            return obj.lead.assigned_to_id == request.user.id
        return False
