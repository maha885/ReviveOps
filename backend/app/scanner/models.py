"""Core data models for the repository scanner.

These dataclasses are the scanner's internal representation, kept separate
from the Pydantic API schemas so the scanner has no web-framework dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    """Finding severity levels, ordered from most to least urgent."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Category(str, Enum):
    """Finding categories aligned with project-health dimensions."""

    DOCUMENTATION = "documentation"
    DEPENDENCIES = "dependencies"
    TESTS = "tests"
    CI = "ci"
    CONTAINERIZATION = "containerization"
    CODE_QUALITY = "code_quality"
    SETUP = "setup"


# Convenience ordering for sorting findings by severity (most urgent first).
SEVERITY_ORDER: dict[Severity, int] = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
    Severity.INFO: 4,
}


@dataclass
class Finding:
    """A single observation about the repository.

    Attributes:
        finding_id:     Stable unique identifier within a scan.
        title:           Short human-readable label.
        category:        Which project-health dimension this relates to.
        severity:        Urgency level for prioritisation.
        evidence:        Concrete, observable fact (file name, line content).
        recommendation:  Suggested next action — never auto-executed.
        source_path:     Relative path to the triggering file, or None.
    """

    finding_id: str
    title: str
    category: Category
    severity: Severity
    evidence: str
    recommendation: str
    source_path: str | None = None


@dataclass
class ScanLimits:
    """Configurable safety limits for a single scan."""

    max_files: int = 5000
    max_file_size_bytes: int = 512_000  # 512 KB
    max_duration_seconds: float = 30.0
    max_todo_findings: int = 50


@dataclass
class ScanResult:
    """Complete output of a repository scan."""

    repo_name: str
    scanned_at: str  # ISO-8601 UTC timestamp
    findings: list[Finding] = field(default_factory=list)
    file_count: int = 0
    truncated: bool = False
    errors: list[str] = field(default_factory=list)


# ── Phase 3: Score + Checklist models ──────────────────────────────────


@dataclass
class ScoreDimension:
    """A single dimension of the revival score.

    Attributes:
        name:         Human-readable dimension name.
        score:        Points earned (0 .. max_points).
        max_points:   Maximum possible points for this dimension.
        explanation:   Why this score was assigned.
        finding_ids:   Finding IDs that influenced this dimension.
    """

    name: str
    score: int
    max_points: int
    explanation: str
    finding_ids: list[str] = field(default_factory=list)


@dataclass
class ScoreBreakdown:
    """Full revival score with per-dimension breakdown.

    The score is deterministic: the same findings always produce the same
    result.  ``label`` is always ``"heuristic"`` — it is an estimate, not
    a guarantee the project will run.
    """

    total: int
    dimensions: list[ScoreDimension]
    label: str = "heuristic"
    # Points subtracted from the dimension sum (TODO/FIXME markers).
    penalty: int = 0
    penalty_reason: str = ""


@dataclass
class RecoveryTask:
    """A prioritised action item derived from a finding.

    Attributes:
        task_id:            Stable unique identifier.
        title:              Short human-readable label.
        priority:           "critical" | "high" | "medium" | "low".
        rationale:          Why this task matters.
        evidence:           Concrete observation from the scan.
        recommended_action: What to do — never auto-executed.
        completed:          Whether the user has marked it done.
    """

    task_id: str
    title: str
    priority: str
    rationale: str
    evidence: str
    recommended_action: str
    completed: bool = False
