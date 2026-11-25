# T06 — analysis/vegetation.py + classification.py — pure functions + unit tests

## Goal
Implement pure, Django-free computation modules `analysis/vegetation.py` and `analysis/classification.py` using numpy/dataclasses for NDVI statistics, anomalous pixel (`< -0.1`) exclusion, vigour class thresholds (`LOW < 0.20`, `MODERATE 0.20-0.45`, `HIGH 0.45-0.70`, `VERY_HIGH > 0.70`), absolute vs relative (`NDVI < low_threshold AND NDVI < p50 - 1.0*IQR`) low-vigour area, and deterministic half-up rounding.

## Files to touch
- `backend/analysis/vegetation.py`
- `backend/analysis/classification.py`
- `backend/analysis/tests/__init__.py`
- `backend/analysis/tests/test_vegetation.py`
- `backend/analysis/tests/test_classification.py`

## Spec reference
- PRD §§7, 8

## Verification
```bash
pytest --cov=analysis --cov-branch backend/analysis/tests/
```
100% branch coverage on threshold logic; `ruff` and `mypy` clean on `analysis/`.

## Out of scope
- Django models or GEE network calls

## Result
- `analysis/vegetation.py` and `analysis/classification.py` implemented as pure NumPy/dataclass functions.
- `pytest --cov=analysis --cov-branch analysis/tests/`: **100% statement and 100% branch coverage** (all tests passed).
- `ruff check analysis` and `mypy analysis`: clean.

