"""SQLite persistence layer for scan history and checklist state.

Keeps a small, typed API behind a ``Database`` class so the rest of the
application doesn't touch SQL directly.  Uses ``sqlite3`` from the standard
library — no extra dependencies.

Schema::

    scans         — one row per scan (findings, score, tasks stored as JSON)
    task_status   — completion state per (scan_id, task_id)
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS scans (
    scan_id     TEXT PRIMARY KEY,
    repo_name   TEXT NOT NULL,
    scanned_at  TEXT NOT NULL,
    file_count  INTEGER NOT NULL,
    truncated   INTEGER NOT NULL DEFAULT 0,
    errors      TEXT NOT NULL DEFAULT '[]',
    label       TEXT,
    findings    TEXT NOT NULL,
    score       TEXT NOT NULL,
    tasks       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task_status (
    scan_id     TEXT NOT NULL,
    task_id     TEXT NOT NULL,
    completed   INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (scan_id, task_id),
    FOREIGN KEY (scan_id) REFERENCES scans(scan_id)
);
"""


class Database:
    """Thin repository layer over SQLite for scan + task persistence."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        # Ensure parent directory exists.
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)

    # ── Scans ──────────────────────────────────────────────────────────

    def save_scan(
        self,
        scan_id: str,
        repo_name: str,
        scanned_at: str,
        file_count: int,
        truncated: bool,
        errors: list[str],
        label: str | None,
        findings_json: str,
        score_json: str,
        tasks_json: str,
    ) -> None:
        """Insert or replace a scan record."""
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO scans
                   (scan_id, repo_name, scanned_at, file_count, truncated,
                    errors, label, findings, score, tasks)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    scan_id,
                    repo_name,
                    scanned_at,
                    file_count,
                    int(truncated),
                    json.dumps(errors),
                    label,
                    findings_json,
                    score_json,
                    tasks_json,
                ),
            )

    def get_scan(self, scan_id: str) -> dict | None:
        """Return a raw scan row as a dict, or None if not found."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM scans WHERE scan_id = ?", (scan_id,)
            ).fetchone()
        return dict(row) if row else None

    # ── Task status ────────────────────────────────────────────────────

    def update_task_status(
        self, scan_id: str, task_id: str, completed: bool
    ) -> None:
        """Insert or update the completion state of a single task."""
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO task_status
                   (scan_id, task_id, completed)
                   VALUES (?, ?, ?)""",
                (scan_id, task_id, int(completed)),
            )

    def get_task_statuses(self, scan_id: str) -> dict[str, bool]:
        """Return a {task_id: completed} map for all tasks in a scan."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT task_id, completed FROM task_status WHERE scan_id = ?",
                (scan_id,),
            ).fetchall()
        return {row["task_id"]: bool(row["completed"]) for row in rows}
