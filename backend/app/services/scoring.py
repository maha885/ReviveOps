"""Deterministic revival score engine.

A pure function: given a list of Findings, it always produces the same
ScoreBreakdown.  The score is split across five dimensions, each with a
fixed maximum.  The overall total is clamped to 0–100.

The score is labelled "heuristic" — it estimates project health based on
observed signals, not a guarantee the project will run.

Score dimensions and max points::

    Documentation       20
    Dependencies        25
    Testing             25
    CI/CD               15
    Containerization    15
    ──────────────────────
    Total              100
"""

from __future__ import annotations

from app.scanner.models import (
    Category,
    Finding,
    ScoreBreakdown,
    ScoreDimension,
    Severity,
)

# ── Dimension configuration ───────────────────────────────────────────

# Maximum points per dimension (sums to 100).
DIMENSION_MAX: dict[str, int] = {
    "Documentation": 20,
    "Dependencies": 25,
    "Testing": 25,
    "CI/CD": 15,
    "Containerization": 15,
}

# Finding IDs that indicate a signal is *present* (good).
PRESENT_IDS = {
    "doc-readme-present",
    "dep-manifest-present",
    "dep-lockfile-present",
    "test-tests-present",
    "ci-config-present",
    "docker-dockerfile-present",
    "docker-compose-present",
}


def _findings_by_category(
    findings: list[Finding], category: Category
) -> list[Finding]:
    """Return all findings matching a given category."""
    return [f for f in findings if f.category == category]


def _has_finding(findings: list[Finding], finding_id: str) -> bool:
    """Return True if a finding with the given ID exists."""
    return any(f.finding_id == finding_id for f in findings)


def compute_score(findings: list[Finding]) -> ScoreBreakdown:
    """Compute a deterministic 0–100 revival score from scanner findings.

    This is a pure function — the same input always yields the same output.
    """
    dimensions: list[ScoreDimension] = []

    # ── Documentation (20 pts) ──────────────────────────────────────────
    doc_findings = _findings_by_category(findings, Category.DOCUMENTATION)
    doc_ids = [f.finding_id for f in doc_findings]
    if _has_finding(doc_findings, "doc-readme-present"):
        doc_score = 20
        doc_explanation = "README is present — documentation supports onboarding."
    else:
        doc_score = 0
        doc_explanation = "No README detected. Documentation is critical for new contributors."
    dimensions.append(ScoreDimension(
        name="Documentation",
        score=doc_score,
        max_points=20,
        explanation=doc_explanation,
        finding_ids=doc_ids,
    ))

    # ── Dependencies (25 pts) ─────────────────────────────────────────
    dep_findings = _findings_by_category(findings, Category.DEPENDENCIES)
    dep_ids = [f.finding_id for f in dep_findings]
    has_manifest = _has_finding(dep_findings, "dep-manifest-present")
    has_lockfile = _has_finding(dep_findings, "dep-lockfile-present")
    if has_manifest and has_lockfile:
        dep_score = 25
        dep_explanation = "Manifest and lockfile both present — builds are reproducible."
    elif has_manifest:
        dep_score = 18
        dep_explanation = "Manifest present but no lockfile — builds may not be reproducible."
    else:
        dep_score = 0
        dep_explanation = "No package manifest detected — dependencies are undeclared."
    dimensions.append(ScoreDimension(
        name="Dependencies",
        score=dep_score,
        max_points=25,
        explanation=dep_explanation,
        finding_ids=dep_ids,
    ))

    # ── Testing (25 pts) ───────────────────────────────────────────────
    test_findings = _findings_by_category(findings, Category.TESTS)
    test_ids = [f.finding_id for f in test_findings]
    if _has_finding(test_findings, "test-tests-present"):
        test_score = 25
        test_explanation = "Tests are present — changes can be verified."
    else:
        test_score = 0
        test_explanation = "No tests detected — regressions may go unnoticed."
    dimensions.append(ScoreDimension(
        name="Testing",
        score=test_score,
        max_points=25,
        explanation=test_explanation,
        finding_ids=test_ids,
    ))

    # ── CI/CD (15 pts) ─────────────────────────────────────────────────
    ci_findings = _findings_by_category(findings, Category.CI)
    ci_ids = [f.finding_id for f in ci_findings]
    if _has_finding(ci_findings, "ci-config-present"):
        ci_score = 15
        ci_explanation = "CI configuration is present — builds and tests are automated."
    else:
        ci_score = 0
        ci_explanation = "No CI configuration detected — builds and tests are not automated."
    dimensions.append(ScoreDimension(
        name="CI/CD",
        score=ci_score,
        max_points=15,
        explanation=ci_explanation,
        finding_ids=ci_ids,
    ))

    # ── Containerization (15 pts) ──────────────────────────────────────
    docker_findings = _findings_by_category(findings, Category.CONTAINERIZATION)
    docker_ids = [f.finding_id for f in docker_findings]
    has_dockerfile = _has_finding(docker_findings, "docker-dockerfile-present")
    has_compose = _has_finding(docker_findings, "docker-compose-present")
    if has_dockerfile and has_compose:
        docker_score = 15
        docker_explanation = "Dockerfile and Docker Compose both present."
    elif has_dockerfile:
        docker_score = 12
        docker_explanation = "Dockerfile present — containerised builds are possible."
    elif has_compose:
        docker_score = 5
        docker_explanation = "Docker Compose present but no Dockerfile."
    else:
        docker_score = 0
        docker_explanation = "No containerization files detected."
    dimensions.append(ScoreDimension(
        name="Containerization",
        score=docker_score,
        max_points=15,
        explanation=docker_explanation,
        finding_ids=docker_ids,
    ))

    # ── Total (with code-quality penalty) ──────────────────────────────
    total = sum(d.score for d in dimensions)
    code_findings = _findings_by_category(findings, Category.CODE_QUALITY)
    # Each TODO/FIXME marker costs 2 points, capped at 10.
    code_penalty = min(len(code_findings) * 2, 10)
    total = max(0, total - code_penalty)
    penalty_reason = (
        f"{len(code_findings)} TODO/FIXME marker(s) found (2 pts each, max 10)"
        if code_penalty
        else ""
    )

    return ScoreBreakdown(
        total=total,
        dimensions=dimensions,
        penalty=code_penalty,
        penalty_reason=penalty_reason,
    )
