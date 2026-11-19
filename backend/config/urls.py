"""
URL configuration for Solar CRM backend.
"""

from django.conf import settings
from django.contrib import admin
from django.db import connection
from django.http import FileResponse, HttpResponse, JsonResponse
from django.urls import include, path, re_path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework import permissions
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from accounts.password_reset_views import PasswordResetConfirmView, PasswordResetRequestView
from accounts.views import (
    LogoutView,
    MeView,
    PasswordChangeView,
    RolesMatrixView,
    SolarTokenObtainPairView,
    TourStateView,
    UserViewSet,
)
from activities.views import ActivityViewSet
from leads.views import (
    AuditLogViewSet,
    DashboardView,
    ImportBatchViewSet,
    LeadStatusHistoryViewSet,
    LeadViewSet,
)
from masters.views import (
    LanguageViewSet,
    LeadSourceViewSet,
    LostReasonViewSet,
    NurtureReasonViewSet,
    OutcomeViewSet,
    PolicySettingsViewSet,
    PropertyTypeViewSet,
    PublicHolidayViewSet,
    RegionViewSet,
    RoofTypeViewSet,
    StateViewSet,
    TranslationViewSet,
)
from notifications.views import NotificationViewSet
from quotes.views import QuoteViewSet
from surveys.views import SurveyPhotoViewSet, SurveyViewSet


def health_check(request):
    """
    Readiness & health check endpoint: verifies DB connectivity and migrations status.
    """
    db_status = "connected"
    migrations_status = "up_to_date"
    errors = []

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            cursor.fetchone()
    except Exception as e:
        db_status = "disconnected"
        errors.append(f"Database error: {e}")

    try:
        from django.db.migrations.executor import MigrationExecutor
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        if plan:
            migrations_status = "pending"
            errors.append(f"{len(plan)} pending migrations found")
    except Exception as e:
        errors.append(f"Migration check error: {e}")

    is_ready = db_status == "connected" and migrations_status == "up_to_date"
    app_env = getattr(settings, 'APP_ENV', 'development')

    status_code = 200 if is_ready else 503
    return JsonResponse(
        {
            "status": "ok" if is_ready else "degraded",
            "ready": is_ready,
            "database": db_status,
            "migrations": migrations_status,
            "environment": app_env,
            "service": "Solar CRM Backend",
            "errors": errors if errors else None,
        },
        status=status_code,
    )


def serve_spa(request):
    """Serves the built SPA frontend or an instructional message if not built."""
    index_file = settings.BASE_DIR.parent / 'frontend' / 'dist' / 'index.html'
    if index_file.exists():
        return FileResponse(open(index_file, 'rb'), content_type='text/html')
    return HttpResponse("Solar CRM frontend is not built. Run 'npm run build' inside frontend/.", status=404)


doc_permissions = [permissions.IsAdminUser] if getattr(settings, 'APP_ENV', '') == 'production' else []


router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'masters/regions', RegionViewSet, basename='region')
router.register(r'masters/states', StateViewSet, basename='state')
router.register(r'masters/public-holidays', PublicHolidayViewSet, basename='public-holiday')
router.register(r'masters/roof-types', RoofTypeViewSet, basename='roof-type')
router.register(r'masters/property-types', PropertyTypeViewSet, basename='property-type')
router.register(r'masters/outcomes', OutcomeViewSet, basename='outcome')
router.register(r'masters/lost-reasons', LostReasonViewSet, basename='lost-reason')
router.register(r'masters/nurture-reasons', NurtureReasonViewSet, basename='nurture-reason')
router.register(r'masters/lead-sources', LeadSourceViewSet, basename='lead-source')
router.register(r'masters/policy-settings', PolicySettingsViewSet, basename='policy-settings')
router.register(r'masters/languages', LanguageViewSet, basename='language')
router.register(r'masters/translations', TranslationViewSet, basename='translation')
router.register(r'leads', LeadViewSet, basename='lead')
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')
router.register(r'import-batches', ImportBatchViewSet, basename='import-batch')
router.register(r'lead-status-history', LeadStatusHistoryViewSet, basename='lead-status-history')
router.register(r'activities', ActivityViewSet, basename='activity')
router.register(r'surveys', SurveyViewSet, basename='survey')
router.register(r'survey-photos', SurveyPhotoViewSet, basename='survey-photo')
router.register(r'quotes', QuoteViewSet, basename='quote')
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('admin/', admin.site.urls),

    # Health check
    path('api/health/', health_check, name='health-check'),

    # Current user & dashboard
    path('api/me/', MeView.as_view(), name='me'),
    path('api/me/tour/', TourStateView.as_view(), name='tour-state'),
    path('api/dashboard/', DashboardView.as_view(), name='dashboard'),
    path('api/roles-matrix/', RolesMatrixView.as_view(), name='roles-matrix'),

    # Router endpoints
    path('api/', include(router.urls)),

    # OpenAPI schema and Swagger / Redoc documentation
    path('api/schema/', SpectacularAPIView.as_view(permission_classes=doc_permissions), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema', permission_classes=doc_permissions), name='swagger-ui'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema', permission_classes=doc_permissions), name='swagger-ui-alias'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema', permission_classes=doc_permissions), name='redoc'),

    # JWT Authentication
    path('api/token/', SolarTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/logout/', LogoutView.as_view(), name='auth_logout'),

    # Password Reset & Change Flow
    path('api/auth/password-reset/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('api/auth/password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('api/auth/change-password/', PasswordChangeView.as_view(), name='password_change'),

    # Helpbot (Phase 13)
    path('api/helpbot/', include('helpbot.urls')),

    # SPA Fallback for production serving
    re_path(r'^(?!api/|admin/|static/|media/).*$', serve_spa, name='spa_fallback'),
]
