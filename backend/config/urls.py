"""
URL configuration for Solar CRM backend.
"""

from django.contrib import admin
from django.db import connection
from django.http import JsonResponse
from django.urls import path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)


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


urlpatterns = [
    path('admin/', admin.site.urls),

    # Health check
    path('api/health/', health_check, name='health-check'),

    # OpenAPI schema and Swagger / Redoc documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # JWT Authentication
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
