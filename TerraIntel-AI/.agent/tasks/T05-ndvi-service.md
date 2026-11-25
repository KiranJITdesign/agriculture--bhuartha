# T05 — ndvi_service.py — masking in PRD §8.2 order, median composite, NDVI, tile URL

## Goal
Implement `ndvi_service.py` performing masking in the exact PRD §8.2 order (1. region boundary -> 2. WorldCover == 40 -> 3. SCL not in {3,8,9,10,11} -> 4. MSK_CLDPRB <= 40 -> 5. B8 + B4 > 0), median composite, `(B8 - B4) / (B8 + B4)` clamped `[-1, 1]`, `ee.Image.pixelArea()` areal stats, histogram-derived percentiles (1% sample if >5M pixels), and tile URL generation with `expires_at`.

## Files to touch
- `backend/services/ndvi_service.py`
- `backend/services/tests/test_ndvi_service.py`

## Spec reference
- PRD §§5, 8.2, 9

## Verification
```bash
pytest backend/services/tests/test_ndvi_service.py
```
Mean NDVI over a known field within ±0.03 of Sentinel Hub EO Browser.

## Out of scope
- Pure numpy classification logic (T06)
- `NO_CROPLAND` landcover pre-check (T09)

## Result
- `services/ndvi_service.py` implemented with exact 5-step masking order; `ruff` and `mypy` clean; 2 unit tests in `services/tests/test_ndvi_service.py` passed.
- **Blocked on live GEE verification:** No GEE credentials configured locally.

