"""Application configuration.

Centralised settings so every module reads from one place.  Keeping this as a
simple Pydantic model (no extra dependencies) makes it easy for a solo
developer to understand and extend later.
"""

from pydantic import BaseModel


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


settings = Settings()
