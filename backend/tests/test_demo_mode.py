"""Tests for hosted demo mode (flag, 403 guard, cleanup, SPA fallback)."""

import os
import time

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, settings
from app.main import app
from app.services.cleanup import cleanup_old_revived

client = TestClient(app)

DENIED = (
    "Hosted demo scans the bundled demo repository only. "
    "Run ReviveOps locally to scan your own folders."
)


@pytest.fixture
def demo_on(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", True)


@pytest.fixture
def dist(tmp_path, monkeypatch):
    d = tmp_path / "dist"
    (d / "assets").mkdir(parents=True)
    (d / "index.html").write_text("<html>INDEX</html>")
    (d / "assets" / "app.js").write_text("console.log('asset')")
    (tmp_path / "secret.txt").write_text("SECRET")
    monkeypatch.setattr(settings, "frontend_dist_path", d)
    return d


# -- config ------------------------------------------------------------


@pytest.mark.parametrize("value", ["true", "TRUE", "True", "1", "yes", "YES"])
def test_env_truthy(monkeypatch, value):
    monkeypatch.setenv("REVIVEOPS_DEMO_MODE", value)
    assert Settings().demo_mode is True


@pytest.mark.parametrize("value", ["false", "0", "no", "", "on", "2", "garbage"])
def test_env_falsy(monkeypatch, value):
    monkeypatch.setenv("REVIVEOPS_DEMO_MODE", value)
    assert Settings().demo_mode is False


def test_env_unset_defaults_false(monkeypatch):
    monkeypatch.delenv("REVIVEOPS_DEMO_MODE", raising=False)
    s = Settings()
    assert s.demo_mode is False
    assert s.revived_max_age_minutes == 60
    assert s.frontend_dist_path.parts[-2:] == ("frontend", "dist")


def test_config_endpoint_both_modes(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", False)
    assert client.get("/api/config").json() == {"demo_mode": False}
    monkeypatch.setattr(settings, "demo_mode", True)
    assert client.get("/api/config").json() == {"demo_mode": True}


# -- scan restriction --------------------------------------------------


def test_demo_mode_rejects_other_paths_without_persisting(demo_on, tmp_path):
    import app.main as m

    saved = []
    orig = m.db.save_scan
    m.db.save_scan = lambda **kw: saved.append(kw)
    try:
        r = client.post("/api/scans", json={"path": str(tmp_path)})
        r2 = client.post("/api/scans", json={"path": "does/not/exist"})
    finally:
        m.db.save_scan = orig
    assert r.status_code == 403 and r.json()["detail"] == DENIED
    assert r2.status_code == 403
    assert saved == []


def test_demo_mode_allows_demo(demo_on):
    r = client.post("/api/scans", json={"path": "demo"})
    assert r.status_code == 200
    assert r.json()["repo_name"]


def test_flag_off_unchanged(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "demo_mode", False)
    (tmp_path / "a.py").write_text("print(1)\n")
    assert client.post("/api/scans", json={"path": str(tmp_path)}).status_code == 200
    r = client.post("/api/scans", json={"path": str(tmp_path / "nope")})
    assert r.status_code == 404


# -- revived cleanup ---------------------------------------------------


def _age(path, minutes):
    t = time.time() - minutes * 60
    os.utime(path, (t, t))


def test_cleanup_removes_old_keeps_fresh_and_keep(tmp_path):
    root = tmp_path / "revived"
    old, fresh, keep = root / "old", root / "fresh", root / "keep"
    for d in (old, fresh, keep):
        (d / "sub").mkdir(parents=True)
        (d / "sub" / "f.txt").write_text("x")
    stray = root / "stray.txt"
    stray.write_text("x")
    _age(old, 120)
    _age(keep, 120)
    _age(stray, 120)
    removed = cleanup_old_revived(root, 60, keep=keep)
    assert removed == ["old"]
    assert not old.exists()
    assert fresh.exists() and keep.exists() and stray.exists() and root.exists()


def test_cleanup_ignores_symlinks_and_outside(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_text("x")
    _age(outside, 500)
    root = tmp_path / "revived"
    root.mkdir()
    link = root / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    _age(root, 500)
    assert cleanup_old_revived(root, 60) == []
    assert (outside / "keep.txt").exists() and link.is_symlink()


def test_cleanup_missing_dir_does_not_raise(tmp_path):
    assert cleanup_old_revived(tmp_path / "missing", 60) == []


def test_revive_cleans_old_copies(monkeypatch):
    import app.main as m

    scan_id = client.post("/api/scans", json={"path": "demo"}).json()["scan_id"]
    old = m.REVIVED_DIR / "oldscan"
    old.mkdir()
    _age(old, 600)
    r = client.post(f"/api/scans/{scan_id}/revive")
    assert r.status_code == 200
    assert not old.exists()
    assert (m.REVIVED_DIR / scan_id).exists()


# -- SPA fallback ------------------------------------------------------


def test_spa_serves_index_assets_and_fallback(demo_on, dist):
    assert "INDEX" in client.get("/").text
    assert "INDEX" in client.get("/some/client/route").text
    r = client.get("/assets/app.js")
    assert r.status_code == 200 and "asset" in r.text


@pytest.mark.parametrize(
    "url", ["/..%2fsecret.txt", "/%2e%2e/secret.txt", "/assets/..%2f..%2fsecret.txt", "/../secret.txt"]
)
def test_spa_blocks_traversal(demo_on, dist, url):
    r = client.get(url)
    assert "SECRET" not in r.text


def test_spa_not_applied_when_flag_off(dist, monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", False)
    assert client.get("/").json()["name"] == settings.app_name
    assert client.get("/some/route").status_code == 404
    assert client.get("/assets/app.js").status_code == 404


def test_spa_not_applied_without_index(demo_on, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "frontend_dist_path", tmp_path / "empty")
    assert client.get("/").json()["name"] == settings.app_name
    assert client.get("/x").status_code == 404


def test_route_priority_in_demo_mode(demo_on, dist):
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/api/config").json() == {"demo_mode": True}
    assert "openapi" in client.get("/openapi.json").json()
    assert "INDEX" not in client.get("/docs").text
    r = client.get("/api/scans/missing")
    assert r.status_code == 404 and r.json()["detail"].startswith("Scan not found")
    for url in ("/api/unknown", "/api/", "/api"):
        r = client.get(url)
        assert r.status_code == 404
        assert r.headers["content-type"].startswith("application/json")
        assert "INDEX" not in r.text


# -- Method handling parity with the pre-catch-all app --------------------

PREFLIGHT = {
    "Origin": "http://localhost:5173",
    "Access-Control-Request-Method": "POST",
    "Access-Control-Request-Headers": "content-type",
}


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_flag_off_unknown_path_non_get_is_404(method):
    r = getattr(client, method)("/definitely/not/here")
    assert r.status_code == 404
    assert r.json() == {"detail": "Not Found"}


def test_flag_off_wrong_method_on_real_route_is_405():
    # Original app (git HEAD): only POST /api/scans exists, so GET -> 405.
    r = client.get("/api/scans")
    assert r.status_code == 405
    assert r.json() == {"detail": "Method Not Allowed"}
    assert r.headers["allow"] == "POST"


def test_flag_off_unknown_get_is_404():
    assert client.get("/nope").status_code == 404


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_flag_on_unknown_non_api_non_get_is_404(demo_on, dist, method):
    r = getattr(client, method)("/some/page")
    assert r.status_code == 404
    assert r.json() == {"detail": "Not Found"}


def test_flag_on_wrong_method_on_real_route_still_405(demo_on, dist):
    assert client.get("/api/scans").status_code == 405


def test_cors_preflight_unchanged_on_real_and_unknown_paths(demo_on, dist):
    for path in ("/api/scans", "/unknown"):
        r = client.options(path, headers=PREFLIGHT)
        assert r.status_code == 200
        assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
        assert "POST" in r.headers["access-control-allow-methods"]


def test_cors_preflight_flag_off():
    r = client.options("/api/scans", headers=PREFLIGHT)
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
