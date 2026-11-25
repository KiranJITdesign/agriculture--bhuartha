"""Serializers for /api/v1/weather/."""
from __future__ import annotations

from typing import Any

from rest_framework import serializers


class WeatherQuerySerializer(serializers.Serializer):
    region = serializers.UUIDField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["start_date"] >= attrs["end_date"]:
            raise serializers.ValidationError("start_date must be before end_date.")
        return attrs
