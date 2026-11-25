import uuid

import django.contrib.gis.db.models.fields
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("analyses", "0002_crop_analysis"),
    ]

    operations = [
        migrations.CreateModel(
            name="LowVigourZone",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("zone_type", models.CharField(default="RELATIVE", max_length=16)),
                ("geometry", django.contrib.gis.db.models.fields.PolygonField(srid=4326)),
                ("area_ha", models.DecimalField(decimal_places=2, max_digits=12)),
                (
                    "analysis",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="low_vigour_zones",
                        to="analyses.cropanalysis",
                    ),
                ),
            ],
            options={
                "ordering": ["-area_ha"],
            },
        ),
    ]
