"""HTTP views for AgriculturalRegion CRUD."""
from rest_framework import viewsets

from .models import AgriculturalRegion
from .serializers import AgriculturalRegionSerializer


class AgriculturalRegionViewSet(viewsets.ModelViewSet):
    """CRUD endpoints for agricultural regions."""

    queryset = AgriculturalRegion.objects.all()
    serializer_class = AgriculturalRegionSerializer
