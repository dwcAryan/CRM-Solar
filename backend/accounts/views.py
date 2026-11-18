from django.db import transaction
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.views import APIView

from leads.models import AuditLog, Lead
from notifications.models import Notification
from .models import User
from .permissions import (
    PERMISSION_MATRIX,
    can,
    get_user_permissions,
    HasPermission,
)
from .serializers import UserCreateUpdateSerializer, UserSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('id')
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['role', 'is_active', 'is_staff']
    search_fields = ['username', 'first_name', 'last_name', 'email', 'phone']
    ordering_fields = ['id', 'username', 'role', 'date_joined']

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return User.objects.none()

        # Admin & superuser see all users
        if user.is_superuser or user.role == User.Role.ADMIN:
            return self.queryset

        # Manager can view their team within allowed regions
        if user.role == User.Role.MANAGER:
            allowed = user.allowed_regions.all()
            if allowed.exists():
                return self.queryset.filter(allowed_regions__in=allowed).distinct()
            return self.queryset

        # Salespeople & Surveyors can only view limited team list (for self & lookups)
        return self.queryset.filter(id=user.id)

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [HasPermission('user.manage')()]
        if self.action == 'reassign_leads':
            return [HasPermission('lead.assign')()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return UserCreateUpdateSerializer
        return UserSerializer

    @action(detail=True, methods=['post'], url_path='reassign-leads')
    def reassign_leads(self, request, pk=None):
        """
        Reassigns all active leads owned by this user to another salesperson.
        Permitted for Managers and Admins only.
        """
        source_user = self.get_object()
        target_user_id = request.data.get('target_user_id')
        reason = request.data.get('reason', 'User disabled / reassignment requested')

        if not target_user_id:
            return Response({"error": "target_user_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_user = User.objects.get(id=target_user_id, is_active=True)
        except User.DoesNotExist:
            return Response({"error": "Target user not found or inactive."}, status=status.HTTP_404_NOT_FOUND)

        if target_user.role not in [User.Role.SALESPERSON, User.Role.MANAGER]:
            return Response({"error": "Target user must be a salesperson or manager."}, status=status.HTTP_400_BAD_REQUEST)

        leads_to_reassign = Lead.objects.filter(assigned_to=source_user, is_deleted=False)
        reassigned_count = leads_to_reassign.count()

        with transaction.atomic():
            leads_to_reassign.update(assigned_to=target_user, updated_at=timezone.now())

            # Audit log entry
            AuditLog.objects.create(
                user=request.user,
                action='lead_reassign',
                reason=reason,
                details={
                    'source_user_id': source_user.id,
                    'source_username': source_user.username,
                    'target_user_id': target_user.id,
                    'target_username': target_user.username,
                    'reassigned_count': reassigned_count,
                },
            )

            # Notification to new owner
            Notification.objects.create(
                user=target_user,
                message=f"You have been assigned {reassigned_count} leads previously owned by {source_user.get_full_name() or source_user.username}.",
                link="/leads",
            )

        return Response({
            "message": f"Successfully reassigned {reassigned_count} leads to {target_user.username}.",
            "reassigned_count": reassigned_count,
        })


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        data = serializer.data
        data['permissions'] = get_user_permissions(request.user)
        return Response(data)

    def patch(self, request):
        """
        Allows updating basic contact profile.
        Strictly prevents privilege escalation (cannot modify role, is_staff, is_superuser, allowed_regions).
        """
        disallowed_fields = ['role', 'is_staff', 'is_superuser', 'allowed_regions', 'default_region', 'is_active']
        for field in disallowed_fields:
            if field in request.data:
                return Response(
                    {"error": f"Cannot modify privileged field '{field}' via /api/me/."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            data = serializer.data
            data['permissions'] = get_user_permissions(request.user)
            return Response(data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RolesMatrixView(APIView):
    """
    Returns the read-only permission matrix directly from accounts/permissions.py.
    Permitted for Admin and Manager roles.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not can(request.user, 'user.view_team'):
            return Response({"error": "You do not have permission to view roles matrix."}, status=status.HTTP_403_FORBIDDEN)
        return Response(PERMISSION_MATRIX)
