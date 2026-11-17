"""Application configuration.

Centralised settings so every module reads from one place.  Keeping this as a
simple Pydantic model (no extra dependencies) makes it easy for a solo
developer to understand and extend later.
"""

import os
from pathlib import Path

from pydantic import BaseModel, Field


_TRUE_VALUES = {"true", "1", "yes"}
REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _env_flag(name: str) -> bool:
    """True only for true/1/yes (case-insensitive). Unset or anything else is False."""
    return os.environ.get(name, "").strip().lower() in _TRUE_VALUES


def _env_int(name: str, default: int) -> int:
    try:
        value = int(os.environ.get(name, ""))
    except ValueError:
        return default
    return value if value >= 0 else default


def _default_frontend_dist() -> Path:
    override = os.environ.get("REVIVEOPS_FRONTEND_DIST")
    return Path(override) if override else REPO_ROOT / "frontend" / "dist"


class Settings(BaseModel):
    """Runtime configuration for the ReviveOps backend."""

    # App identity
    app_name: str = "ReviveOps"
    app_version: str = "0.1.0"
    description: str = "Local-first AI-powered software project resurrection platform."

    # CORS — origins allowed to call the API from the browser
    cors_origins: list[str] = [
        "http://localhost:5173",   # Vite dev server (default port)
        "http://localhost:3000",   # alternate dev port
    ]

    # API prefix for future versioned endpoints
    api_prefix: str = "/api"

    # Scanner safety limits
    scan_max_files: int = 5000
    scan_max_file_size_bytes: int = 512_000  # 512 KB
    scan_max_duration_seconds: float = 30.0
    scan_max_todo_findings: int = 50

    # SQLite database path (relative to the backend/ directory)
    database_path: str = "reviveops.db"

    # Hosted demo mode (env REVIVEOPS_DEMO_MODE). Never defaults to True.
    demo_mode: bool = Field(default_factory=lambda: _env_flag("REVIVEOPS_DEMO_MODE"))

    # Revived copies older than this are deleted before a new one is created.
    revived_max_age_minutes: int = Field(
        default_factory=lambda: _env_int("REVIVEOPS_REVIVED_MAX_AGE_MINUTES", 60)
    )

    # Built frontend served in demo mode (env REVIVEOPS_FRONTEND_DIST).
    frontend_dist_path: Path = Field(default_factory=_default_frontend_dist)


settings = Settings()
