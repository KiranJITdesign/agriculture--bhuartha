# ADR 0002: NDVI Masking Order and Object Storage

## Status
Accepted

## Decision
- Sentinel-2 (`COPERNICUS/S2_SR_HARMONIZED`) masking executes in exact order:
  1. Region boundary
  2. ESA WorldCover class 40 (`ESA/WorldCover/v200`)
  3. `SCL` not in `{3, 8, 9, 10, 11}`
  4. `MSK_CLDPRB <= 40`
  5. `B8 + B4 > 0`
- Areal statistics use `ee.Image.pixelArea()`.
- Rasters and generated PDF reports are stored in MinIO/S3; PostgreSQL stores keys and metadata only.
