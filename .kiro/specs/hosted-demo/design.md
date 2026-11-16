# Hosted Demo Mode — Design

## Overview
One container runs FastAPI, which also serves the pre-built React app. A settings flag switches the API into a restricted demo mode.

```text
Browser ──► FastAPI (single service)
              ├─ /api/*, /health     JSON API (unchanged)
              ├─ /api/config         { demo_mode }
              └─ /*                  built React app (SPA fallback to index.html)
```

## Backend changes
- `app/config.py`: add `demo_mode: bool = False` (env `REVIVEOPS_DEMO_MODE`), plus `revived_max_age_minutes`.
- `app/main.py`:
  - `GET /api/config` returns `{ "demo_mode": settings.demo_mode }`.
  - `POST /api/scans`: when `demo_mode` is true and `path != "demo"`, raise HTTP 403 ("Hosted demo scans the bundled demo repository only. Run ReviveOps locally to scan your own folders.").
  - Mount `frontend/dist` (path configurable) with `StaticFiles`, registered after all API routes so `/api` and `/health` keep priority; unknown non-API paths return `index.html`.
  - Revive: before creating a new revived copy, delete copies older than `revived_max_age_minutes`.
- `app/services/github_source.py` (stretch only): URL validator + shallow clone helper.
  - Validator is a pure function: accepts only `https://github.com/<owner>/<repo>` with `[A-Za-z0-9_.-]` segments and an optional `.git` suffix; rejects everything else (other hosts, credentials in the URL, ports, query strings, path traversal).
  - Clone with `git clone --depth 1 --no-tags --single-branch`, `-c core.hooksPath=/dev/null`, no submodules, a timeout, and a size cap; remove the temporary folder in a `finally` block.

## Frontend changes
- `src/api/client.ts`: `getConfig()`.
- `src/App.tsx`: fetch config on load; pass `demoMode` to `ScanInput`.
- `src/components/ScanInput.tsx`: in demo mode, hide the path input and show a note; keep "Use Demo Repository".

## Packaging
- Multi-stage `Dockerfile`: stage 1 builds the frontend (`npm ci && npm run build`); stage 2 installs backend requirements, copies the app plus `frontend/dist`, sets `REVIVEOPS_DEMO_MODE=true`, and runs `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}`.
- `.dockerignore` excludes `node_modules`, `.venv`, `.git`, databases, and `backend/revived`.
- Local development is unchanged: Vite dev server plus `uvicorn --reload`.

## Security notes
- The only way to choose what is scanned in demo mode is the literal string `demo`.
- The stretch clone feature is the riskiest part (outbound network, disk, time); it needs strict validation, limits, and no code execution, or it is cut.
- No secrets are required or stored.

## Testing
- Unit: `/api/config`, 403 on non-demo path in demo mode, unchanged behavior with the flag off.
- Property-based (Hypothesis): the GitHub URL validator never accepts a string that is not a plain `https://github.com/<owner>/<repo>` URL, and always accepts well-formed ones.
- Integration: SPA fallback serves `index.html` for unknown non-API paths; API routes are not shadowed by static files.
