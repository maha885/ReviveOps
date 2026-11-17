# Public Scan — Tasks

Run these in order in Kiro. Commit after each group so the history shows the spec-driven steps.

## Phase 1 — GitHub URL
- [ ] `services/github_url.py`: `parse_github_url`, `archive_url`, `InvalidGitHubUrl`.
- [ ] Hypothesis property tests for the URL parser (accept/reject properties from the design).
- [ ] `services/archive.py`: `safe_extract_zip` with zip-slip, symlink, size and entry caps.
- [ ] Unit tests + Hypothesis test for archive member names.
- [ ] `services/download.py`: capped, time-limited download; redirect only to `codeload.github.com`.
- [ ] `services/limits.py`: rate limiter and concurrency limit.
- [ ] `config.py`: new env-driven limits with safe defaults.
- [ ] `ScanRequest` accepts exactly one of `path` / `github_url`; `create_scan` handles `github_url`; error mapping.
- [ ] Extend cleanup to `backend/sources/`.
- [ ] API tests with a fake downloader (no real network), including 403 for non-demo `path` in demo mode.
- [ ] Frontend: `createScanFromGitHub`, GitHub URL input, loading and error states; typecheck and build.
- [ ] README: document the feature, limits, and env vars; remove the "not AWS, Azure or GCP" hosting line.
- [ ] Full test suite passes; push; redeploy and test with one real public repo on the live URL.

## Phase 2 — Zip upload (only if Phase 1 is done and tested)
- [ ] `POST /api/scans/upload` using the same extraction; add `python-multipart` if required (pinned).
- [ ] Tests: valid zip, non-zip, oversize, zip-slip.
- [ ] Frontend upload control and note.
- [ ] README update; full test suite; redeploy.

## Stretch
- [ ] Let `HEAD /` return 200 in demo mode (Render's health probe currently gets 405).
