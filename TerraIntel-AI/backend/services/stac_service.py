"""Open-source keyless Sentinel-2 STAC (Element84 Earth Search) & ESA WorldCover COG service."""
from __future__ import annotations

import io
import logging
import math
import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
import rasterio
import requests
from PIL import Image
from rasterio.enums import Resampling
from rasterio.features import geometry_mask, shapes
from rasterio.warp import transform_geom
from rasterio.windows import from_bounds
from shapely.geometry import mapping, shape

from analysis.classification import VigourThresholds, classify_ndvi_array, compute_low_vigour_zones
from analysis.comparison import DeltaNdviBin, bin_delta_ndvi
from analysis.vegetation import compute_ndvi, summarize_ndvi

from .exceptions import ServiceError, ServiceFailureCode
from .storage_service import put_object_bytes

logger = logging.getLogger(__name__)

# Official Element84 Earth Search v1 STAC API (AWS Open Data, no API key required):
# https://earth-search.aws.element84.com/v1
EARTH_SEARCH_STAC_URL = "https://earth-search.aws.element84.com/v1/search"
STAC_S2_COLLECTION = "sentinel-2-l2a"
STAC_TIMEOUT_SECONDS = 30

# Official ESA WorldCover v200 public AWS S3 COG bucket (no API key required):
# https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/
ESA_WORLDCOVER_COG_BASE = (
    "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map"
)


@dataclass(frozen=True)
class StacScene:
    """Sentinel-2 L2A STAC item metadata and public COG asset URLs."""

    scene_id: str
    acquired_at: str
    cloud_cover_pct: float
    red_href: str
    nir_href: str
    scl_href: str
    visual_href: str


def worldcover_tile_url(lon: float, lat: float) -> str:
    """Compute the public ESA WorldCover 10m 2021 v200 3x3-degree COG URL for (lon, lat)."""
    lat_tile = math.floor(lat / 3.0) * 3
    lon_tile = math.floor(lon / 3.0) * 3
    ns = "N" if lat_tile >= 0 else "S"
    ew = "E" if lon_tile >= 0 else "W"
    tile_name = f"{ns}{abs(lat_tile):02d}{ew}{abs(lon_tile):03d}"
    return f"{ESA_WORLDCOVER_COG_BASE}/ESA_WorldCover_10m_2021_v200_{tile_name}_Map.tif"


def search_s2_stac_scenes(
    geometry_geojson: dict[str, Any],
    start_date: str,
    end_date: str,
    limit: int = 10,
) -> list[StacScene]:
    """Query Element84 Earth Search STAC for Sentinel-2 L2A scenes intersecting the AOI."""
    geom = shape(geometry_geojson)
    minx, miny, maxx, maxy = geom.bounds
    payload: dict[str, Any] = {
        "collections": [STAC_S2_COLLECTION],
        "bbox": [minx, miny, maxx, maxy],
        "datetime": f"{start_date}T00:00:00Z/{end_date}T23:59:59Z",
        "limit": limit,
        "sortby": [{"field": "properties.datetime", "direction": "desc"}],
    }
    try:
        resp = requests.post(EARTH_SEARCH_STAC_URL, json=payload, timeout=STAC_TIMEOUT_SECONDS)
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
    except requests.Timeout as exc:
        raise ServiceError(
            ServiceFailureCode.UPSTREAM_TIMEOUT,
            "Element84 Earth Search STAC request timed out.",
        ) from exc
    except requests.RequestException as exc:
        raise ServiceError(
            ServiceFailureCode.SATELLITE_UNAVAILABLE,
            f"Element84 Earth Search STAC request failed: {exc}",
        ) from exc

    scenes: list[StacScene] = []
    for feat in data.get("features", []):
        props = feat.get("properties", {})
        assets = feat.get("assets", {})
        scenes.append(
            StacScene(
                scene_id=str(feat.get("id", "")),
                acquired_at=str(props.get("datetime", "")),
                cloud_cover_pct=float(props.get("eo:cloud_cover", 0.0)),
                red_href=str(assets.get("red", {}).get("href", "")),
                nir_href=str(assets.get("nir", {}).get("href", "")),
                scl_href=str(assets.get("scl", {}).get("href", "")),
                visual_href=str(assets.get("visual", {}).get("href", "")),
            )
        )
    return scenes


_YLGN_9_RGB = [
    (255, 255, 229),
    (247, 252, 185),
    (217, 240, 163),
    (173, 221, 142),
    (120, 198, 121),
    (65, 171, 93),
    (35, 132, 67),
    (0, 104, 55),
    (0, 69, 41),
]

_RDBU_11_RGB = [
    (103, 0, 31),
    (178, 24, 43),
    (214, 96, 77),
    (244, 165, 130),
    (253, 219, 199),
    (247, 247, 247),
    (209, 229, 240),
    (146, 197, 222),
    (67, 147, 195),
    (33, 102, 172),
    (5, 48, 97),
]


def _render_palette_png(
    values: np.ndarray,
    valid_mask: np.ndarray,
    palette: list[tuple[int, int, int]],
    vmin: float,
    vmax: float,
) -> bytes:
    h, w = values.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    safe_vals = np.where(valid_mask, values, vmin)
    clipped = np.clip((safe_vals - vmin) / max(1e-6, (vmax - vmin)), 0.0, 0.9999)
    idx = (clipped * len(palette)).astype(np.int32)
    pal_arr = np.array(palette, dtype=np.uint8)
    rgba[valid_mask, :3] = pal_arr[idx[valid_mask]]
    rgba[valid_mask, 3] = 220
    buf = io.BytesIO()
    Image.fromarray(rgba, mode="RGBA").save(buf, format="PNG")
    return buf.getvalue()


def _render_true_colour_png(
    visual_href: str,
    geometry_geojson: dict[str, Any],
    out_shape: tuple[int, int],
    inside_mask: np.ndarray,
) -> bytes | None:
    if not visual_href:
        return None
    try:
        with rasterio.Env(AWS_NO_SIGN_REQUEST="YES", GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
            with rasterio.open(visual_href) as src:
                geom_src = transform_geom("EPSG:4326", src.crs, geometry_geojson)
                minx, miny, maxx, maxy = shape(geom_src).bounds
                win = from_bounds(minx, miny, maxx, maxy, src.transform)
                win = win.intersection(rasterio.windows.Window(0, 0, src.width, src.height))
                if win.width <= 0 or win.height <= 0:
                    return None
                rgb = src.read(
                    [1, 2, 3],
                    window=win,
                    out_shape=(3, out_shape[0], out_shape[1]),
                    resampling=Resampling.bilinear,
                )
                h, w = out_shape
                rgba = np.zeros((h, w, 4), dtype=np.uint8)
                rgba[:, :, 0] = rgb[0]
                rgba[:, :, 1] = rgb[1]
                rgba[:, :, 2] = rgb[2]
                rgba[inside_mask, 3] = 255
                buf = io.BytesIO()
                Image.fromarray(rgba, mode="RGBA").save(buf, format="PNG")
                return buf.getvalue()
    except Exception:
        return None


def _read_clipped_band(
    href: str,
    geometry_geojson: dict[str, Any],
    *,
    out_shape: tuple[int, int] | None = None,
) -> tuple[np.ndarray, np.ndarray, float, Any, Any]:
    """Read a public COG clipped to geometry_geojson using AWS_NO_SIGN_REQUEST=YES."""
    os.environ["AWS_NO_SIGN_REQUEST"] = "YES"
    with rasterio.Env(AWS_NO_SIGN_REQUEST="YES", GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
        with rasterio.open(href) as src:
            geom_src = transform_geom("EPSG:4326", src.crs, geometry_geojson)
            minx, miny, maxx, maxy = shape(geom_src).bounds
            win = from_bounds(minx, miny, maxx, maxy, src.transform)
            win = win.intersection(rasterio.windows.Window(0, 0, src.width, src.height))
            if win.width <= 0 or win.height <= 0:
                raise ServiceError(
                    ServiceFailureCode.NO_SCENES_FOUND,
                    "Region does not intersect the satellite tile.",
                )
            h = max(1, min(512, int(round(win.height))))
            w = max(1, min(512, int(round(win.width))))
            target_shape = out_shape or (h, w)
            data = src.read(
                1,
                window=win,
                out_shape=target_shape,
                resampling=Resampling.nearest,
            )
            win_transform = src.window_transform(win)
            scale_x = win.width / target_shape[1]
            scale_y = win.height / target_shape[0]
            eff_transform = win_transform * rasterio.Affine.scale(scale_x, scale_y)
            inside = ~geometry_mask(
                [geom_src],
                out_shape=target_shape,
                transform=eff_transform,
                invert=False,
            )
            if src.crs and src.crs.is_projected:
                px_m2 = abs(eff_transform.a * eff_transform.e)
            else:
                lat_c = shape(geometry_geojson).centroid.y
                m_per_deg_lat = 111_320.0
                m_per_deg_lon = 111_320.0 * max(0.1, math.cos(math.radians(lat_c)))
                px_m2 = abs(eff_transform.a * m_per_deg_lon * eff_transform.e * m_per_deg_lat)
            return data.astype(np.float64), inside, px_m2 / 10_000.0, eff_transform, src.crs


def compute_ndvi_stac(
    geometry_geojson: dict[str, Any],
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """
    Compute cropland-scoped NDVI composite using keyless Element84 STAC + ESA WorldCover COGs,
    following the exact 5-step masking order.
    """
    scenes = search_s2_stac_scenes(geometry_geojson, start_date, end_date, limit=5)
    if not scenes:
        raise ServiceError(
            ServiceFailureCode.NO_SCENES_FOUND,
            f"No Sentinel-2 scenes found between {start_date} and {end_date}.",
        )

    centroid = shape(geometry_geojson).centroid
    wc_url = worldcover_tile_url(centroid.x, centroid.y)

    best_scenes = sorted(scenes, key=lambda s: s.cloud_cover_pct)[:3]
    ndvi_stack: list[np.ndarray] = []
    px_area_ha = 0.01
    cropland_mask_ref: np.ndarray | None = None
    inside_ref: np.ndarray | None = None
    ref_transform: Any = None
    ref_crs: Any = None

    for sc in best_scenes:
        if not (sc.red_href and sc.nir_href and sc.scl_href):
            continue
        red, inside, px_ha, eff_transform, src_crs = _read_clipped_band(
            sc.red_href, geometry_geojson
        )
        nir, _, _, _, _ = _read_clipped_band(sc.nir_href, geometry_geojson, out_shape=red.shape)
        scl, _, _, _, _ = _read_clipped_band(sc.scl_href, geometry_geojson, out_shape=red.shape)
        px_area_ha = px_ha
        inside_ref = inside
        ref_transform = eff_transform
        ref_crs = src_crs

        if cropland_mask_ref is None:
            try:
                wc_arr, _, _, _, _ = _read_clipped_band(
                    wc_url, geometry_geojson, out_shape=red.shape
                )
                cropland_mask_ref = (wc_arr == 40) & inside
            except Exception:
                cropland_mask_ref = inside

        # Exact 5-step masking order:
        # 1. region boundary -> 2. WorldCover == 40 -> 3. SCL not in {3,8,9,10,11}
        # 4. cloud -> 5. B8 + B4 > 0
        valid_scl = ~np.isin(scl, [3, 8, 9, 10, 11])
        step_mask = inside & cropland_mask_ref & valid_scl & ((nir + red) > 0)
        ndvi_scene = np.full(red.shape, np.nan, dtype=np.float64)
        ndvi_vals = compute_ndvi(nir[step_mask], red[step_mask])
        ndvi_scene[step_mask] = ndvi_vals
        ndvi_stack.append(ndvi_scene)

    if not ndvi_stack or cropland_mask_ref is None or inside_ref is None:
        raise ServiceError(
            ServiceFailureCode.NO_SCENES_FOUND,
            "No usable Sentinel-2 bands found in STAC items.",
        )

    total_cropland_px = int(np.sum(cropland_mask_ref))
    if total_cropland_px == 0:
        raise ServiceError(
            ServiceFailureCode.NO_CROPLAND,
            "Region contains no ESA WorldCover class 40 cropland. "
            "Switch the Regions map to Satellite view and draw over farmland.",
        )

    composite = np.nanmedian(np.stack(ndvi_stack, axis=0), axis=0)
    summary = summarize_ndvi(composite[cropland_mask_ref], total_cropland_pixels=total_cropland_px)
    if summary.valid_pixel_count == 0:
        raise ServiceError(
            ServiceFailureCode.NO_SCENES_FOUND,
            "All Sentinel-2 observations were masked by cloud/shadow filters.",
        )

    thresholds = VigourThresholds()
    class_stats = classify_ndvi_array(
        composite[cropland_mask_ref], pixel_area_ha=px_area_ha, thresholds=thresholds
    )
    low_zones = compute_low_vigour_zones(
        composite[cropland_mask_ref],
        pixel_area_ha=px_area_ha,
        p50_ndvi=summary.p50_ndvi,
        iqr_ndvi=summary.iqr_ndvi,
        thresholds=thresholds,
    )

    # Render YlGn NDVI PNG + True-Colour PNG overlays
    valid_overlay_mask = cropland_mask_ref & np.isfinite(composite) & (composite >= -0.1)
    overlay_id = uuid.uuid4().hex[:12]
    ndvi_png = _render_palette_png(composite, valid_overlay_mask, _YLGN_9_RGB, 0.0, 0.9)
    ndvi_key = put_object_bytes(f"overlays/{overlay_id}_ndvi.png", ndvi_png, "image/png")
    ndvi_url = f"/media/{ndvi_key}"

    tc_url = ""
    tc_png = _render_true_colour_png(
        best_scenes[0].visual_href, geometry_geojson, composite.shape, inside_ref
    )
    if tc_png:
        tc_key = put_object_bytes(f"overlays/{overlay_id}_tc.png", tc_png, "image/png")
        tc_url = f"/media/{tc_key}"

    # Polygonize relative low-vigour pixels for map display & GeoJSON export
    low_mask = valid_overlay_mask & (composite < thresholds.low_max) & (
        composite < low_zones.relative_cutoff_ndvi
    )
    low_zone_polygons: list[dict[str, Any]] = []
    if np.any(low_mask) and ref_transform is not None and ref_crs is not None:
        for geom_dict, val in shapes(
            low_mask.astype(np.uint8), mask=low_mask, transform=ref_transform
        ):
            if val == 1:
                wgs_geom = transform_geom(ref_crs, "EPSG:4326", geom_dict)
                poly = shape(wgs_geom)
                if poly.is_valid and not poly.is_empty and poly.area > 0:
                    low_zone_polygons.append(
                        {
                            "geometry": mapping(poly),
                            "area_ha": max(0.01, poly.area * (111.32**2) * 100.0),
                        }
                    )
        low_zone_polygons = low_zone_polygons[:50]

    expires_at = (datetime.now(UTC) + timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "mean_ndvi": summary.mean_ndvi,
        "p25_ndvi": summary.p25_ndvi,
        "p50_ndvi": summary.p50_ndvi,
        "p75_ndvi": summary.p75_ndvi,
        "min_ndvi": summary.min_ndvi,
        "max_ndvi": summary.max_ndvi,
        "cropland_area_ha": total_cropland_px * px_area_ha,
        "valid_area_ha": summary.valid_pixel_count * px_area_ha,
        "absolute_low_area_ha": low_zones.absolute_low_area_ha,
        "relative_low_area_ha": low_zones.relative_low_area_ha,
        "valid_pixel_pct": summary.valid_pixel_pct,
        "anomalous_pixel_pct": summary.anomalous_pixel_pct,
        "sampled": False,
        "low_coverage": summary.low_coverage,
        "ndvi_tile_url": ndvi_url,
        "true_colour_tile_url": tc_url,
        "tiles_expires_at": expires_at,
        "scenes": [{"scene_id": s.scene_id, "acquired_at": s.acquired_at} for s in scenes],
        "class_stats": [
            {
                "vigour_class": cs.vigour_class.value,
                "area_ha": cs.area_ha,
                "area_pct": cs.area_pct,
            }
            for cs in class_stats
        ],
        "low_zone_polygons": low_zone_polygons,
    }


def compare_ndvi_stac(
    geometry_geojson: dict[str, Any],
    period_a_start: str,
    period_a_end: str,
    period_b_start: str,
    period_b_end: str,
) -> tuple[float, float, str, str, list[DeltaNdviBin]]:
    """Compare two date ranges using keyless Element84 STAC Sentinel-2 L2A COGs."""
    scenes_a = search_s2_stac_scenes(geometry_geojson, period_a_start, period_a_end, limit=3)
    scenes_b = search_s2_stac_scenes(geometry_geojson, period_b_start, period_b_end, limit=3)
    if not scenes_a or not scenes_b:
        raise ServiceError(
            ServiceFailureCode.NO_SCENES_FOUND,
            "Both comparison periods require at least one Sentinel-2 scene.",
        )

    sc_a = sorted(scenes_a, key=lambda s: s.cloud_cover_pct)[0]
    sc_b = sorted(scenes_b, key=lambda s: s.cloud_cover_pct)[0]

    red_a, inside, px_ha, _, _ = _read_clipped_band(sc_a.red_href, geometry_geojson)
    nir_a, _, _, _, _ = _read_clipped_band(sc_a.nir_href, geometry_geojson, out_shape=red_a.shape)
    scl_a, _, _, _, _ = _read_clipped_band(sc_a.scl_href, geometry_geojson, out_shape=red_a.shape)

    red_b, _, _, _, _ = _read_clipped_band(sc_b.red_href, geometry_geojson, out_shape=red_a.shape)
    nir_b, _, _, _, _ = _read_clipped_band(sc_b.nir_href, geometry_geojson, out_shape=red_a.shape)
    scl_b, _, _, _, _ = _read_clipped_band(sc_b.scl_href, geometry_geojson, out_shape=red_a.shape)

    mask_a = inside & ~np.isin(scl_a, [3, 8, 9, 10, 11]) & ((nir_a + red_a) > 0)
    mask_b = inside & ~np.isin(scl_b, [3, 8, 9, 10, 11]) & ((nir_b + red_b) > 0)

    ndvi_a = np.full(red_a.shape, np.nan, dtype=np.float64)
    ndvi_b = np.full(red_a.shape, np.nan, dtype=np.float64)
    ndvi_a[mask_a] = compute_ndvi(nir_a[mask_a], red_a[mask_a])
    ndvi_b[mask_b] = compute_ndvi(nir_b[mask_b], red_b[mask_b])

    delta_summary = bin_delta_ndvi(ndvi_a, ndvi_b, pixel_area_ha=px_ha)
    valid_diff = np.isfinite(ndvi_a) & np.isfinite(ndvi_b) & (ndvi_a >= -0.1) & (ndvi_b >= -0.1)
    diff_arr = np.where(valid_diff, np.clip(ndvi_b - ndvi_a, -0.5, 0.5), 0.0)
    diff_png = _render_palette_png(diff_arr, valid_diff, _RDBU_11_RGB, -0.5, 0.5)
    diff_key = put_object_bytes(
        f"overlays/{uuid.uuid4().hex[:12]}_diff.png", diff_png, "image/png"
    )
    expires_at = (datetime.now(UTC) + timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return (
        delta_summary.mean_delta_ndvi,
        delta_summary.analysed_area_ha,
        f"/media/{diff_key}",
        expires_at,
        delta_summary.bins,
    )
