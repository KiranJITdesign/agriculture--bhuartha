# T18 — Compare page (side-by-side synced maps + diverging diff map)

## Goal
Implement the Compare page with side-by-side synchronised Leaflet maps (Period A vs Period B), a diverging `ΔNDVI` difference map using ColorBrewer RdBu 11-class ramp centred at 0 with explicit numeric breakpoints, and a `±0.05` binned area change chart.

## Files to touch
- `frontend/js/pages/compare.js`
- `frontend/js/components/SyncedMaps.js`
- `frontend/js/components/DiffLegend.js`
- `frontend/css/compare.css`
- `frontend/index.html`

## Spec reference
- PRD §§5, 8, 10; `.agent/context/design-tokens.md`

## Verification
Pan and zoom one map on Compare page — verify sibling map and diff map stay synchronised and RdBu legend shows explicit breakpoints.

## Out of scope
- Dashboard summary (T19)

## Result
- Implemented `pages/compare.js`, `components/SyncedMaps.js` (3 synced Leaflet maps), `components/DiffLegend.js` (RdBu 11-class ramp), and `css/compare.css`.
- **Pending browser E2E verification:** Requires running backend `/api/v1/compare/`.

