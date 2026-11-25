# Agent operating rules — TerraIntel AI Module 3

## Scope discipline
- Implement ONE task from `.agent/tasks/` at a time. Do not build the next task.
- Touch ONLY the files listed in the current task's "Files to touch".
- Do not add a dependency without updating requirements.txt and noting why in docs/CHANGELOG.md.
- If a requirement is ambiguous, STOP and append the question to `.agent/QUESTIONS.md`.
  Do not invent behaviour.

## Code quality bar
- Python: type hints on every public function; ruff + mypy clean on `analysis/` and `services/`;
  no bare except; no print() (use logging); views contain no computation;
  services contain no HTTP concerns.
- `analysis/` functions are pure: no Django imports, take/return plain data (numpy, dataclasses).
- JS: ES modules, no globals, no inline styles (except dynamic map values), one component per file,
  no framework, no build step.
- Every endpoint: serializer validation + permission check + error mapping + integration test
  hitting the real URL.
- Every numeric field name carries its unit (`_ha`, `_mm`, `_c`, `_pct`).

## UI quality bar
- Read `.agent/context/design-tokens.md` before writing CSS. Use ONLY those tokens.
- FORBIDDEN: gradients, emoji anywhere, border-radius > 6px on panels, drop shadows on static
  surfaces, purple/blue accent, glassmorphism, centred hero sections, count-up animations,
  rainbow/jet colour ramps for NDVI, more than one accent hue, icon+label where label suffices.
- Every async surface has FOUR states: loading (skeleton matching final layout), empty
  (explains why + next action), error (inline, retry, trace_id copy), partial (coverage banner).
- No placeholder or lorem content. No fabricated numbers. If data is unavailable, render empty state.

## Honesty rules
- Never fabricate a data source, scene ID, GEE collection name, NASA POWER parameter, or API
  response shape. If unsure, check the official docs and cite the URL in a comment.
- Never silently swallow an exception.
- If a test fails, fix the code — never weaken the test.

## Definition of done (per task)
- [ ] Tests written and passing
- [ ] Verified against real data at least once; the exact command recorded in the task file
- [ ] No TODOs, no commented-out code
- [ ] Task file has a "Result" section with the verification output pasted in
