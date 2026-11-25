"""Serializers for AnalysisJob submission and polling."""
from __future__ import annotations

from typing import Any

from rest_framework import serializers

from .models import AnalysisJob, CropAnalysis, VegetationClassStat


class VegetationClassStatSerializer(serializers.ModelSerializer):
    area_ha = serializers.SerializerMethodField()
    area_pct = serializers.SerializerMethodField()

    class Meta:
        model = VegetationClassStat
        fields = ["vigour_class", "area_ha", "area_pct"]

    def get_area_ha(self, obj: VegetationClassStat) -> str:
        return f"{obj.area_ha:.2f}"

    def get_area_pct(self, obj: VegetationClassStat) -> str:
        return f"{obj.area_pct:.2f}"


class CropAnalysisSerializer(serializers.ModelSerializer):
    mean_ndvi = serializers.SerializerMethodField()
    p25_ndvi = serializers.SerializerMethodField()
    p50_ndvi = serializers.SerializerMethodField()
    p75_ndvi = serializers.SerializerMethodField()
    min_ndvi = serializers.SerializerMethodField()
    max_ndvi = serializers.SerializerMethodField()
    cropland_area_ha = serializers.SerializerMethodField()
    valid_area_ha = serializers.SerializerMethodField()
    absolute_low_area_ha = serializers.SerializerMethodField()
    relative_low_area_ha = serializers.SerializerMethodField()
    valid_pixel_pct = serializers.SerializerMethodField()
    anomalous_pixel_pct = serializers.SerializerMethodField()
    tiles = serializers.SerializerMethodField()
    class_stats = VegetationClassStatSerializer(many=True, read_only=True)
    cached = serializers.BooleanField(default=False, read_only=True)

    class Meta:
        model = CropAnalysis
        fields = [
            "id",
            "job",
            "region",
            "start_date",
            "end_date",
            "mean_ndvi",
            "p25_ndvi",
            "p50_ndvi",
            "p75_ndvi",
            "min_ndvi",
            "max_ndvi",
            "cropland_area_ha",
            "valid_area_ha",
            "absolute_low_area_ha",
            "relative_low_area_ha",
            "valid_pixel_pct",
            "anomalous_pixel_pct",
            "sampled",
            "low_coverage",
            "tiles",
            "scenes",
            "class_stats",
            "cached",
            "created_at",
        ]

    def get_mean_ndvi(self, obj: CropAnalysis) -> str:
        return f"{obj.mean_ndvi:.4f}"

    def get_p25_ndvi(self, obj: CropAnalysis) -> str:
        return f"{obj.p25_ndvi:.4f}"

    def get_p50_ndvi(self, obj: CropAnalysis) -> str:
        return f"{obj.p50_ndvi:.4f}"

    def get_p75_ndvi(self, obj: CropAnalysis) -> str:
        return f"{obj.p75_ndvi:.4f}"

    def get_min_ndvi(self, obj: CropAnalysis) -> str:
        return f"{obj.min_ndvi:.4f}"

    def get_max_ndvi(self, obj: CropAnalysis) -> str:
        return f"{obj.max_ndvi:.4f}"

    def get_cropland_area_ha(self, obj: CropAnalysis) -> str:
        return f"{obj.cropland_area_ha:.2f}"

    def get_valid_area_ha(self, obj: CropAnalysis) -> str:
        return f"{obj.valid_area_ha:.2f}"

    def get_absolute_low_area_ha(self, obj: CropAnalysis) -> str:
        return f"{obj.absolute_low_area_ha:.2f}"

    def get_relative_low_area_ha(self, obj: CropAnalysis) -> str:
        return f"{obj.relative_low_area_ha:.2f}"

    def get_valid_pixel_pct(self, obj: CropAnalysis) -> str:
        return f"{obj.valid_pixel_pct:.2f}"

    def get_anomalous_pixel_pct(self, obj: CropAnalysis) -> str:
        return f"{obj.anomalous_pixel_pct:.2f}"

    def get_tiles(self, obj: CropAnalysis) -> dict[str, str]:
        return {
            "ndvi_url": obj.ndvi_tile_url,
            "true_colour_url": obj.true_colour_tile_url,
            "expires_at": obj.tiles_expires_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }


class CompareRequestSerializer(serializers.Serializer):
    region = serializers.UUIDField()
    period_a_start = serializers.DateField()
    period_a_end = serializers.DateField()
    period_b_start = serializers.DateField()
    period_b_end = serializers.DateField()

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["period_a_start"] >= attrs["period_a_end"]:
            raise serializers.ValidationError("period_a_start must be before period_a_end.")
        if attrs["period_b_start"] >= attrs["period_b_end"]:
            raise serializers.ValidationError("period_b_start must be before period_b_end.")
        return attrs


class AnalysisJobCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisJob
        fields = ["id", "region", "start_date", "end_date"]
        read_only_fields = ["id"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["start_date"] >= attrs["end_date"]:
            raise serializers.ValidationError("start_date must be before end_date.")
        return attrs


class AnalysisJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisJob
        fields = [
            "id",
            "region",
            "start_date",
            "end_date",
            "status",
            "stage",
            "progress_pct",
            "failure_code",
            "failure_detail",
            "trace_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
