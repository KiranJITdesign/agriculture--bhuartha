# T19 — Dashboard (stat strip, region table, attention list)

## Goal
Implement the Dashboard page displaying the top stat strip (`tabular-nums`, units, adjacent coverage percentages), region summary table, and low-vigour attention list linking directly to Crop Health analyses.

## Files to touch
- `frontend/js/pages/dashboard.js`
- `frontend/js/components/RegionTable.js`
- `frontend/js/components/AttentionList.js`
- `frontend/css/dashboard.css`
- `frontend/index.html`

## Spec reference
- PRD §10; `.agent/context/design-tokens.md`

## Verification
Verify dashboard stat strip numbers reconcile exactly with the region table and every low-vigour area displays its coverage percentage adjacent.

## Out of scope
- PDF report export (T20)

## Result
- Implemented `pages/dashboard.js`, `components/RegionTable.js`, `components/AttentionList.js`, and `css/dashboard.css`.
- **Pending browser E2E verification:** Requires running backend `/api/v1/regions/` and `/api/v1/analyses/`.

