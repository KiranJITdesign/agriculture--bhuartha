"""URL routes for analyses app."""
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AgronomicCopilotView,
    AnalysisJobViewSet,
    ComparePeriodsView,
    CompareReportPdfView,
    CropAnalysisViewSet,
    CropHealthReportPdfView,
    LowVigourExportView,
)

router = DefaultRouter()
router.register(r"jobs", AnalysisJobViewSet, basename="analysis-job")
router.register(r"analyses", CropAnalysisViewSet, basename="crop-analysis")

urlpatterns = router.urls + [
    path("compare/", ComparePeriodsView.as_view(), name="compare-periods"),
    path("compare/report.pdf", CompareReportPdfView.as_view(), name="compare-report-pdf"),
    path("copilot/", AgronomicCopilotView.as_view(), name="agronomic-copilot"),
    path(
        "analyses/<uuid:analysis_id>/low-vigour.geojson",
        LowVigourExportView.as_view(),
        name="low-vigour-export",
    ),
    path(
        "analyses/<uuid:analysis_id>/report.pdf",
        CropHealthReportPdfView.as_view(),
        name="analysis-report-pdf",
    ),
]
