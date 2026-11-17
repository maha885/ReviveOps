"""Housekeeping for revived copies."""

import os
import shutil
import time
from pathlib import Path


def cleanup_old_revived(
    revived_dir: Path,
    max_age_minutes: int,
    keep: Path | None = None,
    now: float | None = None,
) -> list[str]:
    """Prune ``backend/revived`` (see :func:`cleanup_old_dirs`)."""
    return cleanup_old_dirs(revived_dir, max_age_minutes, keep=keep, now=now)


def cleanup_old_dirs(
    revived_dir: Path,
    max_age_minutes: int,
    keep: Path | None = None,
    now: float | None = None,
) -> list[str]:
    """Delete direct child directories of *revived_dir* older than the limit.

    Age is the directory's own mtime. Symlinks are never followed or removed,
    only real directories directly under *revived_dir* are candidates, and
    *keep* (the copy about to be created) is skipped. Errors are swallowed so
    cleanup can never fail a request. Returns the names that were removed.
    """
    removed: list[str] = []
    try:
        cutoff = (time.time() if now is None else now) - max_age_minutes * 60
        keep_name = keep.name if keep is not None else None
        with os.scandir(revived_dir) as entries:
            candidates = list(entries)
    except Exception:
        return removed

    for entry in candidates:
        try:
            if entry.name == keep_name:
                continue
            if entry.is_symlink() or not entry.is_dir(follow_symlinks=False):
                continue
            if entry.stat(follow_symlinks=False).st_mtime >= cutoff:
                continue
            shutil.rmtree(entry.path, ignore_errors=True)
            removed.append(entry.name)
        except Exception:
            continue
    return removed
