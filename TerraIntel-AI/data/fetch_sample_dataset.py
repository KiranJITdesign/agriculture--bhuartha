"""Download a real-time open-source sample dataset (Sentinel-2 STAC, ESA WorldCover, NASA POWER) into data/."""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import rasterio
import requests
from rasterio.warp import transform_geom
from rasterio.windows import from_bounds
from shapely.geometry import shape

DATA_DIR = Path(__file__).resolve().parent
# Real agricultural farmland polygon in Punjab, India (cropland)
SAMPLE_REGION = {
    "name": "Ludhiana Cropland Sample",
    "crop_type": "Wheat",
    "geometry": {
        "type": "Polygon",
        "coordinates": [
            [
                [75.810, 30.870],
                [75.825, 30.870],
                [75.825, 30.885],
                [75.810, 30.885],
                [75.810, 30.870],
            ]
        ],
    },
}


def download_clipped_cog(href: str, geom_geojson: dict, out_path: Path) -> None:
    os.environ["AWS_NO_SIGN_REQUEST"] = "YES"
    with rasterio.Env(AWS_NO_SIGN_REQUEST="YES", GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
        with rasterio.open(href) as src:
            geom_src = transform_geom("EPSG:4326", src.crs, geom_geojson)
            minx, miny, maxx, maxy = shape(geom_src).bounds
            win = from_bounds(minx, miny, maxx, maxy, src.transform)
            win = win.intersection(rasterio.windows.Window(0, 0, src.width, src.height))
            data = src.read(1, window=win)
            meta = src.meta.copy()
            meta.update(
                {
                    "driver": "GTiff",
                    "height": data.shape[0],
                    "width": data.shape[1],
                    "transform": src.window_transform(win),
                }
            )
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with rasterio.open(out_path, "w", **meta) as dst:
                dst.write(data, 1)


def main() -> None:
    end_dt = datetime.now(UTC).date()
    start_dt = end_dt - timedelta(days=30)
    geom = SAMPLE_REGION["geometry"]
    minx, miny, maxx, maxy = shape(geom).bounds

    # 1. Query Element84 Earth Search STAC (no API key)
    stac_resp = requests.post(
        "https://earth-search.aws.element84.com/v1/search",
        json={
            "collections": ["sentinel-2-l2a"],
            "bbox": [minx, miny, maxx, maxy],
            "datetime": f"{start_dt.isoformat()}T00:00:00Z/{end_dt.isoformat()}T23:59:59Z",
            "limit": 5,
            "sortby": [{"field": "properties.datetime", "direction": "desc"}],
        },
        timeout=30,
    )
    stac_resp.raise_for_status()
    features = stac_resp.json().get("features", [])
    if not features:
        raise RuntimeError("No Sentinel-2 scenes returned from Element84 STAC.")

    best = min(features, key=lambda f: float(f.get("properties", {}).get("eo:cloud_cover", 100.0)))
    scene_id = best["id"]
    assets = best["assets"]

    s2_dir = DATA_DIR / "sentinel2"
    download_clipped_cog(assets["red"]["href"], geom, s2_dir / f"{scene_id}_B04_red.tif")
    download_clipped_cog(assets["nir"]["href"], geom, s2_dir / f"{scene_id}_B08_nir.tif")
    download_clipped_cog(assets["scl"]["href"], geom, s2_dir / f"{scene_id}_SCL.tif")

    # 2. ESA WorldCover 10m v200 (tile N30E075)
    wc_url = (
        "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/"
        "ESA_WorldCover_10m_2021_v200_N30E075_Map.tif"
    )
    wc_path = DATA_DIR / "worldcover" / "N30E075_cropland_clip.tif"
    download_clipped_cog(wc_url, geom, wc_path)

    # 3. NASA POWER daily weather (last 30 days)
    centroid = shape(geom).centroid
    pwr_resp = requests.get(
        "https://power.larc.nasa.gov/api/temporal/daily/point",
        params={
            "parameters": "PRECTOTCORR,T2M",
            "community": "AG",
            "longitude": f"{centroid.x:.4f}",
            "latitude": f"{centroid.y:.4f}",
            "start": start_dt.strftime("%Y%m%d"),
            "end": end_dt.strftime("%Y%m%d"),
            "format": "JSON",
        },
        timeout=20,
    )
    pwr_resp.raise_for_status()
    weather_path = DATA_DIR / "weather" / "nasa_power_sample.json"
    weather_path.parent.mkdir(parents=True, exist_ok=True)
    weather_path.write_text(json.dumps(pwr_resp.json(), indent=2), encoding="utf-8")

    manifest = {
        "region": SAMPLE_REGION,
        "sentinel2_scene_id": scene_id,
        "acquired_at": best["properties"].get("datetime"),
        "cloud_cover_pct": best["properties"].get("eo:cloud_cover"),
        "files": {
            "red": str((s2_dir / f"{scene_id}_B04_red.tif").relative_to(DATA_DIR)),
            "nir": str((s2_dir / f"{scene_id}_B08_nir.tif").relative_to(DATA_DIR)),
            "scl": str((s2_dir / f"{scene_id}_SCL.tif").relative_to(DATA_DIR)),
            "worldcover": str(wc_path.relative_to(DATA_DIR)),
            "weather": str(weather_path.relative_to(DATA_DIR)),
        },
    }
    (DATA_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
