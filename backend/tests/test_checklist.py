"""Tests for the checklist service — finding-to-task conversion.

Run with:
    pytest tests/test_checklist.py
"""

from app.scanner.models import Category, Finding, Severity
from app.services.checklist import generate_tasks, PRIORITY_ORDER


def _f(
    finding_id: str,
    category: Category,
    severity: Severity,
) -> Finding:
    """Helper: build a minimal Finding."""
    return Finding(
        finding_id=finding_id,
        title=f"Test {finding_id}",
        category=category,
        severity=severity,
        evidence="Test evidence",
        recommendation="Test recommendation",
        source_path=None,
    )


class TestTaskGeneration:
    def test_high_severity_generates_task(self):
        """High-severity findings should produce tasks."""
        findings = [_f("doc-readme-missing", Category.DOCUMENTATION, Severity.HIGH)]
        tasks = generate_tasks(findings)
        assert len(tasks) == 1

    def test_medium_severity_generates_task(self):
        """Medium-severity findings should produce tasks."""
        findings = [_f("dep-lockfile-missing", Category.DEPENDENCIES, Severity.MEDIUM)]
        tasks = generate_tasks(findings)
        assert len(tasks) == 1

    def test_low_severity_generates_task(self):
        """Low-severity findings should produce tasks."""
        findings = [_f("docker-dockerfile-missing", Category.CONTAINERIZATION, Severity.LOW)]
        tasks = generate_tasks(findings)
        assert len(tasks) == 1

    def test_info_severity_skipped(self):
        """Info-severity findings should NOT produce tasks."""
        findings = [_f("doc-readme-present", Category.DOCUMENTATION, Severity.INFO)]
        tasks = generate_tasks(findings)
        assert len(tasks) == 0

    def test_mixed_severities(self):
        """Should generate tasks only for actionable severities."""
        findings = [
            _f("doc-readme-present", Category.DOCUMENTATION, Severity.INFO),
            _f("doc-readme-missing", Category.DOCUMENTATION, Severity.HIGH),
            _f("dep-lockfile-missing", Category.DEPENDENCIES, Severity.MEDIUM),
        ]
        tasks = generate_tasks(findings)
        assert len(tasks) == 2  # high + medium, not info


class TestTaskFields:
    def test_task_has_all_required_fields(self):
        """Each task should have all required fields."""
        findings = [_f("doc-readme-missing", Category.DOCUMENTATION, Severity.HIGH)]
        tasks = generate_tasks(findings)
        t = tasks[0]
        assert hasattr(t, "task_id")
        assert hasattr(t, "title")
        assert hasattr(t, "priority")
        assert hasattr(t, "rationale")
        assert hasattr(t, "evidence")
        assert hasattr(t, "recommended_action")
        assert hasattr(t, "completed")

    def test_task_id_format(self):
        """Task ID should be prefixed with 'task-'."""
        findings = [_f("doc-readme-missing", Category.DOCUMENTATION, Severity.HIGH)]
        tasks = generate_tasks(findings)
        assert tasks[0].task_id == "task-doc-readme-missing"

    def test_task_priority_matches_severity(self):
        """Task priority should match the finding severity."""
        findings = [_f("doc-readme-missing", Category.DOCUMENTATION, Severity.HIGH)]
        tasks = generate_tasks(findings)
        assert tasks[0].priority == "high"

    def test_task_completed_defaults_false(self):
        """New tasks should default to not completed."""
        findings = [_f("doc-readme-missing", Category.DOCUMENTATION, Severity.HIGH)]
        tasks = generate_tasks(findings)
        assert tasks[0].completed is False

    def test_task_has_rationale(self):
        """Each task should have a non-empty rationale."""
        findings = [_f("doc-readme-missing", Category.DOCUMENTATION, Severity.HIGH)]
        tasks = generate_tasks(findings)
        assert tasks[0].rationale
        assert len(tasks[0].rationale) > 10

    def test_task_evidence_from_finding(self):
        """Task evidence should come from the finding."""
        f = _f("doc-readme-missing", Category.DOCUMENTATION, Severity.HIGH)
        f.evidence = "No README file detected"
        tasks = generate_tasks([f])
        assert tasks[0].evidence == "No README file detected"

    def test_task_recommended_action_from_finding(self):
        """Task recommended action should come from the finding."""
        f = _f("doc-readme-missing", Category.DOCUMENTATION, Severity.HIGH)
        f.recommendation = "Add a README.md"
        tasks = generate_tasks([f])
        assert tasks[0].recommended_action == "Add a README.md"


class TestTaskOrdering:
    def test_sorted_by_priority(self):
        """Tasks should be sorted by priority (most urgent first)."""
        findings = [
            _f("docker-dockerfile-missing", Category.CONTAINERIZATION, Severity.LOW),
            _f("doc-readme-missing", Category.DOCUMENTATION, Severity.HIGH),
            _f("dep-lockfile-missing", Category.DEPENDENCIES, Severity.MEDIUM),
        ]
        tasks = generate_tasks(findings)
        priorities = [t.priority for t in tasks]
        assert priorities == ["high", "medium", "low"]

    def test_empty_findings_no_tasks(self):
        """No findings should produce no tasks."""
        tasks = generate_tasks([])
        assert tasks == []
