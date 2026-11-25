# T16 — Crop Health page (layer switcher, fixed bordered legend, stats, histogram)

## Goal
Implement the Crop Health page with true-colour / NDVI layer switcher (respecting `tiles.expires_at`), fixed bordered ColorBrewer YlGn 9-class legend (with nodata hatch), cropland-scoped stats with adjacent coverage percentage, Chart.js histogram via `chartTheme.js`, low-vigour GeoJSON download, and all 4 async states + partial coverage banner.

## Files to touch
- `frontend/js/pages/cropHealth.js`
- `frontend/js/components/NdviMap.js`
- `frontend/js/components/NdviLegend.js`
- `frontend/js/components/NdviHistogram.js`
- `frontend/css/crop-health.css`
- `frontend/index.html`

## Spec reference
- PRD §§8, 10; `.agent/context/design-tokens.md`

## Verification
Verify all async states (loading, empty, error, partial, ready), adjacent coverage percentages on every low-vigour stat, and YlGn legend readability.

## Out of scope
- Weather charts (T17)
- PDF generation (T20)

## Result
- Implemented `pages/cropHealth.js`, `components/NdviMap.js` (layer switcher + `tiles.expires_at` check), `components/NdviLegend.js` (YlGn 9-class + nodata hatch), `components/NdviHistogram.js`, and `css/crop-health.css`.
- **Pending browser E2E verification:** Requires running backend & GEE tiles.

