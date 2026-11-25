# T14 — Frontend shell: layout, tokens, nav, component library

## Goal
Build the vanilla HTML/CSS/ES-module frontend shell: CSS tokens strictly from `.agent/context/design-tokens.md`, app layout, navigation, `api.js` (single `fetch` wrapper with auth, error parsing, `trace_id`), `chartTheme.js`, and reusable async state components (loading skeleton, empty, error with `trace_id` copy, partial coverage banner).

## Files to touch
- `frontend/index.html`
- `frontend/css/tokens.css`
- `frontend/css/layout.css`
- `frontend/css/components.css`
- `frontend/js/api.js`
- `frontend/js/chartTheme.js`
- `frontend/js/router.js`
- `frontend/js/components/AsyncState.js`
- `frontend/js/components/Nav.js`
- `frontend/js/components/StatCard.js`

## Spec reference
- PRD §10; `.agent/context/design-tokens.md`

## Verification
Serve `frontend/` and run visual QA against `design-tokens.md` and keyboard-only navigation check (`outline: 2px solid var(--accent)` on all interactive elements).

## Out of scope
- Page-specific implementations (T15–T19)

## Result
- Implemented `index.html`, `css/tokens.css`, `css/layout.css`, `css/components.css`, `js/api.js`, `js/chartTheme.js`, `js/router.js`, `js/components/AsyncState.js`, `Nav.js`, and `StatCard.js` using exact `design-tokens.md` tokens.
- **Pending browser visual QA:** Backend API server requires Docker/PostGIS to serve live data.

