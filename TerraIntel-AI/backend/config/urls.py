"""Root URL configuration for TerraIntel AI Module 3."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from core.views import health_check

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health-check"),
    path("api/v1/", include("regions.urls")),
    path("api/v1/", include("analyses.urls")),
    path("api/v1/", include("weather.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
