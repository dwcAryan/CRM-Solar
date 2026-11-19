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

from .models import User, UserTourState
from .permissions import (
    PERMISSION_MATRIX,
    HasPermission,
    can,
    get_user_permissions,
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
        disallowed_fields = [
            'role',
            'is_staff',
            'is_superuser',
            'allowed_regions',
            'default_region',
            'is_active',
            'is_demo',
            'must_change_password',
        ]
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


TOUR_VERSION = 1


class TourStateView(APIView):
    """
    Tracks and persists interactive product tour progress and completion per user.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        states = UserTourState.objects.filter(user=request.user)
        tours_dict = {
            s.tour_id: {
                "status": s.status,
                "last_step": s.last_step,
                "version": s.version,
                "updated_at": s.updated_at.isoformat(),
            }
            for s in states
        }
        has_seen_tour = any(
            s.status in [UserTourState.Status.COMPLETED, UserTourState.Status.DISMISSED, UserTourState.Status.IN_PROGRESS]
            for s in states
            if s.tour_id in ['complete', 'main']
        )
        completed_tours = [s.tour_id for s in states if s.status == UserTourState.Status.COMPLETED]
        return Response({
            "tour_version": TOUR_VERSION,
            "has_seen_tour": has_seen_tour,
            "completed_tours": completed_tours,
            "tours": tours_dict,
        }, status=status.HTTP_200_OK)

    def patch(self, request):
        has_seen = request.data.get('has_seen_tour')
        completed_tours = request.data.get('completed_tours', [])

        if has_seen:
            state, _ = UserTourState.objects.get_or_create(
                user=request.user,
                tour_id='complete',
                defaults={"version": TOUR_VERSION, "status": UserTourState.Status.COMPLETED, "last_step": 0},
            )
            state.status = UserTourState.Status.COMPLETED
            state.save()

        if isinstance(completed_tours, list):
            for t_id in completed_tours:
                st, _ = UserTourState.objects.get_or_create(
                    user=request.user,
                    tour_id=t_id,
                    defaults={"version": TOUR_VERSION, "status": UserTourState.Status.COMPLETED, "last_step": 0},
                )
                st.status = UserTourState.Status.COMPLETED
                st.save()

        tour_id = request.data.get('tour_id')
        if tour_id:
            new_status = request.data.get('status')
            last_step = request.data.get('last_step')
            version = request.data.get('version', TOUR_VERSION)

            state, _ = UserTourState.objects.get_or_create(
                user=request.user,
                tour_id=tour_id,
                defaults={"version": version, "status": UserTourState.Status.NOT_STARTED, "last_step": 0},
            )
            if new_status in UserTourState.Status.values:
                state.status = new_status
            if last_step is not None:
                state.last_step = int(last_step)
            state.version = version
            state.save()

        return self.get(request)

    def post(self, request):
        """Admin or user reset of tour states."""
        reset_all = request.data.get('all', False)
        target_user_id = request.data.get('user_id')

        if reset_all or target_user_id:
            if not can(request.user, 'user.manage') and not request.user.is_superuser:
                return Response(
                    {"error": "Admin permission required to reset tours for other users."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if reset_all:
                count = UserTourState.objects.all().update(status=UserTourState.Status.NOT_STARTED, last_step=0)
                return Response({"message": f"Successfully reset tour for all {count} user states.", "count": count})
            else:
                count = UserTourState.objects.filter(user_id=target_user_id).update(
                    status=UserTourState.Status.NOT_STARTED, last_step=0
                )
                return Response({"message": f"Reset tour for user {target_user_id}.", "count": count})
        else:
            UserTourState.objects.filter(user=request.user).update(
                status=UserTourState.Status.NOT_STARTED, last_step=0
            )
            return Response({"message": "Successfully reset tour for your account."})


class PasswordChangeView(APIView):
    """
    Enforces strong password update for authenticated users (mandatory on first login if flagged).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        if not new_password:
            return Response({"error": "New password is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Check existing password if usable
        if user.has_usable_password() and old_password:
            if not user.check_password(old_password):
                return Response({"error": "Incorrect current password."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate password complexity
        import re
        if len(new_password) < 10:
            return Response({"error": "Password must be at least 10 characters long."}, status=status.HTTP_400_BAD_REQUEST)
        if not re.search(r'[A-Z]', new_password):
            return Response({"error": "Password must include at least one uppercase letter."}, status=status.HTTP_400_BAD_REQUEST)
        if not re.search(r'[a-z]', new_password):
            return Response({"error": "Password must include at least one lowercase letter."}, status=status.HTTP_400_BAD_REQUEST)
        if not re.search(r'[0-9]', new_password):
            return Response({"error": "Password must include at least one digit."}, status=status.HTTP_400_BAD_REQUEST)
        if not re.search(r'[^A-Za-z0-9]', new_password):
            return Response({"error": "Password must include at least one special character."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.must_change_password = False
        user.save(update_fields=['password', 'must_change_password'])

        return Response({"status": "success", "message": "Password changed successfully."})


from django.core.cache import cache
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView


class SolarTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = {
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
            'role': self.user.role,
            'must_change_password': getattr(self.user, 'must_change_password', False),
            'preferred_language': getattr(self.user, 'preferred_language', 'en'),
        }
        return data


class SolarTokenObtainPairView(TokenObtainPairView):
    """
    Hardened Token Obtain View:
    - Rate limits login attempts (max 5 failed attempts per 5 minutes per IP/username).
    - Account lockout for 15 minutes after 5 consecutive failures.
    - Uniform generic error on authentication failure (preventing username enumeration).
    - Throttling scope: 'login'.
    """
    serializer_class = SolarTokenObtainPairSerializer
    throttle_scope = 'login'

    def post(self, request, *args, **kwargs):
        username = str(request.data.get('username', '')).strip().lower()
        ip = request.META.get('REMOTE_ADDR', 'unknown')
        cache_key = f"login_attempts_{ip}_{username}"
        lockout_key = f"login_lockout_{ip}_{username}"

        if cache.get(lockout_key):
            return Response(
                {"detail": "Account temporarily locked due to too many failed login attempts. Please try again in 15 minutes."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        response = super().post(request, *args, **kwargs)

        if response.status_code == status.HTTP_200_OK:
            cache.delete(cache_key)
            cache.delete(lockout_key)
        else:
            attempts = cache.get(cache_key, 0) + 1
            cache.set(cache_key, attempts, timeout=300)
            if attempts >= 5:
                cache.set(lockout_key, True, timeout=900)
                return Response(
                    {"detail": "Too many failed login attempts. Account temporarily locked for 15 minutes."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
            # Uniform message to prevent username enumeration
            response.data = {"detail": "No active account found with the given credentials."}

        return response


class LogoutView(APIView):
    """
    Blacklists the refresh token to immediately revoke session access.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({"error": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception as e:
            return Response({"error": f"Invalid or expired token: {e}"}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"message": "Successfully logged out and session revoked."}, status=status.HTTP_200_OK)


