# ReviveOps — Bring Dormant Projects Back to Life

**Hackathon track:** Resurrection  
**Builder:** Solo · Intermediate · Local-first  
**Working title:** ReviveOps

ReviveOps is a local-first AI-assisted project revival workbench. It helps a developer understand a dormant or broken repository, identify setup/build blockers, prioritize repair tasks, and generate a safe, reviewable revival plan. The MVP uses a demo repository and deterministic diagnostics so the product works even without a cloud account or paid AI API.

## MVP user journey
1. Open ReviveOps and load the bundled demo repository (or point to a local folder).
2. Run a repository health scan: project files, dependencies, scripts, tests, TODOs, and common setup issues.
3. View a “revival score,” blocker list, and prioritized checklist.
4. Ask the local AI helper to explain a blocker and suggest a patch/command (Ollama optional).
5. Review a generated revival report and export it as Markdown.

## Local-first architecture
- Frontend: React + TypeScript + Vite + Tailwind (or plain CSS initially)
- API: Python + FastAPI
- Scanner: Python standard library first; optional language-specific adapters
- Storage: SQLite (scan history and user decisions)
- AI: Ollama local model, optional; deterministic templates are the fallback
- Tests: pytest + Vitest
- Run: Docker Compose optional; native local run supported

## Local Setup

### Prerequisites
- **Python 3.11+** — [download](https://www.python.org/downloads/)
- **Node.js 18+** — [download](https://nodejs.org/)

### Project structure

```
ReviveOps_Kiro_Blueprint/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py             # Settings (app name, CORS, scan limits)
│   │   ├── main.py               # FastAPI app + /health, /, POST /api/scans
│   │   ├── schemas.py            # Pydantic models (health, root, scan, finding)
│   │   └── scanner/
│   │       ├── __init__.py
│   │       ├── models.py          # Finding, ScanResult, ScanLimits, enums
│   │       ├── traversal.py       # Safe directory traversal + ignore rules
│   │       ├── detectors.py       # File signal detectors (README, CI, TODO, …)
│   │       └── scanner.py         # Orchestrator: traverse → detect → sort
│   ├── demo_repo/                # Bundled dormant demo repository fixture
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── main.py            # Contains TODO / FIXME markers
│   │   │   └── utils.py            # Contains TODO marker
│   │   ├── pyproject.toml         # Minimal manifest
│   │   └── .gitignore
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_health.py         # Tests for /health and /
│   │   ├── test_scanner.py        # Tests for traversal, detectors, integration
│   │   └── test_scan_api.py       # Tests for POST /api/scans endpoint
│   ├── requirements.txt
│   └── pyproject.toml             # pytest config
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── client.ts           # Typed API client (health + scan)
│   │   ├── components/
│   │   │   ├── HealthIndicator.tsx     # Live backend status badge + card
│   │   │   ├── HealthIndicator.css
│   │   │   ├── ScanPanel.tsx           # Scan input, controls, results display
│   │   │   ├── ScanPanel.css
│   │   │   ├── FindingsList.tsx        # Sorted findings with severity badges
│   │   │   └── FindingsList.css
│   │   ├── App.tsx                # Revival console layout
│   │   ├── App.css
│   │   ├── main.tsx               # React entry point
│   │   └── index.css              # Global theme tokens + dark base
│   ├── index.html
│   ├── vite.config.ts             # Vite + dev-server proxy config
│   ├── tsconfig.json
│   └── package.json
└── README.md
```

### Backend (FastAPI)

```bash
cd backend

# Create a virtual environment
python -m venv .venv

# Activate it:
#   Windows (PowerShell):  .venv\Scripts\Activate.ps1
#   macOS / Linux:         source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the dev server (auto-reloads on changes)
uvicorn app.main:app --reload --port 8000
```

The API is now running at `http://localhost:8000`.
- Health check: `http://localhost:8000/health`
- Scan repository: `POST http://localhost:8000/api/scans` (body: `{"path": "demo"}`)
- Interactive API docs (Swagger UI): `http://localhost:8000/docs`

### Backend tests (pytest)

```bash
cd backend
# Activate the virtual environment first (see above)

pytest
```

### Frontend (React + TypeScript + Vite)

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

The UI is now running at `http://localhost:5173`.

Vite proxies `/health` and `/api/*` to the backend on port 8000, so both
servers must run simultaneously for the health indicator to turn green.

### Frontend production build

```bash
cd frontend
npm run build    # type-check + production build → dist/
npm run preview  # preview the production build locally
```

### Quick start (both terminals)

**Terminal 1 — Backend:**
```bash
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows PowerShell
# source .venv/bin/activate          # macOS / Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser. The health badge in the
header turns green when the backend is online and red with a hint message
when it is unreachable.

## Non-goals for first submission
- Automatically applying code changes without approval
- Sending repository contents to external services by default
- Supporting every language/build system
- Cloud deployment or cloud-provider dependencies

## Build order
1. Scaffold API + UI and health endpoint.
2. Implement demo repo + repository scanner.
3. Build findings/score/checklist UI.
4. Add report export.
5. Add optional Ollama explain/plan endpoint.
6. Polish, test, record demo, document Kiro workflow.

## Definition of done
- `README` has setup/run instructions.
- A user can scan the bundled demo and see meaningful findings.
- Revival score and recommendations are explainable.
- Report exports successfully.
- Tests pass; app runs locally from a clean checkout.
- `.kiro/` artifacts are committed and demonstrate spec-driven development.
