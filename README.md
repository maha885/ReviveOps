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

1. Scan a local folder, paste a public GitHub repository URL, or click **Use Demo Repository**.
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

## Hosted demo

Live demo: <https://reviveops-0ig9.onrender.com> (free host, so the first load after idle can take about a minute).

A single Docker container can serve both the API and the built UI, so anyone can try ReviveOps from a URL without installing anything.

**What demo mode is.** Setting `REVIVEOPS_DEMO_MODE=true` restricts the server. `POST /api/scans` accepts the bundled demo (`{"path": "demo"}`) or a public GitHub repository (`{"github_url": "..."}`, see [Scan a public GitHub repository](#scan-a-public-github-repository)). Any other `path` returns HTTP 403, so visitors cannot read files on the server. The UI hides the folder-path input and shows a GitHub URL input next to **Use Demo Repository**. Demo mode is off by default, so local use is unchanged. To scan your own local folders, run ReviveOps locally (see [Quick start](#quick-start)).

**Environment variables**

| Variable | Default | Purpose |
| --- | --- | --- |
| `REVIVEOPS_DEMO_MODE` | off | `true`, `1` or `yes` turns on demo mode. The Dockerfile sets it to `true`. |
| `REVIVEOPS_FRONTEND_DIST` | `frontend/dist` in the repo | Folder with the built UI, served in demo mode. The Dockerfile sets it to `/app/frontend/dist`. |
| `REVIVEOPS_REVIVED_MAX_AGE_MINUTES` | `60` | Revived copies (`backend/revived/`) and downloaded GitHub sources (`backend/sources/`) older than this are deleted before a new one is created. |
| `REVIVEOPS_MAX_DOWNLOAD_MB` | `25` | Largest GitHub archive download accepted. |
| `REVIVEOPS_MAX_EXTRACT_MB` | `100` | Largest total uncompressed size extracted. |
| `REVIVEOPS_MAX_EXTRACT_ENTRIES` | `10000` | Largest number of archive entries extracted. |
| `REVIVEOPS_SCAN_RATE_PER_MINUTE` | `10` | GitHub scans allowed per client IP per minute. |
| `REVIVEOPS_DOWNLOAD_TIMEOUT_SECONDS` | `20` | Time limit for the GitHub download. |
| `REVIVEOPS_MAX_CONCURRENT_SCANS` | `2` | GitHub downloads/extractions that may run at once. |
| `PORT` | `8000` | Port the container listens on. Many hosts set this for you. |

The limit variables must be whole numbers of at least 1; an unset, empty or invalid value falls back to the default. No secrets or API keys are needed.

**Build and run with Docker**

```bash
docker build -t reviveops .
docker run -p 8000:8000 reviveops
```

Open <http://localhost:8000>. To use another port, pass `PORT` and map it:

```bash
docker run -e PORT=9000 -p 9000:9000 reviveops
```

**Deploy to a free host.** Any host that runs a Dockerfile works. Two options:

- **Render** — create a *Web Service* from this repository, choose the Docker runtime and the free instance type. Render sets `PORT` and the container reads it. Free web services spin down after about 15 minutes without traffic and take roughly a minute to wake on the next request.
- **Hugging Face Spaces (Docker)** — create a Space with the Docker SDK. Spaces expect the app on port 7860 by default, so either set `app_port: 8000` in the Space's README metadata or run the container with `PORT=7860`. Check Hugging Face's current pricing page to see whether the free hardware tier covers Docker Spaces for your account.

Free-tier limits change, so confirm them on the host's site before relying on them.

**Storage is ephemeral.** The SQLite database, revived copies and downloaded GitHub sources live inside the container. They are lost when the service restarts or is redeployed. Old revived copies and downloaded sources are also removed automatically (see `REVIVEOPS_REVIVED_MAX_AGE_MINUTES`).

## Scan a public GitHub repository

Paste a repository URL into the **GitHub URL** field (shown in the hosted app, and also in local mode) to scan it without cloning it yourself.

- **Accepted URLs:** `https://github.com/<owner>/<repo>`, optionally with a trailing `/`, `.git`, or `/tree/<branch>`. Owner and repo names may contain only letters, digits, `.`, `_` and `-`. The host must be lowercase `github.com` over `https`. Other hosts, `www.`, `http://`, user info, ports, query strings, fragments and `..` are rejected.
- **Default branch only.** A `/tree/<branch>` suffix is accepted but ignored.
- **Public repositories only.** Private or missing repositories return "Repository not found or not public." No tokens or accounts are used.
- **How it works.** The server downloads a zip archive from `codeload.github.com` using the Python standard library (no `git`), refusing redirects to any other host. The archive is extracted safely (entries that would escape the folder, absolute paths and symlinks are skipped), scanned, and the temporary download is deleted. Nothing from the repository is executed. Revive and the revival plan work on these scans like on the demo.
- **API:** `POST /api/scans` with `{"github_url": "https://github.com/<owner>/<repo>"}`. Send exactly one of `path` or `github_url`.

**Limits** (defaults; configurable with the environment variables in the [Hosted demo](#hosted-demo) table): 25 MB download, 100 MB extracted, 10,000 archive entries, 20 second download timeout, 10 scans per minute per client IP, 2 concurrent downloads/extractions.

**Errors you may see**

| HTTP status | Meaning |
| --- | --- |
| 422 | Invalid URL, wrong request shape, or an invalid or unsafe archive |
| 404 | Repository not found or not public |
| 413 | Repository too large (download or extracted size or entry count over the limit) |
| 429 | Too many scans per minute, or too many running at once (rate limit responses include `Retry-After`) |
| 504 | The download timed out |
| 502 | GitHub could not be reached or the download failed |

The rate limit is per server process and kept in memory: it resets when the server restarts and is not shared between instances. Downloaded sources are stored under `backend/sources/` and are ephemeral on a hosted container.
## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/health` | Backend status (polled by the UI) |
| POST | `/api/scans` | Scan a repository: `{"path": "demo"}` for the bundled demo, a local path (local mode), or `{"github_url": "..."}` for a public GitHub repository |
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
