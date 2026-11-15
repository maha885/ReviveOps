"""Safe repository traversal with ignore rules and configurable limits.

Key safety properties:
- Never follows symlinks that resolve outside the repository root.
- Skips well-known non-source directories (.git, node_modules, venv, build, …).
- Enforces file-count, file-size, and duration limits.
- Never executes anything — reads file metadata only.
- Handles unreadable files gracefully (records error, continues).
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from .models import ScanLimits

# Directories that are always excluded from traversal.
IGNORED_DIR_NAMES: frozenset[str] = frozenset({
    # Version control
    ".git", ".svn", ".hg",
    # Dependencies
    "node_modules", "vendor", "Pods", ".bundle",
    # Python
    "__pycache__", ".venv", "venv", "env", ".tox", ".eggs", "htmlcov",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
    # Build outputs
    "dist", "build", "out", "target", "bin", "obj",
    # JS / TS build
    ".next", ".turbo", ".parcel-cache", ".nuxt",
    # Coverage
    "coverage", ".nyc_output",
    # IDE / editor
    ".idea", ".vscode",
    # Misc caches
    ".cache", "tmp", ".tmp",
})


def is_ignored_dir(name: str) -> bool:
    """Return True if a directory name should be excluded from traversal."""
    if name in IGNORED_DIR_NAMES:
        return True
    # Python egg-info directories: *.egg-info
    if name.endswith(".egg-info"):
        return True
    return False


@dataclass
class TraversalResult:
    """Output of the traversal phase."""

    files: list[tuple[Path, str]] = field(default_factory=list)  # (abs_path, rel_path)
    file_count: int = 0
    truncated: bool = False
    errors: list[str] = field(default_factory=list)


def traverse(root: Path, limits: ScanLimits) -> TraversalResult:
    """Walk a directory tree safely, returning files within limits.

    Uses ``os.walk`` with ``topdown=True`` so we can prune ignored
    directories in-place, and ``followlinks=False`` so directory symlinks
    are never descended into.

    Args:
        root:  The repository root directory (must exist and be a directory).
        limits: Safety limits for file count, size, and duration.

    Returns:
        TraversalResult with the collected files and any errors.
    """
    result = TraversalResult()
    start_time = time.monotonic()
    root_resolved = root.resolve()

    try:
        for dirpath, dirnames, filenames in os.walk(
            root, topdown=True, followlinks=False
        ):
            # Prune ignored directories in-place so os.walk skips them.
            dirnames[:] = [d for d in dirnames if not is_ignored_dir(d)]

            for filename in filenames:
                # ── Check file-count limit ──
                if result.file_count >= limits.max_files:
                    result.truncated = True
                    return result

                # ── Check duration limit ──
                if time.monotonic() - start_time > limits.max_duration_seconds:
                    result.truncated = True
                    return result

                filepath = Path(dirpath) / filename

                # ── Skip symlinks that point outside root ──
                if filepath.is_symlink():
                    try:
                        resolved = filepath.resolve()
                        if resolved != root_resolved and root_resolved not in resolved.parents:
                            continue
                    except (OSError, RuntimeError):
                        # Cannot resolve — skip to be safe.
                        continue

                # ── Check file size ──
                try:
                    size = filepath.stat().st_size
                except OSError:
                    result.errors.append(f"Cannot stat: {filepath}")
                    continue

                if size > limits.max_file_size_bytes:
                    continue

                # ── Compute relative path (forward-slash normalised) ──
                try:
                    rel_path = str(filepath.relative_to(root)).replace(os.sep, "/")
                except ValueError:
                    continue

                result.files.append((filepath, rel_path))
                result.file_count += 1

    except OSError as exc:
        result.errors.append(f"Traversal error: {exc}")

    return result
