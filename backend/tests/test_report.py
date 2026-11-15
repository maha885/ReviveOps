"""Tests for the Markdown report renderer.

Run with:
    pytest tests/test_report.py
"""

from app.scanner.models import Finding, RecoveryTask, ScoreBreakdown, ScoreDimension, Category, Severity
from app.services.report import render_report


def _score(total: int = 50) -> ScoreBreakdown:
    """Build a minimal ScoreBreakdown."""
    return ScoreBreakdown(
        total=total,
        dimensions=[
            ScoreDimension(
                name="Documentation",
                score=10,
                max_points=20,
                explanation="Partial documentation.",
                finding_ids=["doc-readme-present"],
            ),
        ],
    )


def _finding(finding_id: str = "doc-readme-missing") -> Finding:
    return Finding(
        finding_id=finding_id,
        title="No README found",
        category=Category.DOCUMENTATION,
        severity=Severity.HIGH,
        evidence="No README file detected",
        recommendation="Add a README.md",
        source_path=None,
    )


def _task(task_id: str = "task-doc-readme-missing", completed: bool = False) -> RecoveryTask:
    return RecoveryTask(
        task_id=task_id,
        title="No README found",
        priority="high",
        rationale="Missing documentation blocks onboarding.",
        evidence="No README file detected",
        recommended_action="Add a README.md",
        completed=completed,
    )


class TestReportStructure:
    def test_report_has_title(self):
        """Report should start with the ReviveOps title."""
        md = render_report("test-repo", "2024-01-01T00:00:00Z", _score(), [], [])
        assert "# ReviveOps Revival Report" in md

    def test_report_has_repo_name(self):
        """Report should include the repository name."""
        md = render_report("my-project", "2024-01-01", _score(), [], [])
        assert "my-project" in md

    def test_report_has_timestamp(self):
        """Report should include the scan timestamp."""
        md = render_report("repo", "2024-06-15T12:00:00Z", _score(), [], [])
        assert "2024-06-15T12:00:00Z" in md

    def test_report_has_score(self):
        """Report should include the overall score."""
        md = render_report("repo", "2024-01-01", _score(total=73), [], [])
        assert "73 / 100" in md

    def test_report_has_heuristic_label(self):
        """Report should label the score as heuristic."""
        md = render_report("repo", "2024-01-01", _score(), [], [])
        assert "heuristic" in md

    def test_report_has_dimension_table(self):
        """Report should include a dimension breakdown table."""
        md = render_report("repo", "2024-01-01", _score(), [], [])
        assert "Documentation" in md
        assert "10" in md  # score
        assert "20" in md  # max_points


class TestReportFindings:
    def test_report_includes_findings(self):
        """Report should include finding details."""
        findings = [_finding()]
        md = render_report("repo", "2024-01-01", _score(), findings, [])
        assert "No README found" in md
        assert "No README file detected" in md
        assert "Add a README.md" in md

    def test_report_handles_empty_findings(self):
        """Report should handle no findings gracefully."""
        md = render_report("repo", "2024-01-01", _score(), [], [])
        assert "No findings" in md or "no findings" in md.lower()

    def test_report_includes_source_path(self):
        """Report should include source path when present."""
        f = _finding()
        f.source_path = "src/main.py"
        md = render_report("repo", "2024-01-01", _score(), [f], [])
        assert "src/main.py" in md


class TestReportChecklist:
    def test_report_includes_tasks(self):
        """Report should include checklist tasks."""
        tasks = [_task()]
        md = render_report("repo", "2024-01-01", _score(), [], tasks)
        assert "No README found" in md
        assert "Missing documentation" in md

    def test_report_shows_progress(self):
        """Report should show completion progress."""
        tasks = [
            _task("task-1", completed=True),
            _task("task-2", completed=False),
        ]
        md = render_report("repo", "2024-01-01", _score(), [], tasks)
        assert "1 / 2" in md

    def test_report_handles_empty_tasks(self):
        """Report should handle no tasks gracefully."""
        md = render_report("repo", "2024-01-01", _score(), [], [])
        assert "No action items" in md or "No findings" in md

    def test_report_markdown_checkbox_format(self):
        """Tasks should use Markdown checkbox format."""
        tasks = [_task(completed=True)]
        md = render_report("repo", "2024-01-01", _score(), [], tasks)
        assert "[x]" in md
