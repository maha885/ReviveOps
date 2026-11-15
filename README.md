# ReviveOps — Bring Dormant Projects Back to Life

**Kiroween 2026 · Category: Resurrection**

ReviveOps is a local-first workbench for reviving abandoned repositories. Point it at a codebase and it tells you how healthy the project is, gives you a prioritized recovery checklist, and can generate the missing starter files (README, smoke test, CI workflow, Dockerfile) — applied to a **copy**, so your original repository is never touched.

> Demo result: the bundled dormant repository goes from **8 / 100** to **80 / 100** after one click.

## Why

Everyone has inherited a repo that has no README, no tests, no CI, and no idea how to run it. Getting it moving again is slow, boring, and easy to get wrong. ReviveOps turns that first hour of detective work into a repeatable, explainable process.

## Features

- **Safe repository scanner** — detects READMEs, dependency manifests and lockfiles, tests, CI configuration, Dockerfiles/Compose, and TODO/FIXME-style markers. It never executes anything from the scanned repo, never follows symlinks outside the root, skips dependency/build folders, and enforces file-count, file-size and time limits.
- **Explainable revival score (0–100)** — five weighted dimensions (Documentation, Dependencies, Testing, CI/CD, Containerization) plus a visible code-quality penalty. The score is labelled *heuristic*: it estimates readiness, it does not guarantee the project builds.
- **Prioritized recovery checklist** — every task links back to concrete evidence and a recommended action. Completion is saved.
- **Revive action** — preview and then apply generated starter files to a copy of the repository, rescan it, and compare the score before and after. Existing files are never overwritten. Things that need real tooling (such as a lockfile) are listed as manual steps instead of faked.
- **Markdown revival report** — generate and download a report for any scan.
- **Saved scans** — scans and checklist progress are stored in a local SQLite database.
- **No cloud, no account, no AI required** — everything is deterministic and runs on your machine.

## How it works

1. Scan a local folder, or click **Use Demo Repository**.
2. Read the score, findings, and recovery checklist.
3. Click **Preview changes** to see exactly which files would be added and why.
4. Click **Revive a copy** to write them into `backend/revived/<scan-id>/`, rescan, and see the score before and after.
5. Tick off the manual steps and download the report.

## Quick start

**Prerequisites:** Python 3.11+ and Node.js 18+.

**Terminal 1 — backend**

```bash
cd backend
python -m venv .venv
# Windows (PowerShell):  .venv\Scripts\Activate.ps1
# macOS / Linux:         source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — frontend**

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. The sidebar shows **Backend Online** when the API is reachable. Click **Use Demo Repository** to try it without any setup.

API docs (Swagger UI): <http://localhost:8000/docs>

### Run the tests

```bash
cd backend
python -m pytest
```

### Production build of the UI

```bash
cd frontend
npm run build
```

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/health` | Backend status (polled by the UI) |
| POST | `/api/scans` | Scan a repository (`{"path": "demo"}` for the bundled demo) |
| GET | `/api/scans/{id}` | Fetch a saved scan |
| PATCH | `/api/scans/{id}/tasks/{task_id}` | Mark a checklist task done / not done |
| GET | `/api/scans/{id}/report` | Markdown revival report |
| GET | `/api/scans/{id}/revival-plan` | Preview the starter files that would be added (changes nothing) |
| POST | `/api/scans/{id}/revive` | Apply the plan to a **copy**, rescan, return before/after score |

## Project layout

```
.kiro/                     Kiro specs and steering documents
backend/
  app/
    main.py                FastAPI app and endpoints
    scanner/               Safe traversal, detectors, scan orchestration
    services/              scoring.py, checklist.py, report.py, revive.py
    db.py                  SQLite persistence (scans, checklist state)
  demo_repo/               Bundled dormant repository used for the demo
  tests/                   pytest suite (includes a Hypothesis property test)
frontend/                  React + TypeScript + Vite UI
```

## Safety design

- Scanning only reads file metadata and text; nothing from the scanned repository is executed.
- Symlinks that resolve outside the repository root are skipped.
- Revival writes only to a copy under `backend/revived/`, blocks path traversal, and never overwrites an existing file.
- Everything stays on your machine; no repository content is sent to any external service.

## Built with Kiro

The project was developed spec-first. The specs and steering documents live in [`.kiro/`](.kiro/):

- `.kiro/specs/reviveops/` — requirements, design, and the phase-by-phase task list
- `.kiro/steering/` — product principles and technical conventions that guided implementation

The foundation, scanner, scoring, checklist, persistence and report features were built with Kiro from these specs. The Revive action and its tests were added afterwards with other AI assistance and the Kiro editor.

## Limitations

- The score is a heuristic based on repository signals; it does not build or run the project.
- Generated files are generic starting points and should be reviewed and adapted.
- Python and Node.js projects get the most useful output; other project types get a README and manual steps.
- Lockfiles cannot be generated without the real package manager, so they stay a manual step.
- Optional local-AI explanations (e.g. Ollama) are planned but not implemented.

## License

[MIT](LICENSE)
