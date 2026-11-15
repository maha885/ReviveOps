"""FastAPI application entry point.

Run locally with:
    uvicorn app.main:app --reload --port 8000
"""

import json
import uuid
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import Database
from app.schemas import (
    FindingSchema,
    HealthResponse,
    ReportResponse,
    RootResponse,
    ScanRequest,
    ScanResponse,
    ScoreBreakdownSchema,
    TaskSchema,
    TaskUpdateRequest,
)
from app.scanner import ScanLimits, scan_repository
from app.scanner.models import (
    Category,
    Finding,
    RecoveryTask,
    ScoreBreakdown,
    ScoreDimension,
    Severity,
)
from app.services.checklist import generate_tasks
from app.services.report import render_report
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


@app.get("/", response_model=RootResponse, tags=["root"])
async def root() -> RootResponse:
    """Basic orientation for anyone hitting the API root."""
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


@app.post("/api/scans", response_model=ScanResponse, tags=["scans"])
async def create_scan(request: ScanRequest) -> ScanResponse:
    """Scan a repository and return findings.

    Send ``{"path": "demo"}`` to scan the bundled dormant demo repository.
    Otherwise pass an absolute or relative path to a local directory.
    """
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

    # Build limits from settings.
    limits = ScanLimits(
        max_files=settings.scan_max_files,
        max_file_size_bytes=settings.scan_max_file_size_bytes,
        max_duration_seconds=settings.scan_max_duration_seconds,
        max_todo_findings=settings.scan_max_todo_findings,
    )

    # Run the scan (file-system errors are caught and recorded, not raised).
    try:
        result = scan_repository(root, limits)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Compute score and generate recovery tasks from findings.
    score = compute_score(result.findings)
    tasks = generate_tasks(result.findings)

    # Persist the scan to SQLite.
    scan_id = uuid.uuid4().hex
    db.save_scan(
        scan_id=scan_id,
        repo_name=result.repo_name,
        scanned_at=result.scanned_at,
        file_count=result.file_count,
        truncated=result.truncated,
        errors=result.errors,
        label=request.label,
        findings_json=json.dumps(
            [asdict(f) for f in result.findings], default=str
        ),
        score_json=json.dumps(asdict(score), default=str),
        tasks_json=json.dumps([asdict(t) for t in tasks], default=str),
    )

    return ScanResponse(
        scan_id=scan_id,
        repo_name=result.repo_name,
        scanned_at=result.scanned_at,
        findings=[FindingSchema(**asdict(f)) for f in result.findings],
        file_count=result.file_count,
        truncated=result.truncated,
        errors=result.errors,
        label=request.label,
        score=ScoreBreakdownSchema(**asdict(score)),
        tasks=[TaskSchema(**asdict(t)) for t in tasks],
    )


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
