# syntax=docker/dockerfile:1

# ---- Stage 1: build the React UI -------------------------------------------
FROM node:22-alpine AS frontend-build
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: FastAPI runtime serving the API and the built UI -------------
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    REVIVEOPS_DEMO_MODE=true \
    REVIVEOPS_FRONTEND_DIST=/app/frontend/dist

# Non-root user. The app writes reviveops.db and revived/ next to its code
# (backend/), so that folder must be owned by this user.
RUN useradd --system --uid 10001 --create-home --home-dir /home/reviveops reviveops

WORKDIR /app/backend

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Application code and the bundled demo repository (needed by the demo scan).
COPY backend/app ./app
COPY backend/demo_repo ./demo_repo
COPY --from=frontend-build /build/frontend/dist /app/frontend/dist

RUN mkdir -p /app/backend/revived \
    && chown -R reviveops:reviveops /app

USER reviveops

EXPOSE 8000

# Shell form so ${PORT} expands; hosts such as Render inject PORT.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
