"""AgriculturalRegion PostGIS model."""
from __future__ import annotations

import uuid
from decimal import ROUND_HALF_UP, Decimal

from django.contrib.gis.db import models


def compute_geodesic_area_ha(geom: models.PolygonField) -> Decimal:
    """Compute polygon area in hectares using EPSG:6933 equal-area projection."""
    equal_area = geom.transform(6933, clone=True)
    area_ha = Decimal(str(equal_area.area / 10_000.0))
    return area_ha.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class AgriculturalRegion(models.Model):
    """Saved agricultural field boundary in WGS84 (SRID 4326)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    crop_type = models.CharField(max_length=120, blank=True, default="")
    boundary = models.PolygonField(srid=4326)
    area_ha = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    vertex_count = models.PositiveIntegerField(editable=False, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.area_ha} ha)"

    @property
    def area_hectares(self) -> Decimal:
        """Alias for area_ha."""
        return self.area_ha

    def save(self, *args: object, **kwargs: object) -> None:
        if self.boundary is not None:
            self.area_ha = compute_geodesic_area_ha(self.boundary)
            coords = self.boundary.coords
            self.vertex_count = sum(len(ring) for ring in coords)
        super().save(*args, **kwargs)
