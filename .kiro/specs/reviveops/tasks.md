# ReviveOps MVP — Implementation Tasks

## Phase 1 — Foundation
- [x] Create FastAPI app, `/health`, typed schemas, and pytest setup.
- [x] Create React + TypeScript + Vite app and basic dark “revival console” layout.
- [x] Add frontend API client and health indicator.
- [x] Add README local setup instructions.

## Phase 2 — Scanner
- [x] Implement safe repository traversal and ignore rules.
  - `backend/app/scanner/traversal.py` — `os.walk` with `followlinks=False`, in-place pruning of ignored dirs
  - Symlinks resolving outside root are skipped; unreadable files recorded in `errors`
  - Configurable limits: `max_files`, `max_file_size_bytes`, `max_duration_seconds` (in `config.py`)
- [x] Detect README, manifests, lockfiles, tests, CI, Dockerfile, and scripts.
  - `backend/app/scanner/detectors.py` — 7 detector functions covering all signal types
  - Each detector reports both presence (info) and absence (high/medium/low)
- [x] Detect TODO/FIXME in bounded text files.
  - `detect_todos()` scans text files for TODO/FIXME/HACK/XXX/BUG markers
  - Binary detection via extension allow-list + null-byte fallback; capped at `max_todo_findings`
- [x] Normalize findings and include evidence/recommendation.
  - `backend/app/scanner/models.py` — `Finding` dataclass with `finding_id`, `title`, `category`, `severity`, `evidence`, `recommendation`, `source_path`
  - `POST /api/scans` endpoint in `backend/app/main.py`; `ScanResponse` Pydantic schema in `schemas.py`
  - Findings sorted by severity (most urgent first)
- [x] Add scanner tests for ignore rules, unreadable files, symlinks, and limits.
  - `backend/tests/test_scanner.py` — 44 tests across traversal, detectors, helpers, and integration
  - `backend/tests/test_scan_api.py` — 12 API endpoint tests
  - All 62 tests pass (1 skipped: symlink test on Windows)
- [x] Create a small intentionally dormant demo repository fixture.
  - `backend/demo_repo/` — pyproject.toml manifest, src/ with TODO/FIXME markers
  - Deliberately missing: README, lockfile, tests, CI, Dockerfile

## Phase 3 — Intelligence and workflow
- [x] Implement deterministic 0–100 score and dimension breakdown.
- [x] Convert findings into prioritized checklist tasks.
- [x] Persist scans and checklist status in SQLite.
- [x] Build overview, findings, and checklist UI.
- [x] Add Markdown report renderer and download.

## Phase 4 — Revival and polish
- [x] Revival planner: generate README, smoke test, CI workflow and Dockerfile for what is missing (`backend/app/services/revive.py`).
- [x] Apply the plan to a copy of the repository, never the original; rescan to show before/after score.
- [x] `GET /api/scans/{id}/revival-plan` and `POST /api/scans/{id}/revive` with tests (incl. a Hypothesis property test).
- [x] Revive panel in the UI (preview changes, revive a copy, before/after score).
- [ ] Add optional Ollama adapter with model/config checks.
- [ ] Add deterministic explanation fallback.
- [ ] Add finding detail / explain UI with clear AI labeling.
- [ ] Add loading, empty, and error states; keyboard/accessibility pass.
- [ ] Add end-to-end smoke test for demo scan → report export.

## Phase 5 — Submission readiness
- [ ] Verify clean local install/run from README.
- [ ] Run backend and frontend test suites.
- [ ] Capture demo under 3 minutes.
- [ ] Document Kiro usage and decisions.
- [ ] Commit `.kiro/` artifacts and an open-source license.
- [ ] Confirm public GitHub repo and Devpost submission fields.
