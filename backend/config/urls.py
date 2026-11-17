"""
URL configuration for Solar CRM backend.
"""

from django.contrib import admin
from django.db import connection
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from accounts.views import MeView, UserViewSet
from activities.views import ActivityViewSet
from leads.views import DashboardView, LeadStatusHistoryViewSet, LeadViewSet
from masters.views import (
    LeadSourceViewSet,
    LostReasonViewSet,
    NurtureReasonViewSet,
    OutcomeViewSet,
    PolicySettingsViewSet,
)
from notifications.views import NotificationViewSet
from quotes.views import QuoteViewSet
from surveys.views import SurveyPhotoViewSet, SurveyViewSet


def health_check(request):
    """
    Health check endpoint: verifies DB connectivity and returns system status.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            cursor.fetchone()
    except Exception as e:
        return JsonResponse(
            {
                "status": "degraded",
                "database": "disconnected",
                "error": str(e),
            },
            status=503,
        )

    return JsonResponse(
        {
            "status": "ok",
            "database": "connected",
            "service": "Solar CRM Backend",
        },
        status=200,
    )


router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'masters/outcomes', OutcomeViewSet, basename='outcome')
router.register(r'masters/lost-reasons', LostReasonViewSet, basename='lost-reason')
router.register(r'masters/nurture-reasons', NurtureReasonViewSet, basename='nurture-reason')
router.register(r'masters/lead-sources', LeadSourceViewSet, basename='lead-source')
router.register(r'masters/policy-settings', PolicySettingsViewSet, basename='policy-settings')
router.register(r'leads', LeadViewSet, basename='lead')
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
    path('api/dashboard/', DashboardView.as_view(), name='dashboard'),

    # Router endpoints
    path('api/', include(router.urls)),

    # OpenAPI schema and Swagger / Redoc documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # JWT Authentication
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
