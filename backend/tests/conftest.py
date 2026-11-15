"""Shared test fixtures.

Replaces the production SQLite database with a temp one for every test
so tests never pollute or depend on the real database file.
"""

import pytest

from app.db import Database


@pytest.fixture(autouse=True)
def test_db(tmp_path_factory, monkeypatch):
    """Replace app.main.db with a fresh temp database per test."""
    db = Database(tmp_path_factory.mktemp("db") / "test_reviveops.db")
    monkeypatch.setattr("app.main.db", db)
    monkeypatch.setattr("app.main.REVIVED_DIR", tmp_path_factory.mktemp("revived"))
    yield
