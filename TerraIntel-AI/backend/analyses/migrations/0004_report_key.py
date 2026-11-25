from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("analyses", "0003_low_vigour_zone"),
    ]

    operations = [
        migrations.AddField(
            model_name="cropanalysis",
            name="report_object_key",
            field=models.CharField(blank=True, default="", max_length=512),
        ),
    ]
