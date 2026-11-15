# ReviveOps MVP — Requirements

## Goal
Build a local-first workbench that scans a dormant repository and produces an evidence-based revival plan.

## User stories

### US-1: Load a repository
As a developer, I want to select a local repository folder or use a bundled demo, so I can inspect a project without uploading it.

**Acceptance criteria**
- The UI offers “Use demo repository” and “Select folder” (folder selection may be gated by browser support; API path input is available in local mode).
- The API validates that the path exists and is a directory.
- The scan is read-only and does not execute scripts or commands.
- The UI shows the repository name and scan timestamp.

### US-2: Scan repository health
As a developer, I want a scan of project structure and common project signals, so I can understand what is present or missing.

**Acceptance criteria**
- Detect README, manifests, lockfiles, tests, CI configuration, Dockerfile, and common scripts.
- Identify TODO/FIXME markers in a bounded set of text files.
- Ignore `.git`, `node_modules`, virtual environments, caches, and build directories.
- Apply file-count, file-size, and time limits to prevent runaway scans.
- Return findings with severity, category, evidence, and recommended next action.

### US-3: Calculate a transparent revival score
As a developer, I want a score with visible reasons, so I can prioritize recovery work.

**Acceptance criteria**
- Score is 0–100 and deterministic for the same scan result.
- Score dimensions include documentation, dependency/build signals, tests, CI, and containerization.
- UI displays dimension breakdown and explains score deductions/additions.
- Score is labeled “heuristic”, not a guarantee that the project will run.

### US-4: Create a prioritized revival checklist
As a developer, I want findings converted into ordered tasks, so I can act on the highest-impact blockers first.

**Acceptance criteria**
- Checklist items include priority, rationale, evidence, and suggested action.
- Critical setup blockers rank above cosmetic or maintenance suggestions.
- Users can mark tasks open/done; state persists locally.
- No task runs commands or edits repository files automatically.

### US-5: Explain a finding
As a developer, I want a plain-language explanation and a safe next step for a finding.

**Acceptance criteria**
- Explanation endpoint works without an LLM using deterministic templates.
- If Ollama is configured, the user can explicitly request local AI explanation.
- AI output is clearly labeled and includes a reminder to review commands before running them.
- Repository content is not sent to external APIs by default.

### US-6: Export a revival report
As a developer, I want to export scan results and checklist as Markdown, so I can share or track the recovery plan.

**Acceptance criteria**
- Report includes repository name, timestamp, score, dimensions, findings, and checklist.
- Export is downloadable as a `.md` file.
- Export succeeds when AI is unavailable.

## Quality requirements
- Local setup documented and reproducible.
- API errors are actionable and do not expose stack traces to the UI.
- Scanner handles unreadable files gracefully.
- Unit tests cover scoring, ignore rules, and scan limits.
- Core workflow has no cloud-provider dependency.
