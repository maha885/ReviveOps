"""FastAPI application entry point.

Run locally with:
    uvicorn app.main:app --reload --port 8000
"""

import json
import shutil
import tempfile
import uuid
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from starlette.routing import Match
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import Database
from app.schemas import (
    FindingSchema,
    HealthResponse,
    ProposedFileSchema,
    ReportResponse,
    ReviveResponse,
    RevivalPlanResponse,
    RootResponse,
    ScanRequest,
    ScanResponse,
    ScoreBreakdownSchema,
    TaskSchema,
    TaskUpdateRequest,
)
from app.scanner import ScanLimits, scan_repository
from app.scanner.traversal import traverse
from app.scanner.models import (
    Category,
    Finding,
    RecoveryTask,
    ScoreBreakdown,
    ScoreDimension,
    Severity,
)
from app.services.checklist import generate_tasks
from app.services.archive import (
    ArchiveTooLarge,
    NotAZip,
    UnsafeArchive,
    safe_extract_zip,
)
from app.services.cleanup import cleanup_old_dirs, cleanup_old_revived
from app.services.download import (
    DownloadError,
    DownloadTimeout,
    DownloadTooLarge,
    RepoNotFound,
    download_archive,
)
from app.services.github_url import InvalidGitHubUrl, archive_url, parse_github_url
from app.services.limits import (
    RateLimited,
    TooManyConcurrent,
    client_key,
    extraction_limiter,
    scan_rate_limiter,
)
from app.services.report import render_report
from app.services.revive import apply_plan_to_copy, build_plan
from app.services.scoring import compute_score

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=settings.description,
)

# Allow the Vite dev server (and common alt ports) to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# SQLite persistence (scan history + checklist state).
BACKEND_DIR = Path(__file__).resolve().parent.parent
db = Database(BACKEND_DIR / settings.database_path)


# ── Helpers: reconstruct typed objects from stored JSON ───────────────


def _reconstruct_finding(d: dict) -> Finding:
    """Build a Finding dataclass from a JSON dict."""
    return Finding(
        finding_id=d["finding_id"],
        title=d["title"],
        category=Category(d["category"]),
        severity=Severity(d["severity"]),
        evidence=d["evidence"],
        recommendation=d["recommendation"],
        source_path=d.get("source_path"),
    )


def _reconstruct_score(d: dict) -> ScoreBreakdown:
    """Build a ScoreBreakdown from a JSON dict."""
    return ScoreBreakdown(
        total=d["total"],
        dimensions=[
            ScoreDimension(
                name=dim["name"],
                score=dim["score"],
                max_points=dim["max_points"],
                explanation=dim["explanation"],
                finding_ids=dim.get("finding_ids", []),
            )
            for dim in d["dimensions"]
        ],
        label=d.get("label", "heuristic"),
        penalty=d.get("penalty", 0),
        penalty_reason=d.get("penalty_reason", ""),
    )


def _reconstruct_task(d: dict) -> RecoveryTask:
    """Build a RecoveryTask from a JSON dict."""
    return RecoveryTask(
        task_id=d["task_id"],
        title=d["title"],
        priority=d["priority"],
        rationale=d["rationale"],
        evidence=d["evidence"],
        recommended_action=d["recommended_action"],
        completed=d.get("completed", False),
    )


def _demo_index() -> Path | None:
    """index.html of the built frontend, only when demo mode is on and it exists."""
    if not settings.demo_mode:
        return None
    index = Path(settings.frontend_dist_path) / "index.html"
    return index if index.is_file() else None


@app.get("/api/config", tags=["config"])
async def get_config() -> dict:
    """Public runtime configuration for the frontend."""
    return {"demo_mode": settings.demo_mode}


@app.get("/", response_model=RootResponse, tags=["root"])
async def root() -> RootResponse:
    """Basic orientation for anyone hitting the API root."""
    index = _demo_index()
    if index is not None:
        return FileResponse(index)  # type: ignore[return-value]
    return RootResponse(
        name=settings.app_name,
        version=settings.app_version,
        docs="/docs",
    )


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """Return the current health status of the application.

    The frontend polls this endpoint to show a live backend indicator.
    """
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
    )


# Path to the bundled demo repository (shipped with the app).
DEMO_REPO_PATH = Path(__file__).resolve().parent.parent / "demo_repo"


def _scan_limits() -> ScanLimits:
    return ScanLimits(
        max_files=settings.scan_max_files,
        max_file_size_bytes=settings.scan_max_file_size_bytes,
        max_duration_seconds=settings.scan_max_duration_seconds,
        max_todo_findings=settings.scan_max_todo_findings,
    )


def _scan_and_persist(
    root: Path, label: str | None, scan_id: str | None = None
) -> ScanResponse:
    """Scan *root*, compute score and tasks, persist, and build the response."""
    # Build limits from settings.
    limits = _scan_limits()

    # Run the scan (file-system errors are caught and recorded, not raised).
    try:
        result = scan_repository(root, limits)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Compute score and generate recovery tasks from findings.
    score = compute_score(result.findings)
    tasks = generate_tasks(result.findings)

    # Persist the scan to SQLite.
    scan_id = scan_id or uuid.uuid4().hex
    db.save_scan(
        scan_id=scan_id,
        repo_name=result.repo_name,
        scanned_at=result.scanned_at,
        file_count=result.file_count,
        truncated=result.truncated,
        errors=result.errors,
        label=label,
        findings_json=json.dumps(
            [asdict(f) for f in result.findings], default=str
        ),
        score_json=json.dumps(asdict(score), default=str),
        tasks_json=json.dumps([asdict(t) for t in tasks], default=str),
        root_path=str(root),
    )

    return ScanResponse(
        scan_id=scan_id,
        repo_name=result.repo_name,
        scanned_at=result.scanned_at,
        findings=[FindingSchema(**asdict(f)) for f in result.findings],
        file_count=result.file_count,
        truncated=result.truncated,
        errors=result.errors,
        label=label,
        score=ScoreBreakdownSchema(**asdict(score)),
        tasks=[TaskSchema(**asdict(t)) for t in tasks],
    )


def _scan_github(http_request: Request, request: ScanRequest) -> ScanResponse:
    """Download a public GitHub repo as a zip, extract it safely, and scan it."""
    try:
        scan_rate_limiter.check(client_key(http_request))
    except RateLimited as exc:
        raise HTTPException(
            status_code=429,
            detail="Too many scans. Please wait and try again.",
            headers={"Retry-After": str(exc.retry_after)},
        )

    try:
        repo = parse_github_url(request.github_url or "")
    except InvalidGitHubUrl as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # Prune old extracted sources before creating a new one.
    scan_id = uuid.uuid4().hex
    source_dir = SOURCES_DIR / scan_id
    cleanup_old_dirs(SOURCES_DIR, settings.revived_max_age_minutes, keep=source_dir)

    try:
        with extraction_limiter.slot():
            tmp_dir = Path(tempfile.mkdtemp(prefix="reviveops-dl-"))
            try:
                try:
                    zip_file = download_archive(
                        archive_url(repo),
                        tmp_dir / "repo.zip",
                        settings.max_download_bytes,
                        settings.download_timeout_seconds,
                    )
                    root = safe_extract_zip(
                        zip_file,
                        source_dir,
                        settings.max_extract_bytes,
                        settings.max_extract_entries,
                    )
                    return _scan_and_persist(
                        root, request.label or f"{repo.owner}/{repo.repo}", scan_id
                    )
                except BaseException:
                    shutil.rmtree(source_dir, ignore_errors=True)
                    raise
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)
    except TooManyConcurrent as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except RepoNotFound:
        raise HTTPException(
            status_code=404, detail="Repository not found or not public."
        )
    except (DownloadTooLarge, ArchiveTooLarge):
        raise HTTPException(
            status_code=413, detail="Repository is too large to scan."
        )
    except DownloadTimeout:
        raise HTTPException(
            status_code=504, detail="Downloading the repository timed out."
        )
    except (UnsafeArchive, NotAZip):
        raise HTTPException(
            status_code=422,
            detail="The repository archive is invalid or unsafe.",
        )
    except DownloadError:
        raise HTTPException(
            status_code=502, detail="Could not download the repository."
        )


# Sync ``def`` on purpose: FastAPI runs it in a worker thread, so the blocking
# download/extract/scan never stalls the event loop. The local-path branch is
# unchanged apart from running in that thread.
@app.post("/api/scans", response_model=ScanResponse, tags=["scans"])
def create_scan(request: ScanRequest, http_request: Request) -> ScanResponse:
    """Scan a repository and return findings.

    Send ``{"path": "demo"}`` to scan the bundled dormant demo repository,
    ``{"path": "<dir>"}`` for a local directory, or
    ``{"github_url": "https://github.com/<owner>/<repo>"}`` for a public repo.
    """
    if request.github_url is not None:
        return _scan_github(http_request, request)

    # Hosted demo: only the bundled demo repo. Checked before any filesystem access.
    if settings.demo_mode and request.path != "demo":
        raise HTTPException(
            status_code=403,
            detail=(
                "Hosted demo scans the bundled demo repository only. "
                "Run ReviveOps locally to scan your own folders."
            ),
        )

    # Resolve the scan root.
    if request.path == "demo":
        root = DEMO_REPO_PATH
        if not root.exists():
            raise HTTPException(
                status_code=404,
                detail="Demo repository not found.",
            )
    else:
        root = Path(request.path).resolve()

    if not root.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Path not found: {request.path}",
        )
    if not root.is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"Not a directory: {request.path}",
        )

    return _scan_and_persist(root, request.label)


@app.get("/api/scans/{scan_id}", response_model=ScanResponse, tags=["scans"])
async def get_scan(scan_id: str) -> ScanResponse:
    """Retrieve a previously persisted scan by ID."""
    scan = db.get_scan(scan_id)
    if scan is None:
        raise HTTPException(
            status_code=404, detail=f"Scan not found: {scan_id}"
        )

    task_statuses = db.get_task_statuses(scan_id)
    findings_data = json.loads(scan["findings"])
    score_data = json.loads(scan["score"])
    tasks_data = json.loads(scan["tasks"])

    # Merge persisted completion states into tasks.
    for t in tasks_data:
        if t["task_id"] in task_statuses:
            t["completed"] = task_statuses[t["task_id"]]

    return ScanResponse(
        scan_id=scan_id,
        repo_name=scan["repo_name"],
        scanned_at=scan["scanned_at"],
        findings=[FindingSchema(**f) for f in findings_data],
        file_count=scan["file_count"],
        truncated=bool(scan["truncated"]),
        errors=json.loads(scan["errors"]),
        label=scan["label"],
        score=ScoreBreakdownSchema(**score_data),
        tasks=[TaskSchema(**t) for t in tasks_data],
    )


@app.patch(
    "/api/scans/{scan_id}/tasks/{task_id}",
    response_model=TaskSchema,
    tags=["scans"],
)
async def update_task_completion(
    scan_id: str, task_id: str, request: TaskUpdateRequest
) -> TaskSchema:
    """Update the completion state of a recovery checklist task."""
    scan = db.get_scan(scan_id)
    if scan is None:
        raise HTTPException(
            status_code=404, detail=f"Scan not found: {scan_id}"
        )

    tasks_data = json.loads(scan["tasks"])
    task = next(
        (t for t in tasks_data if t["task_id"] == task_id), None
    )
    if task is None:
        raise HTTPException(
            status_code=404, detail=f"Task not found: {task_id}"
        )

    db.update_task_status(scan_id, task_id, request.completed)
    task["completed"] = request.completed
    return TaskSchema(**task)


@app.get(
    "/api/scans/{scan_id}/report",
    response_model=ReportResponse,
    tags=["scans"],
)
async def get_scan_report(scan_id: str) -> ReportResponse:
    """Generate and return a Markdown revival report for a scan."""
    scan = db.get_scan(scan_id)
    if scan is None:
        raise HTTPException(
            status_code=404, detail=f"Scan not found: {scan_id}"
        )

    task_statuses = db.get_task_statuses(scan_id)
    findings = [
        _reconstruct_finding(f) for f in json.loads(scan["findings"])
    ]
    score = _reconstruct_score(json.loads(scan["score"]))
    tasks = [_reconstruct_task(t) for t in json.loads(scan["tasks"])]
    for t in tasks:
        if t.task_id in task_statuses:
            t.completed = task_statuses[t.task_id]

    markdown = render_report(
        repo_name=scan["repo_name"],
        scanned_at=scan["scanned_at"],
        score=score,
        findings=findings,
        tasks=tasks,
        file_count=scan["file_count"],
        truncated=bool(scan["truncated"]),
    )

    return ReportResponse(
        scan_id=scan_id,
        repo_name=scan["repo_name"],
        scanned_at=scan["scanned_at"],
        markdown=markdown,
    )


REVIVED_DIR = BACKEND_DIR / "revived"
SOURCES_DIR = BACKEND_DIR / "sources"


def _load_source(scan_id: str):
    """Return (scan row, source root) or raise the right HTTP error."""
    scan = db.get_scan(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail=f"Scan not found: {scan_id}")
    root_path = scan.get("root_path")
    if not root_path or not Path(root_path).is_dir():
        raise HTTPException(
            status_code=409,
            detail="The scanned repository is no longer available. Run a new scan.",
        )
    return scan, Path(root_path)


@app.get(
    "/api/scans/{scan_id}/revival-plan",
    response_model=RevivalPlanResponse,
    tags=["revival"],
)
async def get_revival_plan(scan_id: str) -> RevivalPlanResponse:
    """Preview the starter files ReviveOps would add. Changes nothing."""
    scan, root = _load_source(scan_id)
    findings = [_reconstruct_finding(f) for f in json.loads(scan["findings"])]
    traversal = traverse(root, _scan_limits())
    plan = build_plan(scan["repo_name"], [rel for _, rel in traversal.files], findings)
    return RevivalPlanResponse(
        scan_id=scan_id,
        project_type=plan.project_type,
        files=[ProposedFileSchema(**asdict(f)) for f in plan.files],
        manual_steps=plan.manual_steps,
    )


@app.post(
    "/api/scans/{scan_id}/revive",
    response_model=ReviveResponse,
    tags=["revival"],
)
async def revive_repository(scan_id: str) -> ReviveResponse:
    """Apply the revival plan to a *copy* of the repository and rescan it.

    The original repository is never modified. The copy lives under
    ``backend/revived/<scan_id>`` and is scanned like any other repo so the
    before/after score can be compared.
    """
    scan, root = _load_source(scan_id)
    before = _reconstruct_score(json.loads(scan["score"]))
    findings = [_reconstruct_finding(f) for f in json.loads(scan["findings"])]
    traversal = traverse(root, _scan_limits())
    plan = build_plan(scan["repo_name"], [rel for _, rel in traversal.files], findings)

    dest = REVIVED_DIR / scan_id / scan["repo_name"]
    cleanup_old_revived(
        REVIVED_DIR, settings.revived_max_age_minutes, keep=REVIVED_DIR / scan_id
    )
    written = apply_plan_to_copy(traversal.files, plan, dest)
    revived = _scan_and_persist(dest, f"revived from {scan_id[:8]}")

    return ReviveResponse(
        source_scan_id=scan_id,
        files_written=written,
        score_before=before.total,
        score_after=revived.score.total,
        revived_scan=revived,
    )


# -- Hosted demo: serve the built frontend (must stay registered LAST) --


_ALL_METHODS = ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]


@app.api_route("/{full_path:path}", methods=_ALL_METHODS, include_in_schema=False)
async def spa_fallback(full_path: str, request: Request):
    """Serve frontend assets / index.html in demo mode; otherwise behave as if
    this route did not exist (404, or 405 when a real route has another method)."""
    # A real route that matches the path but not the method must still give 405,
    # exactly as before this catch-all existed.
    allowed: set[str] = set()
    for route in request.app.router.routes:
        if getattr(route, "endpoint", None) is spa_fallback:
            continue
        match, _ = route.matches(request.scope)
        if match == Match.PARTIAL:
            allowed |= set(getattr(route, "methods", None) or [])
    if allowed:
        raise HTTPException(
            status_code=405,
            detail="Method Not Allowed",
            headers={"Allow": ", ".join(sorted(allowed))},
        )

    index = _demo_index()
    if (
        index is None
        or request.method not in ("GET", "HEAD")
        or full_path == "api"
        or full_path.startswith("api/")
    ):
        raise HTTPException(status_code=404, detail="Not Found")

    dist = index.parent.resolve()
    try:
        candidate = (dist / full_path).resolve()
        if candidate.is_file() and candidate.is_relative_to(dist):
            return FileResponse(candidate)
    except (OSError, ValueError):
        pass
    return FileResponse(index)