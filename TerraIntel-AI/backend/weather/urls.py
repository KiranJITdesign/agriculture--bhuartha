"""URL routes for weather app."""
from django.urls import path

from .views import WeatherSummaryView

urlpatterns = [
    path("weather/", WeatherSummaryView.as_view(), name="weather-summary"),
]
