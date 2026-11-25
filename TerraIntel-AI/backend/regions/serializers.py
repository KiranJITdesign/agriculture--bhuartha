"""DRF serializers for AgriculturalRegion."""
from __future__ import annotations

import json
from typing import Any

from django.contrib.gis.geos import GEOSException, GEOSGeometry, Polygon
from rest_framework import serializers

from core.exceptions import DomainFailure, FailureCode

from .models import AgriculturalRegion, compute_geodesic_area_ha

MIN_AREA_HA = 0.1
MAX_AREA_HA = 50_000.0
MAX_VERTICES = 500


def _count_vertices(geom: Polygon) -> int:
    return sum(len(ring) for ring in geom.coords)


def simplify_to_max_vertices(geom: Polygon, max_vertices: int = MAX_VERTICES) -> Polygon:
    """Simplify polygon topology-preserving until vertex count <= max_vertices."""
    if _count_vertices(geom) <= max_vertices:
        return geom

    low, high = 1e-6, 0.1
    best = geom
    for _ in range(25):
        mid = (low + high) / 2.0
        candidate = geom.simplify(mid, preserve_topology=True)
        if isinstance(candidate, Polygon) and _count_vertices(candidate) <= max_vertices:
            best = candidate
            high = mid
        else:
            low = mid

    if not isinstance(best, Polygon) or _count_vertices(best) > max_vertices:
        raise DomainFailure(
            FailureCode.BOUNDARY_INVALID,
            f"Boundary could not be simplified to <= {max_vertices} vertices.",
        )
    return best


class AgriculturalRegionSerializer(serializers.ModelSerializer):
    """Serializer for AgriculturalRegion with GeoJSON boundary validation."""

    boundary = serializers.JSONField()
    area_ha = serializers.SerializerMethodField()

    class Meta:
        model = AgriculturalRegion
        fields = [
            "id",
            "name",
            "crop_type",
            "boundary",
            "area_ha",
            "vertex_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "area_ha", "vertex_count", "created_at", "updated_at"]

    def get_area_ha(self, obj: AgriculturalRegion) -> str:
        return f"{obj.area_ha:.2f}"

    def to_representation(self, instance: AgriculturalRegion) -> dict[str, Any]:
        data = super().to_representation(instance)
        data["boundary"] = json.loads(instance.boundary.geojson)
        return data

    def validate_boundary(self, value: Any) -> Polygon:
        if not isinstance(value, dict) or value.get("type") != "Polygon":
            raise DomainFailure(
                FailureCode.BOUNDARY_INVALID,
                "Boundary must be a GeoJSON Polygon.",
            )
        try:
            geom = GEOSGeometry(json.dumps(value), srid=4326)
        except (GEOSException, TypeError, ValueError) as exc:
            raise DomainFailure(
                FailureCode.BOUNDARY_INVALID,
                f"Invalid GeoJSON geometry: {exc}",
            ) from exc

        if not isinstance(geom, Polygon) or not geom.valid or geom.empty:
            raise DomainFailure(
                FailureCode.BOUNDARY_INVALID,
                "Boundary polygon is not topologically valid.",
            )

        geom = simplify_to_max_vertices(geom, MAX_VERTICES)
        area_ha = float(compute_geodesic_area_ha(geom))
        if area_ha < MIN_AREA_HA:
            raise DomainFailure(
                FailureCode.BOUNDARY_INVALID,
                f"Boundary area ({area_ha:.2f} ha) is below minimum {MIN_AREA_HA} ha.",
            )
        if area_ha > MAX_AREA_HA:
            raise DomainFailure(
                FailureCode.BOUNDARY_TOO_LARGE,
                f"Boundary area ({area_ha:.2f} ha) exceeds maximum {MAX_AREA_HA:.0f} ha.",
            )
        return geom
