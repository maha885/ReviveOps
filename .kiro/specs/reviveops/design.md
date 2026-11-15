# ReviveOps MVP — Design

## Architecture
```text
React UI
  ├─ Dashboard / scan state / findings / checklist / report export
  └─ REST client
       ↓
FastAPI
  ├─ Scan API → Scanner → filesystem (read-only)
  ├─ Score engine (pure function)
  ├─ Checklist service
  ├─ Report renderer (Markdown)
  └─ Explanation service → deterministic templates | optional Ollama
       ↓
SQLite (scan metadata + checklist state)
```

## Backend modules
- `app/main.py`: FastAPI app and route registration.
- `app/schemas.py`: Pydantic request/response models.
- `app/scanner/`: traversal, detectors, findings normalization.
- `app/services/scoring.py`: pure deterministic score calculation.
- `app/services/checklist.py`: finding-to-task mapping and state.
- `app/services/report.py`: Markdown rendering.
- `app/services/explainer.py`: fallback templates and optional Ollama adapter.
- `app/db.py`: SQLite connection and schema.

## Frontend screens
1. **Home / Scan** — demo repo CTA, local path input, scan progress.
2. **Overview** — revival score, dimension cards, project signals.
3. **Findings** — filter by severity/category; evidence and recommended action.
4. **Revival checklist** — prioritized tasks, status toggles.
5. **Report** — preview and Markdown download.
6. **Finding detail** — deterministic explanation; optional “Explain with local AI”.

## API contract (initial)
- `GET /health` → `{ "status": "ok" }`
- `POST /api/scans` body `{ "path": "...", "label": "..." }` → scan summary, score, findings, checklist
- `GET /api/scans/{scan_id}` → persisted scan
- `PATCH /api/scans/{scan_id}/tasks/{task_id}` body `{ "completed": true }`
- `POST /api/findings/explain` body `{ "finding": ... , "mode": "template|ollama" }`
- `GET /api/scans/{scan_id}/report` → Markdown content

## Finding model
`id`, `title`, `category`, `severity (critical|high|medium|low|info)`, `evidence`, `recommendation`, `source_path?`.

## Score model
Start at 100; apply bounded, documented penalties for missing/weak project signals. Clamp to 0–100. Display dimensions and evidence. Avoid implying execution success.

## Safety
- Resolve and validate scan root.
- Do not follow symlinks outside root.
- Never execute discovered scripts/commands.
- Skip binary files and files above configured size.
- Limit traversal count and duration.
- Escape repository-derived strings in UI.
