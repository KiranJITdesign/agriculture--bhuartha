"""Unit tests for landcover_service NO_CROPLAND path."""
from unittest.mock import MagicMock, patch

import pytest

from services.exceptions import ServiceError, ServiceFailureCode
from services.landcover_service import compute_cropland_coverage


def test_lake_polygon_raises_no_cropland() -> None:
    lake_geojson = {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [0.01, 0.0], [0.01, 0.01], [0.0, 0.01], [0.0, 0.0]]],
    }
    mock_img = MagicMock()
    mock_img.clip.return_value = mock_img
    mock_img.select.return_value = mock_img
    mock_img.eq.return_value = mock_img
    mock_img.divide.return_value = mock_img
    mock_img.updateMask.return_value = mock_img
    mock_img.reduceRegion.return_value.getInfo.side_effect = [
        {"area": 100.0},  # total area
        {"area": 0.0},    # cropland area == 0 (lake)
    ]

    with (
        patch("services.landcover_service.init_gee"),
        patch("services.landcover_service.ee.Geometry"),
        patch("services.landcover_service.ee.ImageCollection") as mock_ic,
        patch("services.landcover_service.ee.Image.pixelArea", return_value=mock_img),
        patch("services.landcover_service.ee.Reducer.sum"),
    ):
        mock_ic.return_value.first.return_value = mock_img
        with pytest.raises(ServiceError) as exc_info:
            compute_cropland_coverage(lake_geojson)

    assert exc_info.value.code == ServiceFailureCode.NO_CROPLAND
