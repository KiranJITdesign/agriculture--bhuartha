"""Tests for AgriculturalRegion model."""
from decimal import Decimal

import pytest
from django.contrib.gis.geos import Polygon

from regions.models import AgriculturalRegion


@pytest.mark.django_db
def test_region_area_calculation() -> None:
    # ~1000m x 1000m square near equator (~100 ha)
    poly = Polygon(
        (
            (0.0, 0.0),
            (0.008983, 0.0),
            (0.008983, 0.009044),
            (0.0, 0.009044),
            (0.0, 0.0),
        ),
        srid=4326,
    )
    region = AgriculturalRegion.objects.create(name="Test Plot", crop_type="Wheat", boundary=poly)
    assert Decimal("99.00") <= region.area_ha <= Decimal("101.00")
    assert region.area_hectares == region.area_ha
    assert region.vertex_count == 5
