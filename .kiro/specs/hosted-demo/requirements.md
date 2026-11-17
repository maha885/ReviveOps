# Hosted Demo Mode — Requirements

## Goal
Let hackathon judges (and anyone else) use ReviveOps from a public URL without installing anything, while keeping the full local-first workflow for people who run it on their own machine.

## Why
The submission requires a URL to a functional application. A public server must never read arbitrary paths from its own filesystem, so the hosted app needs a restricted mode.

## User stories

### US-1: Try ReviveOps from a URL
As a judge, I want to open one URL and scan the bundled demo, so I can see the product working without setup.

**Acceptance criteria**
- A single deployed service serves both the API and the built React UI.
- "Use Demo Repository" works end to end: scan, score, checklist, report, Preview changes, Revive a copy.
- The sidebar health indicator shows Backend Online.
- No account, login, or API key is needed.

### US-2: Demo mode protects the server
As the operator, I want the hosted app to refuse arbitrary filesystem paths, so visitors cannot read files on the server.

**Acceptance criteria**
- Demo mode is switched on by the environment variable `REVIVEOPS_DEMO_MODE=true`; it is off by default so local use is unchanged.
- In demo mode, `POST /api/scans` accepts only the bundled demo (`{"path": "demo"}`); any other path returns HTTP 403 with a clear message.
- Revive output stays inside the server's revived-output folder and old revived copies are cleaned up (bounded disk use).
- Scan limits (files, size, time) still apply.

### US-3: The UI explains the mode
As a visitor, I want the UI to tell me why the folder-path input is unavailable, so I am not confused.

**Acceptance criteria**
- `GET /api/config` reports `{ "demo_mode": true|false }`.
- In demo mode the path input is hidden or disabled, with a short note pointing to the README's local setup, and "Use Demo Repository" is the primary action.
- Local mode looks and behaves exactly as before.

### US-3b: Scan a public GitHub repository (moved to `.kiro/specs/public-scan`)
As a visitor, I want to paste a public GitHub URL, so I can try ReviveOps on a real dormant project.

**Acceptance criteria**
- Only `https://github.com/<owner>/<repo>` URLs are accepted; anything else is rejected with HTTP 422.
- The repository is cloned shallowly into a temporary folder with a size and time limit, with hooks disabled, and deleted after the scan.
- Nothing from the cloned repository is ever executed.
- This story ships only if the above safety criteria are met; otherwise it is dropped.

### US-4: Deployable by anyone
As a contributor, I want a documented deploy path, so the hosted demo can be reproduced.

**Acceptance criteria**
- A `Dockerfile` builds the UI and runs the API in one container.
- README documents the environment variable, the build, and deploying to a free host.
- Any host that runs a Dockerfile works. (The Official Rules do not restrict hosting providers.)

## Out of scope
- Authentication, user accounts, or per-user storage.
- Persisting scans across redeploys (hosted storage may be ephemeral).
- Uploading zip files.
