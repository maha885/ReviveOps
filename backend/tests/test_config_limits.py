"""Tests for env-driven public scan limits in Settings."""

import pytest

from app.config import Settings

CASES = [
    ("REVIVEOPS_MAX_DOWNLOAD_MB", "max_download_mb", 25),
    ("REVIVEOPS_MAX_EXTRACT_MB", "max_extract_mb", 100),
    ("REVIVEOPS_MAX_EXTRACT_ENTRIES", "max_extract_entries", 10000),
    ("REVIVEOPS_SCAN_RATE_PER_MINUTE", "scan_rate_per_minute", 10),
    ("REVIVEOPS_DOWNLOAD_TIMEOUT_SECONDS", "download_timeout_seconds", 20),
    ("REVIVEOPS_MAX_CONCURRENT_SCANS", "max_concurrent_scans", 2),
]


@pytest.mark.parametrize("env,attr,default", CASES)
def test_defaults(monkeypatch, env, attr, default):
    monkeypatch.delenv(env, raising=False)
    assert getattr(Settings(), attr) == default


@pytest.mark.parametrize("env,attr,default", CASES)
def test_override(monkeypatch, env, attr, default):
    monkeypatch.setenv(env, "7")
    assert getattr(Settings(), attr) == 7


@pytest.mark.parametrize("env,attr,default", CASES)
@pytest.mark.parametrize("bad", ["", "abc", "0", "-5", "1.5", "  "])
def test_invalid_falls_back(monkeypatch, env, attr, default, bad):
    monkeypatch.setenv(env, bad)
    assert getattr(Settings(), attr) == default


def test_byte_helpers(monkeypatch):
    monkeypatch.setenv("REVIVEOPS_MAX_DOWNLOAD_MB", "2")
    monkeypatch.setenv("REVIVEOPS_MAX_EXTRACT_MB", "3")
    s = Settings()
    assert s.max_download_bytes == 2 * 1024 * 1024
    assert s.max_extract_bytes == 3 * 1024 * 1024
