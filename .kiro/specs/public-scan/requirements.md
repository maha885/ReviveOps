# Public Scan — Requirements

## Goal
Let anyone use the hosted ReviveOps on a real project, not only the bundled demo: scan a **public GitHub repository by URL**, and (second phase) **upload a zip** of a local project.

## Why
The Official Rules require the project to be available "free of charge and without any restriction" for judges to test. A demo that can only scan one bundled repo is a restriction and weakens the "Potential Impact" case. A hosted server cannot read a visitor's local folders, so "scan local" on the hosted app means uploading a zip from the browser.

## Threat model
On a public server the risk is the visitor, not the repository. Every story below must keep these true:
- Nothing from a scanned repository is ever executed or imported.
- The server never reads its own filesystem on behalf of a visitor (`{"path": "/etc"}` stays 403 in demo mode).
- The server only contacts GitHub's archive host for URL scans (no SSRF, no redirects to other hosts).
- Disk, memory, CPU time and request rate are bounded.

## User stories

### US-1: Scan a public GitHub repository
As a visitor, I paste `https://github.com/<owner>/<repo>` and get a scan, score, checklist and report for that repository.

**Acceptance criteria**
- `POST /api/scans` accepts `{"github_url": "..."}` (exactly one of `path` or `github_url`; both or neither returns HTTP 422).
- Only URLs of the form `https://github.com/<owner>/<repo>` are accepted. An optional trailing `/`, `.git`, or `/tree/<branch>` is tolerated and ignored (the default branch is used). Anything else returns HTTP 422 with a clear message: other hosts, `http://`, userinfo (`user@`), ports, query strings, IP addresses, `..`, extra path segments, or owner/repo names with characters outside `[A-Za-z0-9._-]`.
- The server downloads the repository archive from `https://codeload.github.com/<owner>/<repo>/zip/HEAD` using the standard library (no `git` binary, no new runtime dependency). Redirects to any other host are refused.
- Download is capped (default 25 MB, env `REVIVEOPS_MAX_DOWNLOAD_MB`) and time-limited (default 20 s). Exceeding either returns HTTP 413 or 504 with a clear message and leaves nothing behind.
- A private or missing repository returns HTTP 404 with the message "Repository not found or not public."
- The archive is extracted safely (see US-3), scanned with the existing scanner and limits, saved like any other scan (label `owner/repo`), and the temporary download is deleted.
- Revive (`POST /api/scans/{id}/revive`) and the revival plan work on these scans exactly as on the demo.

### US-2: Protect the free host
**Acceptance criteria**
- A simple in-process rate limit on scan creation (default 10 per minute per client IP, env `REVIVEOPS_SCAN_RATE_PER_MINUTE`) returns HTTP 429 when exceeded.
- At most 2 downloads/extractions run concurrently; extra requests get HTTP 429 or wait (design decision, documented).
- Extracted source folders and old revived copies are cleaned up by the existing age-based cleanup (extend it, do not duplicate it).

### US-3: Safe archive extraction (shared by GitHub URL and zip upload)
**Acceptance criteria**
- Entries whose resolved path would leave the destination ("zip-slip"), absolute paths, and drive letters are skipped.
- Symlink entries are skipped.
- Total uncompressed size is capped (default 100 MB) and entry count is capped (default 10,000); exceeding either aborts with HTTP 413 and removes the partial folder.
- Compression-ratio abuse ("zip bomb") is caught by the uncompressed-size cap measured while streaming, not by trusting the header.
- GitHub archives contain a single top-level folder `<repo>-<sha>/`; scanning starts inside it.

### US-4: UI
**Acceptance criteria**
- In demo (hosted) mode the scan card shows a GitHub URL input with a Scan button, plus the existing "Use Demo Repository". The folder-path input stays hidden, with the existing note.
- Validation errors from the API (422/404/413/429/504) are shown as readable messages, not raw JSON.
- A loading state is shown while the download runs (it may take several seconds).
- Local mode is unchanged and may also show the GitHub URL input.

### US-5 (phase 2): Upload a zip of a local project
**Acceptance criteria**
- `POST /api/scans/upload` accepts a multipart `.zip` (default cap 25 MB, same env var) and returns a scan using the same safe extraction.
- Content type and extension are checked, but the real check is that the file opens as a zip; a non-zip returns HTTP 422.
- The UI offers a drag-and-drop / file picker next to the GitHub URL input, with the note "Zip your project folder and upload it. Nothing is executed."
- If `python-multipart` is needed, it is added to `backend/requirements.txt` with a pinned version.

## Out of scope
- Private repositories, authentication, GitHub tokens.
- Scanning branches other than the default one.
- Persisting scans across redeploys.
- Executing, building, or installing anything from a scanned repository.

## Hosting note
The Official Rules do not restrict hosting providers. (An earlier draft of the hosted-demo spec said hosting must avoid AWS, Azure and GCP. That was not in the rules and has been removed.)
