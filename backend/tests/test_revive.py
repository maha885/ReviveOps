"""Tests for the revival planner and the revive API.

Run with:
    pytest tests/test_revive.py
"""

import re
from pathlib import Path

from fastapi.testclient import TestClient
from hypothesis import given, settings, strategies as st

from app.main import DEMO_REPO_PATH, app
from app.scanner import scan_repository
from app.scanner.models import Category, Finding, Severity
from app.services.revive import apply_plan_to_copy, build_plan, detect_project_type

client = TestClient(app)
MARKER = re.compile(r"\b(TODO|FIXME|HACK|XXX|BUG)\b", re.IGNORECASE)


def _missing(*ids: str) -> list[Finding]:
    return [
        Finding(i, i, Category.DOCUMENTATION, Severity.HIGH, "e", "r", None)
        for i in ids
    ]


ALL_MISSING = _missing(
    "doc-readme-missing", "test-tests-missing",
    "ci-config-missing", "docker-dockerfile-missing", "dep-lockfile-missing",
)


# ── Planner ────────────────────────────────────────────────────────────


def test_detect_project_type():
    assert detect_project_type(["package.json", "src/a.js"]) == "node"
    assert detect_project_type(["pyproject.toml"]) == "python"
    assert detect_project_type(["a/b.py"]) == "python"
    assert detect_project_type(["notes.txt"]) == "generic"


def test_plan_proposes_all_missing_files_for_python():
    plan = build_plan("demo", ["pyproject.toml", "src/main.py"], ALL_MISSING)
    paths = {f.path for f in plan.files}
    assert paths == {
        "README.md", "tests/test_smoke.py",
        ".github/workflows/ci.yml", "Dockerfile",
    }
    assert any("lockfile" in step for step in plan.manual_steps)


def test_plan_never_overwrites_existing_files():
    plan = build_plan("demo", ["pyproject.toml", "README.md"], ALL_MISSING)
    assert "README.md" not in {f.path for f in plan.files}


def test_generated_files_add_no_code_markers():
    for files in (["pyproject.toml", "a.py"], ["package.json"]):
        plan = build_plan("demo", files, ALL_MISSING)
        for f in plan.files:
            assert not MARKER.search(f.content), f.path


def test_generic_project_gets_readme_and_manual_note_only():
    plan = build_plan("demo", ["notes.txt"], ALL_MISSING)
    assert {f.path for f in plan.files} == {"README.md"}


@settings(max_examples=60, deadline=None)
@given(
    st.lists(
        st.sampled_from([
            "README.md", "package.json", "pyproject.toml", "src/app.py",
            "tests/test_a.py", "Dockerfile", ".github/workflows/ci.yml", "notes.txt",
        ]),
        unique=True,
        max_size=8,
    )
)
def test_plan_properties(rel_paths):
    """Deterministic, never overwrites, never proposes markers."""
    first = build_plan("demo", rel_paths, ALL_MISSING)
    second = build_plan("demo", list(reversed(rel_paths)), ALL_MISSING)
    assert [(f.path, f.content) for f in first.files] == [
        (f.path, f.content) for f in second.files
    ]
    for f in first.files:
        assert f.path not in rel_paths
        assert not MARKER.search(f.content)


def test_apply_plan_copies_and_never_touches_source(tmp_path):
    src = tmp_path / "src_repo"
    src.mkdir()
    (src / "a.py").write_text("x = 1\n")
    plan = build_plan("src_repo", ["a.py"], ALL_MISSING)
    dest = tmp_path / "out"
    written = apply_plan_to_copy([(src / "a.py", "a.py")], plan, dest)
    assert (dest / "a.py").exists()
    assert "README.md" in written
    assert not (src / "README.md").exists()


def test_apply_plan_blocks_path_traversal(tmp_path):
    from app.services.revive import ProposedFile, RevivalPlan

    plan = RevivalPlan("python", [ProposedFile("../escape.txt", "x", "f", "r")])
    dest = tmp_path / "out"
    written = apply_plan_to_copy([], plan, dest)
    assert written == []
    assert not (tmp_path / "escape.txt").exists()


# ── API ────────────────────────────────────────────────────────────────


def _demo_scan_id() -> str:
    resp = client.post("/api/scans", json={"path": "demo"})
    assert resp.status_code == 200
    return resp.json()["scan_id"]


def test_revival_plan_endpoint_previews_without_changes():
    scan_id = _demo_scan_id()
    resp = client.get(f"/api/scans/{scan_id}/revival-plan")
    assert resp.status_code == 200
    body = resp.json()
    assert body["project_type"] == "python"
    assert "README.md" in {f["path"] for f in body["files"]}
    assert not (DEMO_REPO_PATH / "README.md").exists()


def test_revive_raises_score_and_leaves_original_untouched():
    scan_id = _demo_scan_id()
    resp = client.post(f"/api/scans/{scan_id}/revive")
    assert resp.status_code == 200
    body = resp.json()
    assert body["score_after"] > body["score_before"]
    assert "README.md" in body["files_written"]
    assert body["revived_scan"]["scan_id"] != scan_id
    # Original demo repo is unchanged.
    assert not (DEMO_REPO_PATH / "README.md").exists()
    assert not (DEMO_REPO_PATH / "Dockerfile").exists()
    # Rescanning the original still shows the old problems.
    original = scan_repository(DEMO_REPO_PATH)
    assert any(f.finding_id == "doc-readme-missing" for f in original.findings)


def test_revive_unknown_scan_is_404():
    assert client.post("/api/scans/nope/revive").status_code == 404
    assert client.get("/api/scans/nope/revival-plan").status_code == 404


def test_revive_when_source_deleted_is_409(tmp_path):
    repo = tmp_path / "temp_repo"
    repo.mkdir()
    (repo / "a.py").write_text("x = 1\n")
    scan_id = client.post("/api/scans", json={"path": str(repo)}).json()["scan_id"]
    (repo / "a.py").unlink()
    repo.rmdir()
    assert client.post(f"/api/scans/{scan_id}/revive").status_code == 409
