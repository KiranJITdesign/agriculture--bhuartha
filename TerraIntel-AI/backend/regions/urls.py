"""URL routes for regions app."""
from rest_framework.routers import DefaultRouter

from .views import AgriculturalRegionViewSet

router = DefaultRouter()
router.register(r"regions", AgriculturalRegionViewSet, basename="region")

urlpatterns = router.urls
