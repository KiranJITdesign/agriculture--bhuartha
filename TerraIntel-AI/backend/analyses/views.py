"""Views for submitting and polling AnalysisJob."""
from __future__ import annotations

import json
from datetime import timedelta

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.exceptions import DomainFailure, FailureCode
from regions.models import AgriculturalRegion
from services.comparison_service import compare_ndvi_periods
from services.copilot_service import ask_agronomic_copilot
from services.exceptions import ServiceError
from services.export_service import build_low_vigour_geojson
from services.report_service import build_report_context, render_compare_pdf, render_crop_health_pdf
from services.storage_service import put_object_bytes

from .models import AnalysisJob, CropAnalysis
from .serializers import (
    AnalysisJobCreateSerializer,
    AnalysisJobSerializer,
    CompareRequestSerializer,
    CropAnalysisSerializer,
)
from .tasks import run_ndvi_analysis_task


class AnalysisJobViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """Submit and poll async crop health analysis jobs."""

    queryset = AnalysisJob.objects.select_related("region").all()

    def get_serializer_class(self):  # type: ignore[override]
        if self.action == "create":
            return AnalysisJobCreateSerializer
        return AnalysisJobSerializer

    def create(self, request: Request, *args: object, **kwargs: object) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cutoff = timezone.now() - timedelta(hours=24)
        cached = (
            CropAnalysis.objects.filter(
                region=serializer.validated_data["region"],
                start_date=serializer.validated_data["start_date"],
                end_date=serializer.validated_data["end_date"],
                created_at__gte=cutoff,
            )
            .prefetch_related("class_stats")
            .first()
        )
        if cached is not None:
            cached.cached = True  # type: ignore[attr-defined]
            return Response(
                {
                    "cached": True,
                    "analysis": CropAnalysisSerializer(cached).data,
                    "job_id": str(cached.job_id),
                },
                status=status.HTTP_200_OK,
            )

        trace_id = getattr(request, "trace_id", "")
        job = serializer.save(trace_id=trace_id)
        async_result = run_ndvi_analysis_task.delay(str(job.id))
        job.celery_task_id = str(getattr(async_result, "id", ""))
        job.save(update_fields=["celery_task_id", "updated_at"])
        out = AnalysisJobSerializer(job).data
        return Response(out, status=status.HTTP_202_ACCEPTED)


class CropAnalysisViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """Read-only access to persisted CropAnalysis results."""

    queryset = CropAnalysis.objects.select_related("region").prefetch_related("class_stats").all()
    serializer_class = CropAnalysisSerializer


class ComparePeriodsView(APIView):
    """Compare two date ranges for a region and return +/-0.05 binned Delta NDVI."""

    def post(self, request: Request) -> Response:
        serializer = CompareRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        region = get_object_or_404(AgriculturalRegion, id=serializer.validated_data["region"])
        try:
            res = compare_ndvi_periods(
                geometry_geojson=json.loads(region.boundary.geojson),
                period_a_start=serializer.validated_data["period_a_start"].isoformat(),
                period_a_end=serializer.validated_data["period_a_end"].isoformat(),
                period_b_start=serializer.validated_data["period_b_start"].isoformat(),
                period_b_end=serializer.validated_data["period_b_end"].isoformat(),
            )
        except ServiceError as exc:
            raise DomainFailure(FailureCode(exc.code.value), exc.message) from exc

        return Response(
            {
                "region": str(region.id),
                "mean_delta_ndvi": f"{res.mean_delta_ndvi:.4f}",
                "analysed_area_ha": f"{res.analysed_area_ha:.2f}",
                "tiles": {
                    "diff_url": res.diff_tile_url,
                    "expires_at": res.tiles_expires_at,
                },
                "bins": [
                    {
                        "bin_min": f"{b.bin_min:.2f}",
                        "bin_max": f"{b.bin_max:.2f}",
                        "area_ha": f"{b.area_ha:.2f}",
                        "area_pct": f"{b.area_pct:.2f}",
                    }
                    for b in res.bins
                ],
            }
        )


class LowVigourExportView(APIView):
    """Download simplified low-vigour zones as GeoJSON (<= 5 MB)."""

    def get(self, request: Request, analysis_id: str) -> HttpResponse:
        analysis = get_object_or_404(
            CropAnalysis.objects.prefetch_related("low_vigour_zones"), id=analysis_id
        )
        features = [
            {
                "geometry": json.loads(zone.geometry.geojson),
                "properties": {
                    "id": str(zone.id),
                    "zone_type": zone.zone_type,
                    "area_ha": f"{zone.area_ha:.2f}",
                    "valid_pixel_pct": f"{analysis.valid_pixel_pct:.2f}",
                },
            }
            for zone in analysis.low_vigour_zones.all()
        ]
        payload = build_low_vigour_geojson(features)
        response = HttpResponse(payload, content_type="application/geo+json")
        response["Content-Disposition"] = (
            f'attachment; filename="low-vigour-{analysis.id}.geojson"'
        )
        return response


class CropHealthReportPdfView(APIView):
    """Generate and download a 2-page PDF report with output imagery and period comparison."""

    def get(self, request: Request, analysis_id: str) -> HttpResponse:
        analysis = get_object_or_404(
            CropAnalysis.objects.select_related("region").prefetch_related("class_stats"),
            id=analysis_id,
        )
        previous_analysis = (
            CropAnalysis.objects.filter(region=analysis.region)
            .exclude(id=analysis.id)
            .exclude(start_date=analysis.start_date, end_date=analysis.end_date)
            .order_by("-end_date", "-created_at")
            .first()
        )
        ctx = build_report_context(analysis, previous_analysis=previous_analysis)
        html = render_to_string("reports/crop_health_report.html", ctx)
        pdf_bytes = render_crop_health_pdf(html, ctx)
        key = f"reports/{analysis.id}.pdf"
        try:
            put_object_bytes(key, pdf_bytes, "application/pdf")
            analysis.report_object_key = key
            analysis.save(update_fields=["report_object_key"])
        except ServiceError:
            pass

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="report-{analysis.id}.pdf"'
        return response


class CompareReportPdfView(APIView):
    """Generate and download a PDF report for a two-period Delta NDVI comparison."""

    def post(self, request: Request) -> HttpResponse:
        region_id = request.data.get("region")
        region = get_object_or_404(AgriculturalRegion, id=region_id)
        pdf_bytes = render_compare_pdf(
            region_name=region.name,
            period_a_start=str(request.data.get("period_a_start", "")),
            period_a_end=str(request.data.get("period_a_end", "")),
            period_b_start=str(request.data.get("period_b_start", "")),
            period_b_end=str(request.data.get("period_b_end", "")),
            mean_delta_ndvi=str(request.data.get("mean_delta_ndvi", "0.0000")),
            analysed_area_ha=str(request.data.get("analysed_area_ha", "0.00")),
            bins=list(request.data.get("bins", [])),
            diff_tile_url=str(request.data.get("diff_tile_url", "")),
        )
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="compare-report-{region.id}.pdf"'
        return response


class AgronomicCopilotView(APIView):
    """Answer agronomic questions grounded in a persisted CropAnalysis."""

    def post(self, request: Request) -> Response:
        question = str(request.data.get("question", "")).strip()
        if not question:
            return Response({"detail": "question is required."}, status=status.HTTP_400_BAD_REQUEST)
        context = request.data.get("context", {})
        if not isinstance(context, dict):
            context = {}
        result = ask_agronomic_copilot(question, context)
        return Response(result, status=status.HTTP_200_OK)
