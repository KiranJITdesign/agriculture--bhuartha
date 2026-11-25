"""Integration tests for /api/v1/regions/ CRUD and boundary validation."""
import math

import pytest
from rest_framework.test import APIClient


def _square_polygon(lon: float, lat: float, delta: float) -> dict:
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [lon, lat],
                [lon + delta, lat],
                [lon + delta, lat + delta],
                [lon, lat + delta],
                [lon, lat],
            ]
        ],
    }


@pytest.mark.django_db
def test_region_crud_and_simplification() -> None:
    client = APIClient()
    # ~100 ha polygon
    resp = client.post(
        "/api/v1/regions/",
        {"name": "North Field", "crop_type": "Maize", "boundary": _square_polygon(0.0, 0.0, 0.01)},
        format="json",
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "North Field"
    assert isinstance(data["area_ha"], str)
    region_id = data["id"]

    # High-vertex circle (>500 vertices) gets simplified to <= 500
    pts = [
        [0.01 * math.cos(2 * math.pi * i / 700), 0.01 * math.sin(2 * math.pi * i / 700)]
        for i in range(700)
    ]
    pts.append(pts[0])
    resp2 = client.post(
        "/api/v1/regions/",
        {"name": "Circle Field", "boundary": {"type": "Polygon", "coordinates": [pts]}},
        format="json",
    )
    assert resp2.status_code == 201
    assert resp2.json()["vertex_count"] <= 500

    # List & Delete
    list_resp = client.get("/api/v1/regions/")
    assert list_resp.status_code == 200
    assert list_resp.json()["count"] == 2

    del_resp = client.delete(f"/api/v1/regions/{region_id}/")
    assert del_resp.status_code == 204


@pytest.mark.django_db
def test_region_validation_errors() -> None:
    client = APIClient()

    # Too small (< 0.1 ha) -> BOUNDARY_INVALID
    tiny = client.post(
        "/api/v1/regions/",
        {"name": "Tiny", "boundary": _square_polygon(0.0, 0.0, 0.00001)},
        format="json",
    )
    assert tiny.status_code == 400
    assert tiny.json()["code"] == "BOUNDARY_INVALID"

    # Too large (> 50,000 ha) -> BOUNDARY_TOO_LARGE
    huge = client.post(
        "/api/v1/regions/",
        {"name": "Huge", "boundary": _square_polygon(0.0, 0.0, 1.0)},
        format="json",
    )
    assert huge.status_code == 400
    assert huge.json()["code"] == "BOUNDARY_TOO_LARGE"
