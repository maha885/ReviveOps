# Product Steering — ReviveOps

## Product principle
Help developers revive dormant repositories safely, transparently, and locally.

## Target user
A developer inheriting an old, abandoned, or currently failing codebase who needs a fast, structured path to understand and restart it.

## Experience principles
- Local-first: repository data stays on the machine unless the user explicitly configures an external service.
- Explainable: every score and recommendation links to concrete evidence.
- Safe by default: inspect and recommend; never modify files or run arbitrary scripts automatically.
- Useful without AI: core scan, score, checklist, and report work deterministically.
- Honest: distinguish observed facts, heuristics, and AI-generated suggestions.

## MVP boundaries
- Scan one repository at a time.
- Support common indicators: README, package manifests, lockfiles, Dockerfile, CI config, tests, scripts, TODO/FIXME, and missing setup documentation.
- Do not execute repository commands during scanning.
- No authentication or multi-user collaboration.
