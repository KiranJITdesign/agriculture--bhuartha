# Open Questions — TerraIntel AI Module 3

1. **PRD §§5–13 & §9 verbatim text:** The bootstrap prompt referenced `[Paste the PRD sections 5 through 13 from the previous document here]` and `[Paste PRD §9 verbatim]`. Please provide the original PRD §§5–13 (especially exact API endpoint paths, HTTP methods, authentication/permission requirements, and request/response JSON schemas in §9) before starting tasks that depend on exact contract shapes (e.g., T03, T07, T11, T12, T20).
2. **Google Earth Engine credentials / project:** Will GEE authentication in development/CI use a service account JSON key or ADC (`earthengine authenticate`), and which GEE Cloud Project ID should be configured in `.env.example`?
3. **Authentication model:** Are API endpoints authenticated via Django session auth, DRF Token, or JWT, or is auth single-tenant/open for local dev?
