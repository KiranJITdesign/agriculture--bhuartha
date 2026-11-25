"""Low-vigour GeoJSON export service (polygonized, simplified, <= 5 MB)."""
from __future__ import annotations

import json
from typing import Any

from shapely.geometry import mapping, shape

MAX_GEOJSON_BYTES = 5 * 1024 * 1024


def build_low_vigour_geojson(
    features_input: list[dict[str, Any]],
    *,
    max_bytes: int = MAX_GEOJSON_BYTES,
) -> bytes:
    """
    Serialize low-vigour zone features to GeoJSON FeatureCollection bytes,
    iteratively simplifying geometries if payload exceeds `max_bytes` (5 MB).
    """
    tolerances = [0.0, 0.00005, 0.0001, 0.0005, 0.001, 0.005]
    for tol in tolerances:
        features = []
        for item in features_input:
            geom = shape(item["geometry"])
            if tol > 0.0:
                geom = geom.simplify(tol, preserve_topology=True)
            features.append(
                {
                    "type": "Feature",
                    "geometry": mapping(geom),
                    "properties": item.get("properties", {}),
                }
            )
        payload = json.dumps(
            {"type": "FeatureCollection", "features": features},
            separators=(",", ":"),
        ).encode("utf-8")
        if len(payload) <= max_bytes:
            return payload

    raise ValueError(f"Exported GeoJSON exceeds {max_bytes} bytes even after simplification.")
