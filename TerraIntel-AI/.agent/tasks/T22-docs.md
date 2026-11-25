# T22 — Docs: README, runbook, ADRs, API reference

## Goal
Write complete developer and operations documentation: `README.md`, operational runbook, Architecture Decision Records in `docs/decisions/`, and API reference matching `api-contract.md`.

## Files to touch
- `README.md`
- `docs/RUNBOOK.md`
- `docs/API.md`
- `docs/decisions/0001-stack-and-layering.md`
- `docs/decisions/0002-ndvi-masking-and-storage.md`

## Spec reference
- PRD §§5–11; `.agent/context/api-contract.md`

## Verification
Follow `README.md` from a clean environment to boot the stack, run `pytest` and `ruff`, and verify all 6 quality signals pass.

## Out of scope
- New application features

## Result
- Created `README.md`, `docs/RUNBOOK.md`, `docs/API.md`, `docs/decisions/0001-stack-and-layering.md`, and `docs/decisions/0002-ndvi-masking-and-storage.md`.

