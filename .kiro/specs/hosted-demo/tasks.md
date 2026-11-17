# Hosted Demo Mode — Tasks

## Backend
- [x] Add `demo_mode` and revived-copy age settings to `app/config.py`.
- [x] Add `GET /api/config`.
- [x] Restrict `POST /api/scans` to the bundled demo when `demo_mode` is on (HTTP 403 otherwise).
- [x] Clean up old revived copies before creating a new one.
- [x] Serve `frontend/dist` from FastAPI with an SPA fallback, without shadowing `/api` or `/health`.
- [x] Tests: config endpoint, 403 in demo mode, unchanged behavior when the flag is off, SPA fallback, route priority.

## Frontend
- [x] Add `getConfig()` to the API client.
- [x] Hide or disable the path input in demo mode with an explanatory note; keep "Use Demo Repository" prominent.
- [x] Typecheck and build pass.

## Packaging and docs
- [ ] Multi-stage `Dockerfile` and `.dockerignore`.
- [ ] README: "Hosted demo" section (env var, Docker build/run, deploy to a free non-AWS/Azure/GCP host, note that storage is ephemeral).
- [ ] Verify the container locally: `docker build` then `docker run -p 8000:8000`, open `http://localhost:8000`, run the demo end to end.

## Deployment
- [ ] Deploy to a free host and confirm the public URL works logged out.
- [ ] Put the URL in the README and the Devpost form.

## Stretch (only if time allows)
- [ ] GitHub URL validator as a pure function with a Hypothesis property test.
- [ ] Shallow clone helper with timeout, size cap, hooks disabled, and cleanup.
- [ ] `POST /api/scans` accepts `{"github_url": "..."}` in demo mode; UI input for it.
