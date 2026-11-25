# T15 — Regions page (Leaflet + leaflet-draw + Nominatim search, live area readout)

## Goal
Implement the Regions page using Leaflet, `leaflet-draw`, and Nominatim search (10s timeout) with live area readout (`_ha`), boundary validation feedback, and persistence via `/api/v1/regions/`.

## Files to touch
- `frontend/js/pages/regions.js`
- `frontend/js/components/RegionMap.js`
- `frontend/js/components/RegionSearch.js`
- `frontend/css/regions.css`
- `frontend/index.html`

## Spec reference
- PRD §§5, 10, 11; `.agent/context/design-tokens.md`

## Verification
Draw a real field polygon on the map, save, reload page — boundary persists and area matches backend `_ha`.

## Out of scope
- Crop Health analysis view (T16)

## Result
- Implemented `pages/regions.js`, `components/RegionMap.js` (Leaflet + leaflet-draw + live geodesic area readout), `components/RegionSearch.js` (Nominatim 10s timeout), and `css/regions.css`.
- **Pending browser E2E verification:** Requires running backend `/api/v1/regions/`.

