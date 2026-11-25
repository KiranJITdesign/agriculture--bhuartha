import uuid

import django.contrib.gis.db.models.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AgriculturalRegion",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("crop_type", models.CharField(blank=True, default="", max_length=120)),
                ("boundary", django.contrib.gis.db.models.fields.PolygonField(srid=4326)),
                ("area_ha", models.DecimalField(decimal_places=2, editable=False, max_digits=12)),
                ("vertex_count", models.PositiveIntegerField(default=0, editable=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
