"""API tests for POST /api/scans with ``github_url`` (fake downloader, no network)."""

import io
import os
import time
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.main as m
from app.config import settings
from app.main import app
from app.services.download import (
    DownloadError,
    DownloadTimeout,
    DownloadTooLarge,
    RepoNotFound,
)
from app.services.limits import extraction_limiter, scan_rate_limiter

client = TestClient(app)
URL = "https://github.com/octo/hello"


def make_zip_bytes(entries=None) -> bytes:
    if entries is None:
        entries = {
            "hello-abc123/README.md": "# Hello\n",
            "hello-abc123/requirements.txt": "requests\n",
            "hello-abc123/main.py": "print('hi')  # TODO: finish\n",
        }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


class FakeDownloader:
    def __init__(self, payload=None, exc=None):
        self.payload = make_zip_bytes() if payload is None else payload
        self.exc = exc
        self.calls = []
        self.dest_files = []

    def __call__(self, url, dest_file, max_bytes, timeout):
        self.calls.append(url)
        self.dest_files.append(Path(dest_file))
        if self.exc is not None:
            raise self.exc
        Path(dest_file).write_bytes(self.payload)
        return Path(dest_file)


@pytest.fixture
def fake(monkeypatch):
    f = FakeDownloader()
    monkeypatch.setattr(m, "download_archive", f)
    return f


def post(url=URL, **extra):
    return client.post("/api/scans", json={"github_url": url, **extra})


# -- happy path ---------------------------------------------------------


def test_happy_path_and_revival(fake):
    r = post()
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["label"] == "octo/hello"
    assert body["file_count"] > 0
    assert fake.calls == ["https://codeload.github.com/octo/hello/zip/HEAD"]
    assert not fake.dest_files[0].exists()  # temp download removed

    row = m.db.get_scan(body["scan_id"])
    root = Path(row["root_path"])
    assert root.is_dir() and m.SOURCES_DIR.resolve() in root.resolve().parents
    assert (m.SOURCES_DIR / body["scan_id"]).is_dir()  # folder id == scan id

    plan = client.get(f"/api/scans/{body['scan_id']}/revival-plan")
    assert plan.status_code == 200 and plan.json()["files"]
    rev = client.post(f"/api/scans/{body['scan_id']}/revive")
    assert rev.status_code == 200
    assert rev.json()["files_written"]


def test_custom_label_kept(fake):
    assert post(label="mine").json()["label"] == "mine"


def test_local_mode_and_demo_mode_allow_github_url(fake, monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", False)
    assert post().status_code == 200
    monkeypatch.setattr(settings, "demo_mode", True)
    assert post().status_code == 200


# -- request shape -------------------------------------------------------


def test_both_and_neither_and_empty_are_422(fake, tmp_path):
    assert client.post(
        "/api/scans", json={"path": str(tmp_path), "github_url": URL}
    ).status_code == 422
    assert client.post("/api/scans", json={}).status_code == 422
    assert client.post("/api/scans", json={"path": ""}).status_code == 422
    assert client.post("/api/scans", json={"github_url": ""}).status_code == 422
    assert fake.calls == []


def test_path_scan_unchanged(tmp_path):
    (tmp_path / "a.py").write_text("print(1)\n")
    r = client.post("/api/scans", json={"path": str(tmp_path)})
    assert r.status_code == 200 and r.json()["label"] is None


# -- malformed URLs -------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "https://gitlab.com/a/b",
        "http://github.com/a/b",
        "https://user:pw@github.com/a/b",
        "https://github.com:443/a/b",
        "https://github.com/a/b?x=1",
        "https://github.com/a/..",
        "https://github.com/../b",
        "not a url",
    ],
)
def test_malformed_urls_422_no_download(fake, url):
    r = post(url)
    assert r.status_code == 422
    assert fake.calls == []
    assert list(m.SOURCES_DIR.iterdir()) == []


# -- error mapping ----------------------------------------------------------


@pytest.mark.parametrize(
    "exc,status",
    [
        (RepoNotFound("Repository not found or not public."), 404),
        (DownloadTooLarge("x"), 413),
        (DownloadTimeout("x"), 504),
        (DownloadError("x"), 502),
    ],
)
def test_download_errors_mapped(monkeypatch, exc, status):
    monkeypatch.setattr(m, "download_archive", FakeDownloader(exc=exc))
    r = post()
    assert r.status_code == status
    assert list(m.SOURCES_DIR.iterdir()) == []
    assert str(m.SOURCES_DIR) not in r.text


def test_not_found_message(monkeypatch):
    monkeypatch.setattr(m, "download_archive", FakeDownloader(exc=RepoNotFound("x")))
    assert post().json()["detail"] == "Repository not found or not public."


def test_archive_too_large_413_leaves_nothing(fake, monkeypatch):
    monkeypatch.setattr(settings, "max_extract_mb", 1)
    big = make_zip_bytes({"r-1/big.bin": "a" * (2 * 1024 * 1024)})
    fake.payload = big
    r = post()
    assert r.status_code == 413
    assert list(m.SOURCES_DIR.iterdir()) == []
    assert not fake.dest_files[0].exists()


@pytest.mark.parametrize("payload", [b"this is not a zip", b""])
def test_non_zip_422_leaves_nothing(fake, payload):
    fake.payload = payload
    r = post()
    assert r.status_code == 422
    assert list(m.SOURCES_DIR.iterdir()) == []
    assert not fake.dest_files[0].exists()
    tmp = str(fake.dest_files[0].parent)
    assert tmp not in r.text and str(m.SOURCES_DIR) not in r.text


def test_unexpected_error_cleans_up_and_is_500(fake, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("secret internal")

    monkeypatch.setattr(m, "_scan_and_persist", boom)
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.post("/api/scans", json={"github_url": URL})
    assert r.status_code == 500
    assert "secret internal" not in r.text
    assert list(m.SOURCES_DIR.iterdir()) == []
    assert not fake.dest_files[0].exists()
    assert extraction_limiter.active == 0


# -- limits --------------------------------------------------------------------


def test_rate_limit_429_with_retry_after(fake, monkeypatch):
    monkeypatch.setattr(settings, "scan_rate_per_minute", 2)
    assert post().status_code == 200
    assert post().status_code == 200
    r = post()
    assert r.status_code == 429
    assert int(r.headers["retry-after"]) >= 1


def test_rate_limit_does_not_apply_to_path_scans(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "scan_rate_per_minute", 1)
    (tmp_path / "a.py").write_text("x = 1\n")
    for _ in range(3):
        assert client.post("/api/scans", json={"path": str(tmp_path)}).status_code == 200


def test_concurrency_limit_429(fake, monkeypatch):
    monkeypatch.setattr(settings, "max_concurrent_scans", 1)
    assert extraction_limiter.try_acquire()
    try:
        r = post()
        assert r.status_code == 429
        assert fake.calls == []
    finally:
        extraction_limiter.release()
    assert post().status_code == 200


# -- demo mode ------------------------------------------------------------------


def test_demo_mode_non_demo_path_403_before_filesystem(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", True)

    def forbidden(*a, **k):
        raise AssertionError("filesystem touched")

    monkeypatch.setattr(m.Path, "resolve", forbidden)
    monkeypatch.setattr(m.Path, "exists", forbidden)
    r = client.post("/api/scans", json={"path": "/etc"})
    assert r.status_code == 403


# -- cleanup of sources ------------------------------------------------------------


def _age(path, minutes):
    t = time.time() - minutes * 60
    os.utime(path, (t, t))


def test_old_sources_pruned_fresh_kept_and_revive_409(fake):
    first = post().json()["scan_id"]
    old = m.SOURCES_DIR / first
    _age(old, 10_000)
    stale = m.SOURCES_DIR / "stale"
    stale.mkdir()
    _age(stale, 10_000)
    fresh = m.SOURCES_DIR / "fresh"
    fresh.mkdir()

    second = post().json()["scan_id"]
    assert not old.exists() and not stale.exists()
    assert fresh.exists() and (m.SOURCES_DIR / second).exists()

    r = client.post(f"/api/scans/{first}/revive")
    assert r.status_code == 409
    assert "no longer available" in r.json()["detail"]
    assert client.get(f"/api/scans/{first}/revival-plan").status_code == 409
