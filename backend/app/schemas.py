"""Pydantic request/response models.

Every API response is typed so the frontend and tests can rely on a stable
contract.  Models live here so they can be imported by both route handlers
and the test-suite without circular imports.
"""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Returned by GET /health — lets the UI show backend status and version."""

    status: str
    app: str
    version: str


class RootResponse(BaseModel):
    """Returned by GET / — quick orientation for anyone hitting the API root."""

    name: str
    version: str
    docs: str


# ── Scan: findings (Phase 2) ───────────────────────────────────────────


class FindingSchema(BaseModel):
    """A single finding returned by the scanner."""

    finding_id: str
    title: str
    category: str
    severity: str
    evidence: str
    recommendation: str
    source_path: str | None = None


class ScanRequest(BaseModel):
    """Request body for POST /api/scans."""

    path: str
    label: str | None = None


# ── Phase 3: Score, tasks, report ───────────────────────────────────────


class ScoreDimensionSchema(BaseModel):
    """A single dimension of the revival score."""

    name: str
    score: int
    max_points: int
    explanation: str
    finding_ids: list[str]


class ScoreBreakdownSchema(BaseModel):
    """Full revival score with per-dimension breakdown."""

    total: int
    dimensions: list[ScoreDimensionSchema]
    label: str = "heuristic"
    penalty: int = 0
    penalty_reason: str = ""


class TaskSchema(BaseModel):
    """A recovery checklist task."""

    task_id: str
    title: str
    priority: str
    rationale: str
    evidence: str
    recommended_action: str
    completed: bool


class TaskUpdateRequest(BaseModel):
    """Request body for PATCH /api/scans/{id}/tasks/{task_id}."""

    completed: bool


class ReportResponse(BaseModel):
    """Response body for GET /api/scans/{id}/report."""

    scan_id: str
    repo_name: str
    scanned_at: str
    markdown: str


# ── Scan response (combines findings + score + tasks) ──────────────────


class ScanResponse(BaseModel):
    """Response body for POST /api/scans and GET /api/scans/{id}."""

    scan_id: str
    repo_name: str
    scanned_at: str
    findings: list[FindingSchema]
    file_count: int
    truncated: bool
    errors: list[str]
    label: str | None = None
    score: ScoreBreakdownSchema
    tasks: list[TaskSchema]


# ── Phase 4: revival plan ───────────────────────────────────────────────


class ProposedFileSchema(BaseModel):
    """A starter file ReviveOps proposes adding."""

    path: str
    content: str
    finding_id: str
    rationale: str


class RevivalPlanResponse(BaseModel):
    """Response body for GET /api/scans/{id}/revival-plan."""

    scan_id: str
    project_type: str
    files: list[ProposedFileSchema]
    manual_steps: list[str]


class ReviveResponse(BaseModel):
    """Response body for POST /api/scans/{id}/revive."""

    source_scan_id: str
    files_written: list[str]
    score_before: int
    score_after: int
    revived_scan: ScanResponse
