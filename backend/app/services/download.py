"""Capped, time-limited download of a GitHub archive (stdlib only).

Decisions:
- Only ``https://codeload.github.com/...`` is allowed, initially and on every
  redirect (max 3). No userinfo, no port, no http. ``http://`` is not even
  registered with the opener.
- No cookies or credentials are sent; environment proxies are ignored.
- ``timeout`` is both the per-socket-operation timeout and the total
  wall-clock deadline, checked after the request and after every chunk. A
  single blocked read can overrun the deadline by at most ``timeout``.
- Tests inject a fake via the ``opener`` parameter or by monkeypatching
  ``_build_opener`` / ``_monotonic``.
"""

from __future__ import annotations

import socket
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

ALLOWED_HOST = "codeload.github.com"
USER_AGENT = "ReviveOps/1.0 (+public-scan)"
MAX_REDIRECTS = 3
_CHUNK = 64 * 1024

_monotonic = time.monotonic


class DownloadError(Exception):
    """Generic download failure."""


class RepoNotFound(DownloadError):
    pass


class DownloadTooLarge(DownloadError):
    pass


class DownloadTimeout(DownloadError):
    pass


def _check_url(url: str) -> None:
    try:
        parts = urlsplit(url)
        netloc = parts.netloc
        scheme = parts.scheme
    except ValueError as exc:
        raise DownloadError("Download URL is not allowed.") from exc
    if scheme != "https" or netloc != ALLOWED_HOST:
        raise DownloadError("Download URL is not allowed.")


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    max_redirections = MAX_REDIRECTS
    max_repeats = MAX_REDIRECTS

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _check_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _build_opener() -> urllib.request.OpenerDirector:
    opener = urllib.request.OpenerDirector()
    for handler in (
        urllib.request.ProxyHandler({}),
        urllib.request.HTTPSHandler(),
        _SafeRedirectHandler(),
        urllib.request.HTTPDefaultErrorHandler(),
        urllib.request.HTTPErrorProcessor(),
        urllib.request.UnknownHandler(),
    ):
        opener.add_handler(handler)
    return opener


def _is_timeout(exc: BaseException) -> bool:
    return isinstance(exc, (socket.timeout, TimeoutError))


def download_archive(url, dest_file, max_bytes, timeout, opener=None) -> Path:
    dest_file = Path(dest_file)
    _check_url(url)
    if opener is None:
        opener = _build_opener()
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/zip"}
    )
    deadline = _monotonic() + timeout
    resp = None
    try:
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            resp = opener.open(req, timeout=timeout)
        except urllib.error.HTTPError as exc:
            if exc.code in (403, 404, 410):
                raise RepoNotFound("Repository not found or not public.") from exc
            raise DownloadError(f"Download failed (HTTP {exc.code}).") from exc
        except urllib.error.URLError as exc:
            if _is_timeout(exc.reason):
                raise DownloadTimeout("Download timed out.") from exc
            raise DownloadError("Download failed.") from exc
        if _monotonic() > deadline:
            raise DownloadTimeout("Download timed out.")
        length = resp.headers.get("Content-Length")
        if length is not None:
            try:
                if int(length) > max_bytes:
                    raise DownloadTooLarge("Repository archive is too large.")
            except ValueError:
                pass
        total = 0
        with open(dest_file, "wb") as out:
            while True:
                chunk = resp.read(_CHUNK)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise DownloadTooLarge("Repository archive is too large.")
                out.write(chunk)
                if _monotonic() > deadline:
                    raise DownloadTimeout("Download timed out.")
        return dest_file
    except BaseException as exc:
        try:
            dest_file.unlink()
        except OSError:
            pass
        if isinstance(exc, DownloadError):
            raise
        if _is_timeout(exc):
            raise DownloadTimeout("Download timed out.") from exc
        if isinstance(exc, (OSError, EOFError)) or type(exc).__module__ == "http.client":
            raise DownloadError("Download failed.") from exc
        raise
    finally:
        if resp is not None:
            try:
                resp.close()
            except Exception:
                pass
