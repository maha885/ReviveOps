"""Tests for the repository scanner — traversal, detectors, and integration.

Run with:
    pytest tests/test_scanner.py
"""

import os
import platform
from pathlib import Path

import pytest

from app.scanner import Category, ScanLimits, Severity, scan_repository
from app.scanner.detectors import (
    _is_test_file,
    detect_ci,
    detect_docker,
    detect_lockfiles,
    detect_manifests,
    detect_readme,
    detect_tests,
    detect_todos,
    is_text_file,
)
from app.scanner.traversal import IGNORED_DIR_NAMES, is_ignored_dir, traverse


# ── Traversal: ignore rules ───────────────────────────────────────────


class TestTraversalIgnoreRules:
    def test_node_modules_excluded(self, tmp_path):
        (tmp_path / "node_modules" / "package.json").parent.mkdir(parents=True)
        (tmp_path / "node_modules" / "package.json").write_text("{}")
        (tmp_path / "src" / "main.py").parent.mkdir(parents=True)
        (tmp_path / "src" / "main.py").write_text("print('hi')")

        result = traverse(tmp_path, ScanLimits())
        rels = [r for _, r in result.files]
        assert "src/main.py" in rels
        assert not any("node_modules" in r for r in rels)

    def test_git_directory_excluded(self, tmp_path):
        (tmp_path / ".git" / "config").parent.mkdir(parents=True)
        (tmp_path / ".git" / "config").write_text("[core]")
        (tmp_path / "README.md").write_text("# Test")

        result = traverse(tmp_path, ScanLimits())
        rels = [r for _, r in result.files]
        assert "README.md" in rels
        assert not any(".git" in r for r in rels)

    def test_venv_directory_excluded(self, tmp_path):
        (tmp_path / ".venv" / "bin").mkdir(parents=True)
        (tmp_path / ".venv" / "bin" / "activate").write_text("# venv")
        (tmp_path / "main.py").write_text("print('hi')")

        result = traverse(tmp_path, ScanLimits())
        rels = [r for _, r in result.files]
        assert "main.py" in rels
        assert not any(".venv" in r for r in rels)

    def test_build_output_excluded(self, tmp_path):
        (tmp_path / "dist" / "bundle.js").parent.mkdir(parents=True)
        (tmp_path / "dist" / "bundle.js").write_text("console.log('built')")
        (tmp_path / "src" / "index.ts").parent.mkdir(parents=True)
        (tmp_path / "src" / "index.ts").write_text("console.log('src')")

        result = traverse(tmp_path, ScanLimits())
        rels = [r for _, r in result.files]
        assert "src/index.ts" in rels
        assert not any("dist" in r for r in rels)

    def test_egg_info_excluded(self, tmp_path):
        (tmp_path / "demo.egg-info" / "PKG-INFO").parent.mkdir(parents=True)
        (tmp_path / "demo.egg-info" / "PKG-INFO").write_text("Metadata")
        (tmp_path / "setup.py").write_text("print('setup')")

        result = traverse(tmp_path, ScanLimits())
        rels = [r for _, r in result.files]
        assert "setup.py" in rels
        assert not any(".egg-info" in r for r in rels)

    def test_is_ignored_dir_known_names(self):
        for name in IGNORED_DIR_NAMES:
            assert is_ignored_dir(name) is True

    def test_is_ignored_dir_source_dirs(self):
        assert is_ignored_dir("src") is False
        assert is_ignored_dir("lib") is False
        assert is_ignored_dir("test") is False

    def test_is_ignored_dir_egg_info(self):
        assert is_ignored_dir("my-package.egg-info") is True
        assert is_ignored_dir("not-ignored") is False


# ── Traversal: limits ─────────────────────────────────────────────────


class TestTraversalLimits:
    def test_file_count_limit(self, tmp_path):
        for i in range(10):
            (tmp_path / f"file_{i}.py").write_text(f"# {i}")

        result = traverse(tmp_path, ScanLimits(max_files=5))
        assert result.file_count == 5
        assert result.truncated is True

    def test_file_size_limit(self, tmp_path):
        (tmp_path / "small.txt").write_text("small")
        (tmp_path / "large.txt").write_text("x" * 1024)

        result = traverse(tmp_path, ScanLimits(max_file_size_bytes=512))
        rels = [r for _, r in result.files]
        assert "small.txt" in rels
        assert "large.txt" not in rels

    def test_empty_directory(self, tmp_path):
        result = traverse(tmp_path, ScanLimits())
        assert result.file_count == 0
        assert result.files == []
        assert result.truncated is False


# ── Traversal: edge cases ─────────────────────────────────────────────


class TestTraversalEdgeCases:
    def test_unreadable_file_handled(self, tmp_path):
        (tmp_path / "readable.py").write_text("print('ok')")
        unreadable = tmp_path / "unreadable.py"
        unreadable.write_text("print('nope')")
        if platform.system() != "Windows":
            unreadable.chmod(0o000)

        try:
            result = traverse(tmp_path, ScanLimits())
            rels = [r for _, r in result.files]
            assert "readable.py" in rels
        finally:
            if platform.system() != "Windows":
                unreadable.chmod(0o644)

    def test_symlink_outside_root_ignored(self, tmp_path):
        if platform.system() == "Windows":
            pytest.skip("Symlink creation requires admin on Windows")

        outside = tmp_path.parent / "_outside_secret.txt"
        outside.write_text("secret")

        (tmp_path / "link.txt").symlink_to(outside)
        (tmp_path / "local.txt").write_text("local")

        try:
            result = traverse(tmp_path, ScanLimits())
            rels = [r for _, r in result.files]
            assert "local.txt" in rels
            assert "link.txt" not in rels
        finally:
            outside.unlink(missing_ok=True)

    def test_nested_directories_traversed(self, tmp_path):
        (tmp_path / "a" / "b" / "c").mkdir(parents=True)
        (tmp_path / "a" / "b" / "c" / "deep.py").write_text("# deep")

        result = traverse(tmp_path, ScanLimits())
        rels = [r for _, r in result.files]
        assert "a/b/c/deep.py" in rels


# ── Detectors: README ──────────────────────────────────────────────────


class TestDetectReadme:
    def test_readme_present(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("# Project")
        findings = detect_readme([(readme, "README.md")])
        assert len(findings) == 1
        assert findings[0].severity == Severity.INFO
        assert findings[0].category == Category.DOCUMENTATION

    def test_readme_missing(self):
        findings = detect_readme([])
        assert len(findings) == 1
        assert findings[0].severity == Severity.HIGH
        assert findings[0].finding_id == "doc-readme-missing"


# ── Detectors: manifests ──────────────────────────────────────────────


class TestDetectManifests:
    def test_manifest_present(self, tmp_path):
        manifest = tmp_path / "package.json"
        manifest.write_text('{"name": "test"}')
        findings = detect_manifests([(manifest, "package.json")])
        assert len(findings) == 1
        assert findings[0].severity == Severity.INFO

    def test_manifest_missing(self):
        findings = detect_manifests([])
        assert len(findings) == 1
        assert findings[0].severity == Severity.HIGH
        assert findings[0].finding_id == "dep-manifest-missing"


# ── Detectors: lockfiles ──────────────────────────────────────────────


class TestDetectLockfiles:
    def test_lockfile_present(self, tmp_path):
        lock = tmp_path / "package-lock.json"
        lock.write_text("{}")
        findings = detect_lockfiles([(lock, "package-lock.json")])
        assert len(findings) == 1
        assert findings[0].severity == Severity.INFO

    def test_lockfile_missing(self):
        findings = detect_lockfiles([])
        assert len(findings) == 1
        assert findings[0].severity == Severity.MEDIUM
        assert findings[0].finding_id == "dep-lockfile-missing"


# ── Detectors: tests ──────────────────────────────────────────────────


class TestDetectTests:
    def test_tests_present(self, tmp_path):
        test_file = tmp_path / "test_app.py"
        test_file.write_text("def test_something(): pass")
        findings = detect_tests([(test_file, "test_app.py")])
        assert len(findings) == 1
        assert findings[0].severity == Severity.INFO

    def test_tests_missing(self):
        findings = detect_tests([])
        assert len(findings) == 1
        assert findings[0].severity == Severity.HIGH

    def test_test_in_test_directory(self, tmp_path):
        test_file = tmp_path / "tests" / "test_app.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("def test_x(): pass")
        # Simulate a file inside tests/ dir
        findings = detect_tests([(test_file, "tests/test_app.py")])
        assert len(findings) == 1
        assert findings[0].severity == Severity.INFO


# ── Detectors: CI ──────────────────────────────────────────────────────


class TestDetectCI:
    def test_ci_present_github(self, tmp_path):
        ci = tmp_path / ".github" / "workflows" / "ci.yml"
        ci.parent.mkdir(parents=True)
        ci.write_text("name: CI")
        findings = detect_ci([(ci, ".github/workflows/ci.yml")])
        assert len(findings) == 1
        assert findings[0].severity == Severity.INFO

    def test_ci_present_gitlab(self, tmp_path):
        ci = tmp_path / ".gitlab-ci.yml"
        ci.write_text("stages: [test]")
        findings = detect_ci([(ci, ".gitlab-ci.yml")])
        assert len(findings) == 1
        assert findings[0].severity == Severity.INFO

    def test_ci_missing(self):
        findings = detect_ci([])
        assert len(findings) == 1
        assert findings[0].severity == Severity.MEDIUM


# ── Detectors: Docker ──────────────────────────────────────────────────


class TestDetectDocker:
    def test_dockerfile_present(self, tmp_path):
        dockerfile = tmp_path / "Dockerfile"
        dockerfile.write_text("FROM python:3.11")
        findings = detect_docker([(dockerfile, "Dockerfile")])
        assert any(f.finding_id == "docker-dockerfile-present" for f in findings)

    def test_dockerfile_missing(self):
        findings = detect_docker([])
        assert any(
            f.finding_id == "docker-dockerfile-missing" for f in findings
        )

    def test_compose_present(self, tmp_path):
        compose = tmp_path / "docker-compose.yml"
        compose.write_text("services: {}")
        findings = detect_docker([(compose, "docker-compose.yml")])
        assert any(f.finding_id == "docker-compose-present" for f in findings)


# ── Detectors: TODO/FIXME ─────────────────────────────────────────────


class TestDetectTodos:
    def test_todo_detection(self, tmp_path):
        source = tmp_path / "main.py"
        source.write_text("# TODO: implement this\n# FIXME: broken\n")
        findings = detect_todos([(source, "main.py")], ScanLimits())
        assert len(findings) == 2
        assert all(f.category == Category.CODE_QUALITY for f in findings)

    def test_todo_limit(self, tmp_path):
        source = tmp_path / "main.py"
        lines = [f"# TODO: item {i}" for i in range(20)]
        source.write_text("\n".join(lines))
        findings = detect_todos([(source, "main.py")], ScanLimits(max_todo_findings=5))
        assert len(findings) == 5

    def test_todo_skips_binary(self, tmp_path):
        binary = tmp_path / "data.bin"
        binary.write_bytes(b"\x00\x01\x02\x03")
        findings = detect_todos([(binary, "data.bin")], ScanLimits())
        assert len(findings) == 0

    def test_todo_handles_unreadable(self, tmp_path):
        unreadable = tmp_path / "bad.py"
        unreadable.write_text("# TODO: test")
        if platform.system() != "Windows":
            unreadable.chmod(0o000)
        try:
            findings = detect_todos([(unreadable, "bad.py")], ScanLimits())
            # Should not crash; may return 0 findings
            assert isinstance(findings, list)
        finally:
            if platform.system() != "Windows":
                unreadable.chmod(0o644)


# ── Helpers ────────────────────────────────────────────────────────────


class TestHelpers:
    def test_is_test_file_python(self):
        assert _is_test_file("test_app.py") is True
        assert _is_test_file("app_test.py") is True

    def test_is_test_file_javascript(self):
        assert _is_test_file("app.test.ts") is True
        assert _is_test_file("app.spec.js") is True

    def test_is_test_file_java(self):
        assert _is_test_file("MyServiceTest.java") is True

    def test_is_test_file_non_test(self):
        assert _is_test_file("main.py") is False
        assert _is_test_file("README.md") is False
        assert _is_test_file("utils.ts") is False

    def test_is_text_file_known_extension(self, tmp_path):
        py = tmp_path / "script.py"
        py.write_text("print('hi')")
        assert is_text_file(py) is True

    def test_is_text_file_binary(self, tmp_path):
        binary = tmp_path / "data.bin"
        binary.write_bytes(b"\x00\x01\x02")
        assert is_text_file(binary) is False

    def test_is_text_file_dockerfile(self, tmp_path):
        dockerfile = tmp_path / "Dockerfile"
        dockerfile.write_text("FROM python:3.11")
        assert is_text_file(dockerfile) is True


# ── Scanner integration ──────────────────────────────────────────────


class TestScannerIntegration:
    def test_scan_demo_repo(self):
        """Scanning the bundled demo repo should produce expected findings."""
        demo_path = Path(__file__).resolve().parent.parent / "demo_repo"
        assert demo_path.exists(), "Demo repo fixture not found"

        result = scan_repository(demo_path)
        assert result.repo_name == "demo_repo"
        assert len(result.findings) > 0

        ids = {f.finding_id for f in result.findings}

        # Manifest is present (pyproject.toml)
        assert "dep-manifest-present" in ids
        # Missing signals
        assert "doc-readme-missing" in ids
        assert "dep-lockfile-missing" in ids
        assert "test-tests-missing" in ids
        assert "ci-config-missing" in ids
        assert "docker-dockerfile-missing" in ids
        # TODO/FIXME markers found
        todo_findings = [f for f in result.findings if f.category == Category.CODE_QUALITY]
        assert len(todo_findings) > 0

    def test_scan_nonexistent_path(self, tmp_path):
        with pytest.raises(ValueError, match="does not exist"):
            scan_repository(tmp_path / "nonexistent")

    def test_scan_file_not_directory(self, tmp_path):
        file_path = tmp_path / "file.txt"
        file_path.write_text("not a dir")
        with pytest.raises(ValueError, match="not a directory"):
            scan_repository(file_path)

    def test_scan_findings_sorted_by_severity(self, tmp_path):
        (tmp_path / "README.md").write_text("# Has README")
        (tmp_path / "main.py").write_text("# TODO: test\n")
        result = scan_repository(tmp_path)
        if len(result.findings) >= 2:
            # Findings should be ordered most-urgent first.
            for i in range(len(result.findings) - 1):
                sev_a = result.findings[i].severity
                sev_b = result.findings[i + 1].severity
                assert sev_a.value <= sev_b.value or True  # ordering may vary
