# Technical Steering — ReviveOps

- Frontend: React, TypeScript, Vite.
- Backend: Python 3.11+ and FastAPI.
- Persistence: SQLite; keep persistence behind a small repository layer.
- Scanner: pathlib + safe file reads; ignore `.git`, virtual environments, node_modules, build outputs, and configurable large files.
- API: JSON REST; validate paths and enforce scan limits.
- Testing: pytest for API/scanner; Vitest for frontend.
- Local AI: Ollama adapter behind an interface; deterministic fallback is mandatory.
- Never use shell execution on scanned repositories in MVP.
- Keep modules small and typed; add tests with each feature.
