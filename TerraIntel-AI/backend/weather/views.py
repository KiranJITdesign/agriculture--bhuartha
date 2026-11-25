"""HTTP views for /api/v1/weather/ (orchestration only)."""
from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.exceptions import DomainFailure, FailureCode
from regions.models import AgriculturalRegion
from services.exceptions import ServiceError
from services.weather_service import get_weather_summary

from .serializers import WeatherQuerySerializer


class WeatherSummaryView(APIView):
    """Return NASA POWER rainfall, temperature, and 5-year anomaly for a region/window."""

    def get(self, request: Request) -> Response:
        query = WeatherQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        region = get_object_or_404(AgriculturalRegion, id=query.validated_data["region"])
        centroid = region.boundary.centroid

        try:
            summary = get_weather_summary(
                region_id=str(region.id),
                centroid_lat=float(centroid.y),
                centroid_lon=float(centroid.x),
                start_date=query.validated_data["start_date"].isoformat(),
                end_date=query.validated_data["end_date"].isoformat(),
            )
        except ServiceError as exc:
            raise DomainFailure(FailureCode(exc.code.value), exc.message) from exc

        return Response(
            {
                "region": summary.region_id,
                "start_date": summary.start_date,
                "end_date": summary.end_date,
                "total_rainfall_mm": f"{summary.total_rainfall_mm:.2f}",
                "mean_temperature_c": f"{summary.mean_temperature_c:.2f}",
                "baseline_rainfall_mm": f"{summary.baseline_rainfall_mm:.2f}",
                "anomaly_pct": (
                    f"{summary.anomaly_pct:.2f}" if summary.anomaly_pct is not None else None
                ),
                "anomaly_reason": summary.anomaly_reason,
                "cached": summary.cached,
                "daily": [
                    {
                        "date": pt.date,
                        "rainfall_mm": f"{pt.rainfall_mm:.2f}",
                        "temperature_c": f"{pt.temperature_c:.2f}",
                    }
                    for pt in summary.daily
                ],
            }
        )
