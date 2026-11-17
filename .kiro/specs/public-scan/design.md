# Public Scan — Design

## Modules (new, small, pure where possible)
- `backend/app/services/github_url.py` — `parse_github_url(url: str) -> GitHubRepo(owner, repo)`. Pure function, raises `InvalidGitHubUrl`. Uses `urllib.parse` and a strict regex; no network. Also `archive_url(repo) -> str` (always `https://codeload.github.com/{owner}/{repo}/zip/HEAD`).
- `backend/app/services/archive.py` — `safe_extract_zip(zip_path, dest, max_total_bytes, max_entries) -> Path` returning the scan root (the single top-level folder if there is exactly one, else `dest`). Raises `ArchiveTooLarge`, `UnsafeArchive`, `NotAZip`.
- `backend/app/services/download.py` — `download_archive(url, dest_file, max_bytes, timeout)` using `urllib.request` with a custom redirect handler that only allows `codeload.github.com` over https. Streams in chunks, counts bytes, aborts past the cap. Raises `RepoNotFound`, `DownloadTooLarge`, `DownloadTimeout`.
- `backend/app/services/limits.py` — tiny in-memory sliding-window rate limiter keyed by client IP, plus a `threading.BoundedSemaphore` / `asyncio.Semaphore(2)` for concurrent extractions.
- `backend/app/config.py` — add `max_download_mb`, `max_extract_mb`, `max_extract_entries`, `scan_rate_per_minute` (env-driven, safe defaults).

## API changes
- `ScanRequest` becomes `{path: str | None, github_url: str | None}` with a validator that requires exactly one.
- `create_scan` order of checks in demo mode: (1) validate shape, (2) if `path` is set and not `"demo"` → 403 before any filesystem access (unchanged), (3) if `github_url` → rate limit → parse → download → extract → `_scan_and_persist(root, label="owner/repo")`.
- Extracted sources live under `backend/sources/<scan_id>/` and are recorded as the scan's `root_path`, so the existing revival-plan/revive code (`_load_source`) works without changes. The cleanup service also prunes `backend/sources/`.
- Error mapping: `InvalidGitHubUrl`→422, `RepoNotFound`→404, `DownloadTooLarge`/`ArchiveTooLarge`→413, `DownloadTimeout`→504, rate/concurrency→429, `UnsafeArchive`/`NotAZip`→422.
- Phase 2: `POST /api/scans/upload` (`UploadFile`) streams to a temp file with the byte cap, then calls the same `safe_extract_zip`.

## Frontend
- `client.ts`: `createScanFromGitHub(url)`; error helper that turns `{detail}` into a message.
- `ScanInput.tsx`: GitHub URL field with client-side hint (same rule as the server; the server is authoritative), Scan button, loading text "Fetching from GitHub…".
- Phase 2: `ZipUpload` control.

## Testing strategy
- **Property-based (Hypothesis):** `parse_github_url` — for generated valid owner/repo names it round-trips; for generated strings containing any forbidden element (other host, scheme, userinfo, port, `..`, `%`, whitespace, extra segments) it always raises. Property: the accepted output only ever contains `[A-Za-z0-9._-]`.
- **Property-based:** `safe_extract_zip` — for generated archive member names (including `../`, absolute, backslash, drive letters), nothing is ever written outside `dest`.
- **Unit:** zip-slip entry skipped; symlink entry skipped; size cap aborts and cleans up; entry-count cap; single-top-folder root detection; non-zip rejected.
- **Unit with a fake downloader (no real network in tests):** 404→404, oversize→413, timeout→504, redirect to another host refused.
- **API:** demo-mode 403 for `path` unchanged; `github_url` happy path using a monkeypatched downloader that serves a small in-memory zip; 422 for malformed URLs; 429 after the rate limit; revive works on a URL scan.
- Hosted demo tests and the full suite must still pass.

## Decisions (keep short, record here)
- Zip download instead of `git clone`: the runtime image has no `git`, it is faster, smaller, and avoids git hooks/submodules/LFS entirely.
- Stdlib only for the download so the image does not grow.
- Rate limiting is per-process and in-memory. That is enough for one free instance; document the limit.
