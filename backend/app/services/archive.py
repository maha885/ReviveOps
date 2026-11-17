"""Safe zip extraction. Nothing is executed or imported; files are written
with plain ``open()`` and permissions/exec bits are not preserved.

Decisions:
- Entries are skipped (not errors) when: absolute, contain ``\\`` (any
  backslash), contain ``:`` (drive letters / NTFS streams), NUL, a ``..``
  component, resolve outside ``dest``, or sit under a symlink on disk.
- Symlink entries and any other non-regular, non-directory entries (by the
  unix mode in ``external_attr``) are skipped.
- Duplicate names and file/directory collisions: the later entry is skipped.
- Size is counted while streaming; header ``file_size`` is never trusted.
- Cleanup on failure: only what this call created is removed. If ``dest``
  did not exist beforehand it is removed entirely; if it pre-existed it is
  kept, and only the entries this call wrote are deleted.
- Returns the single top-level directory if the extracted content is exactly
  one directory, otherwise ``dest``.
"""

from __future__ import annotations

import shutil
import stat
import zipfile
import zlib
from pathlib import Path, PurePosixPath

_CHUNK = 64 * 1024


class ArchiveError(Exception):
    """Base class for archive problems."""


class ArchiveTooLarge(ArchiveError):
    pass


class UnsafeArchive(ArchiveError):
    pass


class NotAZip(ArchiveError):
    pass


def _clean_parts(name: str) -> list[str] | None:
    """Return safe path components, or None if the entry must be skipped."""
    if not name or "\\" in name or ":" in name or "\x00" in name:
        return None
    if name.startswith("/"):
        return None
    parts = [p for p in name.split("/") if p not in ("", ".")]
    if not parts or any(p == ".." for p in parts):
        return None
    return parts


def _inside(base: Path, target: Path) -> bool:
    try:
        target.resolve().relative_to(base)
        return True
    except (ValueError, OSError):
        return False


def _has_symlink_between(base: Path, target: Path) -> bool:
    cur = target
    while cur != base and cur != cur.parent:
        if cur.is_symlink():
            return True
        cur = cur.parent
    return False


def _remove(path: Path) -> None:
    try:
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
    except OSError:
        pass


def safe_extract_zip(
    zip_path: Path, dest: Path, max_total_bytes: int, max_entries: int
) -> Path:
    zip_path = Path(zip_path)
    dest = Path(dest)
    try:
        zf = zipfile.ZipFile(zip_path)
    except (zipfile.BadZipFile, EOFError) as exc:
        raise NotAZip("File is not a valid zip archive.") from exc

    created_dest = not dest.exists()
    created_top: list[str] = []  # top-level names created under dest
    try:
        with zf:
            infos = zf.infolist()
            if len(infos) > max_entries:
                raise ArchiveTooLarge("Archive has too many entries.")
            dest.mkdir(parents=True, exist_ok=True)
            base = dest.resolve()
            total = 0
            for info in infos:
                # orig_filename: zipfile rewrites os.sep to "/" on Windows in
                # .filename, which would hide backslashes.
                parts = _clean_parts(info.orig_filename)
                if parts is None:
                    continue
                mode = info.external_attr >> 16
                fmt = stat.S_IFMT(mode)
                is_dir = info.is_dir() or fmt == stat.S_IFDIR
                if fmt and not is_dir and fmt != stat.S_IFREG:
                    continue  # symlink, device, fifo, socket...
                target = base.joinpath(*parts)
                if not _inside(base, target) or _has_symlink_between(base, target):
                    continue
                # Collision checks: an ancestor that is a file, or target exists.
                if any(p.exists() and not p.is_dir() for p in list(target.parents)
                       if p != base and base in p.parents):
                    continue
                if is_dir:
                    if target.exists() and not target.is_dir():
                        continue
                    new_top = parts[0] not in created_top and not (base / parts[0]).exists()
                    target.mkdir(parents=True, exist_ok=True)
                    if new_top:
                        created_top.append(parts[0])
                    continue
                if target.exists():
                    continue
                new_top = parts[0] not in created_top and not (base / parts[0]).exists()
                target.parent.mkdir(parents=True, exist_ok=True)
                if new_top:
                    created_top.append(parts[0])
                with zf.open(info) as src, open(target, "wb") as out:
                    while True:
                        chunk = src.read(_CHUNK)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > max_total_bytes:
                            raise ArchiveTooLarge("Archive is too large when extracted.")
                        out.write(chunk)
    except BaseException as exc:
        if created_dest:
            shutil.rmtree(dest, ignore_errors=True)
        else:
            for name in created_top:
                _remove(dest / name)
        if isinstance(exc, (zipfile.BadZipFile, zlib.error, EOFError,
                            NotImplementedError, RuntimeError)):
            raise NotAZip("Archive is corrupt or unsupported.") from exc
        raise

    children = list(dest.iterdir())
    if len(children) == 1 and children[0].is_dir() and not children[0].is_symlink():
        return children[0]
    return dest
