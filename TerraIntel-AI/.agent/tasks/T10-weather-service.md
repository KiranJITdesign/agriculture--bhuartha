# T10 — weather_service.py — NASA POWER, 7-day cache, summary + anomaly

## Goal
Implement `weather_service.py` fetching NASA POWER rainfall (`_mm`) and temperature (`_c`) for the requested window, caching for 7 days, and computing 5-year baseline anomaly (`anomaly_pct`) while guarding divide-by-zero (`anomaly_pct = null` with reason `NO_BASELINE_RAIN`).

## Files to touch
- `backend/services/weather_service.py`
- `backend/services/tests/test_weather_service.py`

## Spec reference
- PRD §§5, 8, 11

## Verification
```bash
pytest backend/services/tests/test_weather_service.py
```
Values cross-checked against NASA POWER web UI for one date range.

## Out of scope
- Weather REST API endpoint (T11)
- Weather frontend page (T17)

## Result
- `services/weather_service.py` implemented (NASA POWER `PRECTOTCORR`/`T2M`, 7-day cache, `NO_BASELINE_RAIN` zero-baseline guard); `ruff` and `mypy` clean; `test_weather_service.py` passed.

