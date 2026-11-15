"""Tests for the POST /api/scans endpoint.

Run with:
    pytest tests/test_scan_api.py
"""

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ── POST /api/scans with demo path ────────────────────────────────────


def test_scan_demo_returns_200():
    """POST /api/scans with path='demo' should return HTTP 200."""
    response = client.post("/api/scans", json={"path": "demo"})
    assert response.status_code == 200


def test_scan_demo_response_shape():
    """Demo scan response should have all expected top-level fields."""
    data = client.post("/api/scans", json={"path": "demo"}).json()
    assert "repo_name" in data
    assert "scanned_at" in data
    assert "findings" in data
    assert "file_count" in data
    assert "truncated" in data
    assert "errors" in data
    assert isinstance(data["findings"], list)


def test_scan_demo_repo_name():
    """Demo scan should return 'demo_repo' as repo_name."""
    data = client.post("/api/scans", json={"path": "demo"}).json()
    assert data["repo_name"] == "demo_repo"


def test_scan_demo_has_findings():
    """Demo scan should produce at least one finding."""
    data = client.post("/api/scans", json={"path": "demo"}).json()
    assert len(data["findings"]) > 0


def test_scan_demo_finding_fields():
    """Each finding should have all required fields."""
    data = client.post("/api/scans", json={"path": "demo"}).json()
    for finding in data["findings"]:
        assert "finding_id" in finding
        assert "title" in finding
        assert "category" in finding
        assert "severity" in finding
        assert "evidence" in finding
        assert "recommendation" in finding
        assert "source_path" in finding  # may be null


def test_scan_demo_has_expected_finding_ids():
    """Demo scan should include both present and missing signal findings."""
    data = client.post("/api/scans", json={"path": "demo"}).json()
    ids = {f["finding_id"] for f in data["findings"]}
    assert "dep-manifest-present" in ids
    assert "doc-readme-missing" in ids
    assert "dep-lockfile-missing" in ids
    assert "test-tests-missing" in ids


def test_scan_demo_with_label():
    """Scan request with a label should include it in the response."""
    data = client.post(
        "/api/scans", json={"path": "demo", "label": "my-label"}
    ).json()
    assert data["label"] == "my-label"


def test_scan_demo_file_count_positive():
    """Demo scan should report a positive file count."""
    data = client.post("/api/scans", json={"path": "demo"}).json()
    assert data["file_count"] > 0


# ── POST /api/scans error cases ───────────────────────────────────────


def test_scan_nonexistent_path_returns_404():
    """Scanning a non-existent path should return HTTP 404."""
    response = client.post(
        "/api/scans", json={"path": "/nonexistent/path/12345"}
    )
    assert response.status_code == 404


def test_scan_file_path_returns_400(tmp_path):
    """Scanning a file (not directory) should return HTTP 400."""
    file_path = tmp_path / "not_a_dir.txt"
    file_path.write_text("file content")
    response = client.post("/api/scans", json={"path": str(file_path)})
    assert response.status_code == 400


# ── POST /api/scans with real directory ───────────────────────────────


def test_scan_real_directory(tmp_path):
    """Scanning a real directory with a README should return 200."""
    (tmp_path / "README.md").write_text("# Test Project")
    response = client.post("/api/scans", json={"path": str(tmp_path)})
    assert response.status_code == 200
    data = response.json()
    assert len(data["findings"]) > 0


def test_scan_empty_directory(tmp_path):
    """Scanning an empty directory should return 200 with findings."""
    response = client.post("/api/scans", json={"path": str(tmp_path)})
    assert response.status_code == 200
    data = response.json()
    # Empty dir should have all "missing" findings.
    ids = {f["finding_id"] for f in data["findings"]}
    assert "doc-readme-missing" in ids
    assert "dep-manifest-missing" in ids
    assert data["file_count"] == 0
