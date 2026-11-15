"""Tests for the deterministic revival score engine.

Run with:
    pytest tests/test_scoring.py
"""

from app.scanner.models import Category, Finding, Severity
from app.services.scoring import compute_score, DIMENSION_MAX


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


# ── Dimension structure ────────────────────────────────────────────────


class TestScoreStructure:
    def test_five_dimensions(self):
        """Score should always have exactly 5 dimensions."""
        score = compute_score([])
        assert len(score.dimensions) == 5

    def test_dimension_max_points_sum_to_100(self):
        """Max points across all dimensions should total 100."""
        assert sum(DIMENSION_MAX.values()) == 100

    def test_dimension_names(self):
        """Dimensions should have the expected names."""
        score = compute_score([])
        names = [d.name for d in score.dimensions]
        assert "Documentation" in names
        assert "Dependencies" in names
        assert "Testing" in names
        assert "CI/CD" in names
        assert "Containerization" in names

    def test_label_is_heuristic(self):
        """Score label should always be 'heuristic'."""
        score = compute_score([])
        assert score.label == "heuristic"


# ── Empty repo (all missing) ──────────────────────────────────────────


class TestEmptyRepo:
    def test_empty_repo_scores_zero(self):
        """A repo with no signals should score 0."""
        findings = [
            _f("doc-readme-missing", Category.DOCUMENTATION, Severity.HIGH),
            _f("dep-manifest-missing", Category.DEPENDENCIES, Severity.HIGH),
            _f("dep-lockfile-missing", Category.DEPENDENCIES, Severity.MEDIUM),
            _f("test-tests-missing", Category.TESTS, Severity.HIGH),
            _f("ci-config-missing", Category.CI, Severity.MEDIUM),
            _f("docker-dockerfile-missing", Category.CONTAINERIZATION, Severity.LOW),
        ]
        score = compute_score(findings)
        assert score.total == 0

    def test_empty_repo_all_dimensions_zero(self):
        """All dimension scores should be 0 for a repo with no signals."""
        findings = [
            _f("doc-readme-missing", Category.DOCUMENTATION, Severity.HIGH),
            _f("dep-manifest-missing", Category.DEPENDENCIES, Severity.HIGH),
            _f("dep-lockfile-missing", Category.DEPENDENCIES, Severity.MEDIUM),
            _f("test-tests-missing", Category.TESTS, Severity.HIGH),
            _f("ci-config-missing", Category.CI, Severity.MEDIUM),
            _f("docker-dockerfile-missing", Category.CONTAINERIZATION, Severity.LOW),
        ]
        score = compute_score(findings)
        for dim in score.dimensions:
            assert dim.score == 0


# ── Full repo (all present) ───────────────────────────────────────────


class TestFullRepo:
    def test_full_repo_scores_100(self):
        """A repo with all signals present should score 100."""
        findings = [
            _f("doc-readme-present", Category.DOCUMENTATION, Severity.INFO),
            _f("dep-manifest-present", Category.DEPENDENCIES, Severity.INFO),
            _f("dep-lockfile-present", Category.DEPENDENCIES, Severity.INFO),
            _f("test-tests-present", Category.TESTS, Severity.INFO),
            _f("ci-config-present", Category.CI, Severity.INFO),
            _f("docker-dockerfile-present", Category.CONTAINERIZATION, Severity.INFO),
            _f("docker-compose-present", Category.CONTAINERIZATION, Severity.INFO),
        ]
        score = compute_score(findings)
        assert score.total == 100

    def test_full_repo_each_dimension_max(self):
        """Each dimension should be at its max when all signals are present."""
        findings = [
            _f("doc-readme-present", Category.DOCUMENTATION, Severity.INFO),
            _f("dep-manifest-present", Category.DEPENDENCIES, Severity.INFO),
            _f("dep-lockfile-present", Category.DEPENDENCIES, Severity.INFO),
            _f("test-tests-present", Category.TESTS, Severity.INFO),
            _f("ci-config-present", Category.CI, Severity.INFO),
            _f("docker-dockerfile-present", Category.CONTAINERIZATION, Severity.INFO),
            _f("docker-compose-present", Category.CONTAINERIZATION, Severity.INFO),
        ]
        score = compute_score(findings)
        for dim in score.dimensions:
            assert dim.score == dim.max_points


# ── Partial repo ──────────────────────────────────────────────────────


class TestPartialRepo:
    def test_manifest_only_partial_dependencies(self):
        """Manifest without lockfile should give partial dependency score."""
        findings = [
            _f("dep-manifest-present", Category.DEPENDENCIES, Severity.INFO),
            _f("dep-lockfile-missing", Category.DEPENDENCIES, Severity.MEDIUM),
        ]
        score = compute_score(findings)
        dep_dim = next(d for d in score.dimensions if d.name == "Dependencies")
        assert dep_dim.score == 18
        assert dep_dim.max_points == 25

    def test_dockerfile_only_partial_containerization(self):
        """Dockerfile without compose should give partial containerization score."""
        findings = [
            _f("docker-dockerfile-present", Category.CONTAINERIZATION, Severity.INFO),
        ]
        score = compute_score(findings)
        docker_dim = next(
            d for d in score.dimensions if d.name == "Containerization"
        )
        assert docker_dim.score == 12

    def test_readme_present_only(self):
        """Just a README should give 20 points (documentation only)."""
        findings = [
            _f("doc-readme-present", Category.DOCUMENTATION, Severity.INFO),
        ]
        score = compute_score(findings)
        assert score.total == 20


# ── Code quality penalty ──────────────────────────────────────────────


class TestCodeQualityPenalty:
    def test_code_quality_reduces_score(self):
        """TODO/FIXME findings should reduce the total score."""
        base_findings = [
            _f("doc-readme-present", Category.DOCUMENTATION, Severity.INFO),
        ]
        base_score = compute_score(base_findings).total

        with_todos = base_findings + [
            _f("code-todo-001", Category.CODE_QUALITY, Severity.LOW),
            _f("code-todo-002", Category.CODE_QUALITY, Severity.LOW),
        ]
        penalised = compute_score(with_todos).total
        assert penalised < base_score
        assert penalised == base_score - 4  # 2 findings × 2 points

    def test_code_quality_penalty_capped(self):
        """Code quality penalty should be capped at 10 points."""
        findings = [
            _f("doc-readme-present", Category.DOCUMENTATION, Severity.INFO),
        ] + [
            _f(f"code-todo-{i:03d}", Category.CODE_QUALITY, Severity.LOW)
            for i in range(20)
        ]
        score = compute_score(findings)
        # 20 points (doc) - 10 (capped penalty) = 10
        assert score.total == 10


# ── Determinism ────────────────────────────────────────────────────────


class TestDeterminism:
    def test_same_input_same_output(self):
        """Same findings should always produce the same score."""
        findings = [
            _f("doc-readme-missing", Category.DOCUMENTATION, Severity.HIGH),
            _f("dep-manifest-present", Category.DEPENDENCIES, Severity.INFO),
        ]
        s1 = compute_score(findings)
        s2 = compute_score(findings)
        assert s1.total == s2.total
        assert len(s1.dimensions) == len(s2.dimensions)

    def test_score_clamped_to_0_100(self):
        """Score should never go below 0 or above 100."""
        # All missing + many code quality findings → should be 0
        findings = [
            _f("doc-readme-missing", Category.DOCUMENTATION, Severity.HIGH),
        ] + [
            _f(f"code-todo-{i:03d}", Category.CODE_QUALITY, Severity.LOW)
            for i in range(50)
        ]
        score = compute_score(findings)
        assert score.total >= 0

    def test_explanations_not_empty(self):
        """Each dimension should have a non-empty explanation."""
        score = compute_score([])
        for dim in score.dimensions:
            assert dim.explanation
            assert len(dim.explanation) > 10
