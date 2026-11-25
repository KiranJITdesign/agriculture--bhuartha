"""Unit tests for open-source keyless STAC & WorldCover COG helpers."""
from unittest.mock import MagicMock, patch

from services.stac_service import search_s2_stac_scenes, worldcover_tile_url


def test_worldcover_tile_url() -> None:
    url = worldcover_tile_url(lon=78.1, lat=20.5)
    assert url.endswith("ESA_WorldCover_10m_2021_v200_N18E078_Map.tif")


def test_search_s2_stac_scenes() -> None:
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "features": [
            {
                "id": "S2B_43QHC_20261121_0_L2A",
                "properties": {"datetime": "2026-11-21T05:30:00Z", "eo:cloud_cover": 5.2},
                "assets": {
                    "red": {"href": "https://example.com/B04.tif"},
                    "nir": {"href": "https://example.com/B08.tif"},
                    "scl": {"href": "https://example.com/SCL.tif"},
                    "visual": {"href": "https://example.com/TCI.tif"},
                },
            }
        ]
    }
    poly = {
        "type": "Polygon",
        "coordinates": [[[78.0, 20.0], [78.05, 20.0], [78.05, 20.05], [78.0, 20.05], [78.0, 20.0]]],
    }
    with patch("services.stac_service.requests.post", return_value=mock_resp):
        scenes = search_s2_stac_scenes(poly, "2026-11-01", "2026-11-25", limit=3)
    assert len(scenes) == 1
    assert scenes[0].scene_id == "S2B_43QHC_20261121_0_L2A"
