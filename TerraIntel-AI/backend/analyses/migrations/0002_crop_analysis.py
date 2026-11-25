import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("analyses", "0001_initial"),
        ("regions", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CropAnalysis",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("mean_ndvi", models.DecimalField(decimal_places=4, max_digits=6)),
                ("p25_ndvi", models.DecimalField(decimal_places=4, max_digits=6)),
                ("p50_ndvi", models.DecimalField(decimal_places=4, max_digits=6)),
                ("p75_ndvi", models.DecimalField(decimal_places=4, max_digits=6)),
                ("min_ndvi", models.DecimalField(decimal_places=4, max_digits=6)),
                ("max_ndvi", models.DecimalField(decimal_places=4, max_digits=6)),
                ("low_threshold", models.DecimalField(decimal_places=4, default=0.2, max_digits=6)),
                ("moderate_threshold", models.DecimalField(decimal_places=4, default=0.45, max_digits=6)),
                ("high_threshold", models.DecimalField(decimal_places=4, default=0.7, max_digits=6)),
                ("cropland_area_ha", models.DecimalField(decimal_places=2, max_digits=12)),
                ("valid_area_ha", models.DecimalField(decimal_places=2, max_digits=12)),
                ("absolute_low_area_ha", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("relative_low_area_ha", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("valid_pixel_pct", models.DecimalField(decimal_places=2, max_digits=5)),
                ("anomalous_pixel_pct", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("sampled", models.BooleanField(default=False)),
                ("low_coverage", models.BooleanField(default=False)),
                ("ndvi_tile_url", models.TextField(blank=True, default="")),
                ("true_colour_tile_url", models.TextField(blank=True, default="")),
                ("tiles_expires_at", models.DateTimeField()),
                ("scenes", models.JSONField(default=list)),
                ("raster_object_key", models.CharField(blank=True, default="", max_length=512)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "job",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="analysis",
                        to="analyses.analysisjob",
                    ),
                ),
                (
                    "region",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="analyses",
                        to="regions.agriculturalregion",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="VegetationClassStat",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("vigour_class", models.CharField(max_length=16)),
                ("area_ha", models.DecimalField(decimal_places=2, max_digits=12)),
                ("area_pct", models.DecimalField(decimal_places=2, max_digits=5)),
                (
                    "analysis",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="class_stats",
                        to="analyses.cropanalysis",
                    ),
                ),
            ],
            options={
                "ordering": ["vigour_class"],
                "unique_together": {("analysis", "vigour_class")},
            },
        ),
        migrations.AddIndex(
            model_name="cropanalysis",
            index=models.Index(
                fields=["region", "start_date", "end_date", "-created_at"],
                name="analyses_cr_region__f14c27_idx",
            ),
        ),
    ]
