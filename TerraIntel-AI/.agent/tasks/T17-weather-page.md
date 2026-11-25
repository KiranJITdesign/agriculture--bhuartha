# T17 — Weather page (dual-axis rainfall+temperature, shaded window, CSV export)

## Goal
Implement the Weather page using `chartTheme.js` with a dual-axis Chart.js chart (rainfall `_mm` + temperature `_c`), shaded analysis window, 5-year baseline anomaly display (handling `NO_BASELINE_RAIN`), tooltips showing date and both units, and CSV export.

## Files to touch
- `frontend/js/pages/weather.js`
- `frontend/js/components/WeatherChart.js`
- `frontend/css/weather.css`
- `frontend/index.html`

## Spec reference
- PRD §§5, 8, 10; `.agent/context/design-tokens.md`

## Verification
Open Weather page for a real region/window; verify tooltips show date + both units (`mm`, `°C`) and CSV export downloads valid data.

## Out of scope
- Comparison page (T18)

## Result
- Implemented `pages/weather.js`, `components/WeatherChart.js` (dual-axis mm + C tooltips, CSV export), and `css/weather.css`.
- **Pending browser E2E verification:** Requires running backend `/api/v1/weather/`.

