from django.contrib.gis import admin

from .models import AgriculturalRegion


@admin.register(AgriculturalRegion)
class AgriculturalRegionAdmin(admin.GISModelAdmin):
    list_display = ("name", "crop_type", "area_ha", "vertex_count", "created_at")
    search_fields = ("name", "crop_type")
    readonly_fields = ("id", "area_ha", "vertex_count", "created_at", "updated_at")
