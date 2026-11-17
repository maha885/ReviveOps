import socket
import urllib.error
import urllib.request

import pytest

from app.services import download as dl
from app.services.download import (
    DownloadError,
    DownloadTimeout,
    DownloadTooLarge,
    RepoNotFound,
    download_archive,
)

URL = "https://codeload.github.com/o/r/zip/HEAD"


class FakeResp:
    def __init__(self, chunks=(), headers=None, exc_at=None, on_read=None):
        self.chunks = list(chunks)
        self.headers = headers or {}
        self.exc_at = exc_at
        self.on_read = on_read
        self.closed = False

    def read(self, n=-1):
        if self.on_read:
            self.on_read()
        if self.exc_at is not None and not self.chunks:
            raise self.exc_at
        return self.chunks.pop(0) if self.chunks else b""

    def close(self):
        self.closed = True


class FakeOpener:
    def __init__(self, resp=None, exc=None):
        self.resp, self.exc, self.requests = resp, exc, []

    def open(self, req, timeout=None):
        self.requests.append((req, timeout))
        if self.exc:
            raise self.exc
        return self.resp


def http_error(code):
    return urllib.error.HTTPError(URL, code, "x", {}, None)


@pytest.mark.parametrize("code", [403, 404, 410])
def test_not_found(tmp_path, code):
    f = tmp_path / "z.zip"
    with pytest.raises(RepoNotFound, match="Repository not found or not public."):
        download_archive(URL, f, 100, 5, opener=FakeOpener(exc=http_error(code)))
    assert not f.exists()


def test_other_http_error(tmp_path):
    with pytest.raises(DownloadError) as ei:
        download_archive(URL, tmp_path / "z", 100, 5, opener=FakeOpener(exc=http_error(500)))
    assert not isinstance(ei.value, RepoNotFound)


def test_url_error_generic(tmp_path):
    with pytest.raises(DownloadError):
        download_archive(
            URL, tmp_path / "z", 100, 5,
            opener=FakeOpener(exc=urllib.error.URLError("dns")),
        )


def test_oversize_content_length(tmp_path):
    f = tmp_path / "z"
    resp = FakeResp([b"x"], {"Content-Length": "1000"})
    with pytest.raises(DownloadTooLarge):
        download_archive(URL, f, 100, 5, opener=FakeOpener(resp))
    assert not f.exists() and resp.closed


def test_oversize_streamed_with_lying_length(tmp_path):
    f = tmp_path / "z"
    resp = FakeResp([b"x" * 60, b"x" * 60], {"Content-Length": "10"})
    with pytest.raises(DownloadTooLarge):
        download_archive(URL, f, 100, 5, opener=FakeOpener(resp))
    assert not f.exists()


@pytest.mark.parametrize(
    "exc",
    [socket.timeout("t"), TimeoutError("t"), urllib.error.URLError(socket.timeout("t"))],
)
def test_timeout_on_open(tmp_path, exc):
    with pytest.raises(DownloadTimeout):
        download_archive(URL, tmp_path / "z", 100, 5, opener=FakeOpener(exc=exc))


def test_timeout_during_read_removes_partial(tmp_path):
    f = tmp_path / "z"
    resp = FakeResp([b"abc"], exc_at=socket.timeout("slow"))
    with pytest.raises(DownloadTimeout):
        download_archive(URL, f, 100, 5, opener=FakeOpener(resp))
    assert not f.exists()


def test_total_deadline_across_slow_chunks(tmp_path, monkeypatch):
    now = [0.0]
    monkeypatch.setattr(dl, "_monotonic", lambda: now[0])
    f = tmp_path / "z"
    resp = FakeResp([b"a"] * 100, on_read=lambda: now.__setitem__(0, now[0] + 1.0))
    with pytest.raises(DownloadTimeout):
        download_archive(URL, f, 10_000, 5, opener=FakeOpener(resp))
    assert not f.exists()


def test_success_writes_file_and_sends_ua(tmp_path):
    f = tmp_path / "sub" / "z.zip"
    resp = FakeResp([b"hello", b"world"], {"Content-Length": "10"})
    op = FakeOpener(resp)
    assert download_archive(URL, f, 100, 5, opener=op) == f
    assert f.read_bytes() == b"helloworld"
    req, timeout = op.requests[0]
    assert req.get_header("User-agent") == dl.USER_AGENT
    assert not req.has_header("Cookie") and not req.has_header("Authorization")
    assert timeout == 5 and resp.closed


@pytest.mark.parametrize(
    "bad",
    [
        "http://codeload.github.com/o/r/zip/HEAD",
        "https://github.com/o/r/zip/HEAD",
        "https://codeload.github.com.evil.com/o/r",
        "https://u@codeload.github.com/o/r",
        "https://codeload.github.com:8443/o/r",
        "file:///etc/passwd",
    ],
)
def test_initial_url_rejected_without_network(tmp_path, bad):
    op = FakeOpener(FakeResp())
    with pytest.raises(DownloadError):
        download_archive(bad, tmp_path / "z", 100, 5, opener=op)
    assert op.requests == []


def _redirect(newurl):
    h = dl._SafeRedirectHandler()
    req = urllib.request.Request(URL)
    return h.redirect_request(req, None, 302, "Found", {}, newurl)


@pytest.mark.parametrize(
    "newurl",
    [
        "https://evil.com/x",
        "http://codeload.github.com/o/r/zip/abc",
        "https://github.com/o/r",
        "https://codeload.github.com.evil.com/x",
        "https://user@codeload.github.com/x",
        "https://codeload.github.com:444/x",
        "ftp://codeload.github.com/x",
    ],
)
def test_redirect_refused(newurl):
    with pytest.raises(DownloadError):
        _redirect(newurl)


def test_redirect_within_codeload_accepted():
    new = _redirect("https://codeload.github.com/o/r/legacy.zip/refs/heads/main")
    assert new is not None
    assert new.full_url == "https://codeload.github.com/o/r/legacy.zip/refs/heads/main"


def test_real_opener_has_no_http_or_cookie_handlers():
    names = {type(h).__name__ for h in dl._build_opener().handlers}
    assert "HTTPHandler" not in names and "HTTPCookieProcessor" not in names
    assert dl._SafeRedirectHandler.max_redirections <= 3
