"""Checklist service — converts findings into prioritised recovery tasks.

Only findings that represent actionable issues (severity high, medium, or
low) become tasks.  Info-severity findings are informational (e.g., "README
is present") and don't need action items.

Tasks are sorted by priority: critical → high → medium → low.
"""

from __future__ import annotations

from app.scanner.models import Category, Finding, RecoveryTask, Severity

# Priority ranking for sorting (lower = more urgent).
PRIORITY_ORDER: dict[str, int] = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}

# Category-specific rationale templates.
RATIONALE_BY_CATEGORY: dict[Category, str] = {
    Category.DOCUMENTATION:
        "Missing documentation makes it difficult for new contributors to "
        "understand and run the project.",
    Category.DEPENDENCIES:
        "Without properly declared or locked dependencies, the project "
        "cannot be reliably built or deployed.",
    Category.TESTS:
        "Lack of automated tests means changes cannot be verified and "
        "regressions may go unnoticed.",
    Category.CI:
        "No CI configuration means builds and tests are not automated, "
        "risking integration issues.",
    Category.CONTAINERIZATION:
        "Containerization enables reproducible deployments across "
        "different environments.",
    Category.CODE_QUALITY:
        "Technical debt markers indicate areas that need attention before "
        "the project can be reliably revived.",
    Category.SETUP:
        "Setup issues may prevent the project from running correctly.",
}

# Severities that generate tasks (info findings are skipped).
ACTIONABLE_SEVERITIES: frozenset[Severity] = frozenset({
    Severity.CRITICAL,
    Severity.HIGH,
    Severity.MEDIUM,
    Severity.LOW,
})


def generate_tasks(findings: list[Finding]) -> list[RecoveryTask]:
    """Convert findings into prioritised recovery tasks.

    Args:
        findings: The list of findings from a scan.

    Returns:
        Sorted list of RecoveryTask objects (most urgent first).
    """
    tasks: list[RecoveryTask] = []

    for finding in findings:
        if finding.severity not in ACTIONABLE_SEVERITIES:
            continue

        rationale = RATIONALE_BY_CATEGORY.get(
            finding.category,
            "This finding indicates an issue that should be addressed.",
        )

        task = RecoveryTask(
            task_id=f"task-{finding.finding_id}",
            title=finding.title,
            priority=finding.severity.value,
            rationale=rationale,
            evidence=finding.evidence,
            recommended_action=finding.recommendation,
            completed=False,
        )
        tasks.append(task)

    # Sort by priority (most urgent first).
    tasks.sort(key=lambda t: PRIORITY_ORDER.get(t.priority, 99))

    return tasks
