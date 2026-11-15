"""Tests for the SQLite persistence layer.

Run with:
    pytest tests/test_db.py
"""

import json

from app.db import Database


def _db(tmp_path):
    """Create a fresh temp database."""
    return Database(tmp_path / "test.db")


class TestSaveAndGetScan:
    def test_save_and_retrieve_scan(self, tmp_path):
        """A saved scan should be retrievable by ID."""
        db = _db(tmp_path)
        db.save_scan(
            scan_id="test-123",
            repo_name="my-repo",
            scanned_at="2024-01-01T00:00:00Z",
            file_count=42,
            truncated=False,
            errors=[],
            label=None,
            findings_json='[{"finding_id": "f1"}]',
            score_json='{"total": 50, "dimensions": [], "label": "heuristic"}',
            tasks_json='[{"task_id": "t1", "completed": false}]',
        )
        scan = db.get_scan("test-123")
        assert scan is not None
        assert scan["repo_name"] == "my-repo"
        assert scan["file_count"] == 42
        assert scan["truncated"] == 0  # stored as int

    def test_get_nonexistent_scan_returns_none(self, tmp_path):
        """Getting a non-existent scan should return None."""
        db = _db(tmp_path)
        assert db.get_scan("does-not-exist") is None

    def test_save_replaces_existing_scan(self, tmp_path):
        """Saving with the same scan_id should replace the existing record."""
        db = _db(tmp_path)
        db.save_scan(
            scan_id="dup-1",
            repo_name="first",
            scanned_at="2024-01-01",
            file_count=10,
            truncated=False,
            errors=[],
            label=None,
            findings_json="[]",
            score_json='{"total": 0, "dimensions": [], "label": "heuristic"}',
            tasks_json="[]",
        )
        db.save_scan(
            scan_id="dup-1",
            repo_name="second",
            scanned_at="2024-01-02",
            file_count=20,
            truncated=True,
            errors=["error1"],
            label="updated",
            findings_json="[]",
            score_json='{"total": 100, "dimensions": [], "label": "heuristic"}',
            tasks_json="[]",
        )
        scan = db.get_scan("dup-1")
        assert scan["repo_name"] == "second"
        assert scan["file_count"] == 20
        assert scan["label"] == "updated"


class TestTaskStatus:
    def test_update_and_get_task_status(self, tmp_path):
        """Task status should persist and be retrievable."""
        db = _db(tmp_path)
        db.save_scan(
            scan_id="s1",
            repo_name="repo",
            scanned_at="2024-01-01",
            file_count=5,
            truncated=False,
            errors=[],
            label=None,
            findings_json="[]",
            score_json='{"total": 0, "dimensions": [], "label": "heuristic"}',
            tasks_json='[{"task_id": "t1"}, {"task_id": "t2"}]',
        )
        db.update_task_status("s1", "t1", True)
        statuses = db.get_task_statuses("s1")
        assert statuses["t1"] is True
        assert "t2" not in statuses  # not yet set

    def test_update_task_status_toggle(self, tmp_path):
        """Task status should be toggleable."""
        db = _db(tmp_path)
        db.save_scan(
            scan_id="s1",
            repo_name="repo",
            scanned_at="2024-01-01",
            file_count=5,
            truncated=False,
            errors=[],
            label=None,
            findings_json="[]",
            score_json='{"total": 0, "dimensions": [], "label": "heuristic"}',
            tasks_json='[{"task_id": "t1"}]',
        )
        db.update_task_status("s1", "t1", True)
        assert db.get_task_statuses("s1")["t1"] is True

        db.update_task_status("s1", "t1", False)
        assert db.get_task_statuses("s1")["t1"] is False

    def test_get_statuses_empty_for_new_scan(self, tmp_path):
        """A scan with no task updates should return an empty status map."""
        db = _db(tmp_path)
        db.save_scan(
            scan_id="s1",
            repo_name="repo",
            scanned_at="2024-01-01",
            file_count=5,
            truncated=False,
            errors=[],
            label=None,
            findings_json="[]",
            score_json='{"total": 0, "dimensions": [], "label": "heuristic"}',
            tasks_json="[]",
        )
        statuses = db.get_task_statuses("s1")
        assert statuses == {}
