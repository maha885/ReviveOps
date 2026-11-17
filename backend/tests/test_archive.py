import stat
import tempfile
import zipfile
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st

from app.services.archive import (
    ArchiveTooLarge,
    NotAZip,
    safe_extract_zip,
)


def make_zip(path: Path, entries, compression=zipfile.ZIP_DEFLATED) -> Path:
    """entries: list of (name, bytes) or (ZipInfo, bytes)."""
    with zipfile.ZipFile(path, "w", compression) as zf:
        for name, data in entries:
            if isinstance(name, str) and "\\" in name:
                # ZipInfo() rewrites os.sep on Windows; force a literal
                # backslash into the stored name like a hostile archive would.
                zi = zipfile.ZipInfo("placeholder")
                zi.filename = name
                zi.compress_type = compression
                zf.writestr(zi, data)
            else:
                zf.writestr(name, data)
    return path


def snapshot(root: Path) -> set[str]:
    return {str(p.relative_to(root)) for p in root.rglob("*")}


def files_under(root: Path) -> set[str]:
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}


def test_zip_slip_skipped(tmp_path):
    z = make_zip(tmp_path / "a.zip", [("../evil.txt", b"x"), ("ok/a.txt", b"1")])
    dest = tmp_path / "out" / "d"
    before = snapshot(tmp_path)
    safe_extract_zip(z, dest, 1000, 10)
    assert not (tmp_path / "out" / "evil.txt").exists()
    assert files_under(dest) == {"ok/a.txt"}
    assert snapshot(tmp_path) - before == {
        str(Path("out")), str(Path("out/d")), str(Path("out/d/ok")),
        str(Path("out/d/ok/a.txt")),
    }


@pytest.mark.parametrize(
    "name",
    ["/abs.txt", "C:/win.txt", "C:\\win.txt", "a\\b.txt", "..\\x.txt", "a/../../x", "a:b"],
)
def test_unsafe_names_skipped(tmp_path, name):
    z = make_zip(tmp_path / "a.zip", [(name, b"x"), ("good.txt", b"1")])
    dest = tmp_path / "d"
    safe_extract_zip(z, dest, 1000, 10)
    assert files_under(dest) == {"good.txt"}
    assert not (tmp_path / "x").exists() and not (tmp_path / "x.txt").exists()


def test_symlink_entry_skipped(tmp_path):
    info = zipfile.ZipInfo("link")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    z = make_zip(tmp_path / "a.zip", [(info, b"/etc/passwd"), ("f.txt", b"1")])
    dest = tmp_path / "d"
    safe_extract_zip(z, dest, 1000, 10)
    assert files_under(dest) == {"f.txt"}
    assert not (dest / "link").exists() and not (dest / "link").is_symlink()


def test_write_through_symlink_on_disk_skipped(tmp_path):
    dest = tmp_path / "d"
    outside = tmp_path / "outside"
    outside.mkdir()
    dest.mkdir()
    try:
        (dest / "lnk").symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not permitted")
    z = make_zip(tmp_path / "a.zip", [("lnk/pwn.txt", b"x")])
    safe_extract_zip(z, dest, 1000, 10)
    assert list(outside.iterdir()) == []


def test_size_cap_with_lying_headers_cleans_up(tmp_path):
    zpath = tmp_path / "a.zip"
    make_zip(zpath, [("a.txt", b"a" * 100), ("b.txt", b"b" * 5000)])
    # Make headers lie: file_size claims 1 byte for each entry.
    with zipfile.ZipFile(zpath) as zf:
        infos = zf.infolist()
    raw = zpath.read_bytes()
    for i in infos:
        real = i.file_size.to_bytes(4, "little")
        raw = raw.replace(real, (1).to_bytes(4, "little"))
    zpath.write_bytes(raw)
    dest = tmp_path / "d"
    with pytest.raises(Exception) as ei:
        safe_extract_zip(zpath, dest, 500, 10)
    assert isinstance(ei.value, (ArchiveTooLarge, NotAZip))
    assert not dest.exists()


def test_size_cap_aborts_and_cleans_up(tmp_path):
    z = make_zip(tmp_path / "a.zip", [("a.txt", b"a" * 400), ("b/c.txt", b"b" * 400)])
    dest = tmp_path / "d"
    with pytest.raises(ArchiveTooLarge):
        safe_extract_zip(z, dest, 500, 10)
    assert not dest.exists()


def test_size_cap_keeps_preexisting_dest(tmp_path):
    z = make_zip(tmp_path / "a.zip", [("a.txt", b"a" * 400), ("b/c.txt", b"b" * 400)])
    dest = tmp_path / "d"
    dest.mkdir()
    (dest / "keep.txt").write_text("k")
    with pytest.raises(ArchiveTooLarge):
        safe_extract_zip(z, dest, 500, 10)
    assert snapshot(dest) == {"keep.txt"}


def test_entry_count_cap(tmp_path):
    z = make_zip(tmp_path / "a.zip", [(f"f{i}.txt", b"x") for i in range(5)])
    dest = tmp_path / "d"
    with pytest.raises(ArchiveTooLarge):
        safe_extract_zip(z, dest, 1000, 4)
    assert not dest.exists()


def test_single_top_folder_is_root(tmp_path):
    z = make_zip(tmp_path / "a.zip", [("repo-abc/a.txt", b"1"), ("repo-abc/s/b.txt", b"2")])
    dest = tmp_path / "d"
    assert safe_extract_zip(z, dest, 1000, 10) == dest / "repo-abc"


def test_multiple_roots_returns_dest(tmp_path):
    z = make_zip(tmp_path / "a.zip", [("one/a.txt", b"1"), ("two/b.txt", b"2")])
    dest = tmp_path / "d"
    assert safe_extract_zip(z, dest, 1000, 10) == dest


def test_top_folder_plus_file_returns_dest(tmp_path):
    z = make_zip(tmp_path / "a.zip", [("one/a.txt", b"1"), ("top.txt", b"2")])
    dest = tmp_path / "d"
    assert safe_extract_zip(z, dest, 1000, 10) == dest


def test_not_a_zip(tmp_path):
    p = tmp_path / "x.zip"
    p.write_bytes(b"this is not a zip")
    with pytest.raises(NotAZip):
        safe_extract_zip(p, tmp_path / "d", 1000, 10)
    assert not (tmp_path / "d").exists()


def test_empty_zip(tmp_path):
    z = make_zip(tmp_path / "a.zip", [])
    dest = tmp_path / "d"
    assert safe_extract_zip(z, dest, 1000, 10) == dest
    assert list(dest.iterdir()) == []


def test_duplicate_and_collision_skipped(tmp_path):
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        z = make_zip(
            tmp_path / "a.zip",
            [("a.txt", b"first"), ("a.txt", b"second"), ("a.txt/b.txt", b"x"), ("d/f", b"1"), ("d", b"file")],
        )
    dest = tmp_path / "x"
    safe_extract_zip(z, dest, 1000, 10)
    assert (dest / "a.txt").read_bytes() == b"first"
    assert (dest / "d" / "f").is_file()


part = st.sampled_from(["..", ".", "a", "b.txt", "", "C:", "/", "\\", "x\\..\\y", "..\\.."])
member_names = st.lists(part, min_size=1, max_size=5).flatmap(
    lambda ps: st.sampled_from(["/", "\\", "//"]).map(lambda sep: sep.join(ps))
) | st.sampled_from(["/etc/passwd", "C:\\evil", "c:/evil", "\\\\srv\\share\\x", "../../evil"])


@given(st.lists(member_names, min_size=1, max_size=6))
@settings(max_examples=100, deadline=None)
def test_nothing_written_outside_dest(names):
    with tempfile.TemporaryDirectory() as td:
        parent = Path(td) / "parent"
        parent.mkdir()
        zpath = Path(td) / "a.zip"
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            make_zip(zpath, [(n, b"data") for n in names])
        dest = parent / "dest"
        before = snapshot(Path(td))
        safe_extract_zip(zpath, dest, 10_000, 100)
        added = snapshot(Path(td)) - before
        for rel in added:
            assert rel == "parent\\dest" or rel == "parent/dest" or Path(rel).parts[:2] == ("parent", "dest"), rel
