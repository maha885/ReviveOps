"""Detectors that analyse collected files and produce Findings.

Each detector function takes the list of (path, relative_path) tuples
collected by the traversal and returns a list of Finding objects.
A finding is produced for both the presence and absence of a signal,
so the UI can show a complete picture.
"""

from __future__ import annotations

import re
from pathlib import Path

from .models import Category, Finding, ScanLimits, Severity

# ── File-name sets ────────────────────────────────────────────────────

README_NAMES: frozenset[str] = frozenset({
    "README", "README.md", "README.rst", "README.txt",
    "readme.md", "readme.txt",
})

MANIFEST_NAMES: frozenset[str] = frozenset({
    "package.json", "pyproject.toml", "requirements.txt", "setup.py",
    "setup.cfg", "Pipfile", "pom.xml", "build.gradle",
    "build.gradle.kts", "Cargo.toml", "go.mod", "Gemfile",
    "composer.json", "Package.swift", "project.clj",
    "deps.edn", "mix.exs",
})

LOCKFILE_NAMES: frozenset[str] = frozenset({
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "poetry.lock", "Pipfile.lock", "Cargo.lock", "go.sum",
    "Gemfile.lock", "composer.lock", "gradle.lockfile",
})

# CI config — checked by path prefix (directories) or exact name.
CI_PATH_PREFIXES: tuple[str, ...] = (
    ".github/workflows/",     # GitHub Actions
    ".circleci/",             # CircleCI
    ".buildkite/",            # Buildkite
)
CI_FILE_NAMES: frozenset[str] = frozenset({
    ".gitlab-ci.yml",
    "Jenkinsfile",
    "azure-pipelines.yml",
    ".travis.yml",
    "bitbucket-pipelines.yml",
    ".drone.yml",
    "cloudbuild.yaml",
})

DOCKERFILE_NAMES: frozenset[str] = frozenset({"Dockerfile"})
COMPOSE_NAMES: frozenset[str] = frozenset({
    "docker-compose.yml", "docker-compose.yaml",
    "compose.yml", "compose.yaml",
})

SCRIPT_NAMES: frozenset[str] = frozenset({
    "Makefile", "makefile", "GNUmakefile",
    "Taskfile.yml", "Taskfile.yaml",
    "Justfile", "justfile",
})

TEST_DIR_NAMES: frozenset[str] = frozenset({
    "test", "tests", "__tests__", "spec", "specs",
})

# ── Helpers ───────────────────────────────────────────────────────────


def _is_test_file(name: str) -> bool:
    """Check if a file name matches common test-file naming conventions."""
    name_lower = name.lower()

    # Prefix patterns (case-insensitive)
    if name_lower.startswith("test_") or name_lower.startswith("test-"):
        return True

    # Case-insensitive suffixes
    ci_suffixes = (
        "_test.py", ".test.ts", ".test.tsx", ".test.js", ".test.jsx",
        ".spec.ts", ".spec.tsx", ".spec.js", ".spec.jsx",
        "_test.go", "_test.rs", "_test.c", "_test.cpp",
        "_spec.rb",
    )
    for suffix in ci_suffixes:
        if name_lower.endswith(suffix):
            return True

    # Case-sensitive suffixes (Java / Kotlin convention)
    cs_suffixes = ("Test.java", "Test.kt", "Test.kts", "Test.dart", "Tests.java")
    for suffix in cs_suffixes:
        if name.endswith(suffix):
            return True

    return False


# File extensions considered safe to read as text.
TEXT_EXTENSIONS: frozenset[str] = frozenset({
    ".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs",
    ".java", ".kt", ".kts", ".scala", ".groovy",
    ".rb", ".go", ".rs", ".c", ".cpp", ".cc", ".cxx",
    ".h", ".hpp", ".hh", ".cs", ".fs", ".vb",
    ".html", ".htm", ".css", ".scss", ".sass", ".less",
    ".vue", ".svelte", ".astro",
    ".json", ".yaml", ".yml", ".toml", ".xml", ".ini",
    ".cfg", ".conf", ".config", ".properties",
    ".md", ".markdown", ".rst", ".txt", ".asciidoc", ".adoc",
    ".sh", ".bash", ".zsh", ".fish", ".ps1", ".bat", ".cmd",
    ".sql", ".graphql", ".gql",
    ".lua", ".php", ".pl", ".pm", ".r", ".swift", ".dart",
    ".tf", ".hcl", ".gradle", ".proto",
})

# Files without a recognised extension that are still text.
TEXT_NO_EXT_NAMES: frozenset[str] = frozenset({
    "Dockerfile", "Makefile", "makefile", "GNUmakefile",
    "Jenkinsfile", "Rakefile", "Gemfile", "Justfile", "justfile",
    ".gitignore", ".dockerignore", ".env", ".editorconfig",
    ".npmrc", ".nvmrc", ".ruby-version", ".python-version",
    ".gitattributes",
})


def is_text_file(path: Path, peek_size: int = 4096) -> bool:
    """Heuristically determine if a file can be safely read as text.

    Uses file extension first, then falls back to checking for null bytes
    in a small chunk read.
    """
    # Known text files without extensions
    if path.name in TEXT_NO_EXT_NAMES:
        return True

    # Dockerfile variants (Dockerfile.dev, Dockerfile.prod, etc.)
    if path.name.startswith("Dockerfile."):
        return True

    suffix = path.suffix.lower()
    if suffix in TEXT_EXTENSIONS:
        return True

    # For files without a recognised extension, check for null bytes.
    if suffix == "" and path.name not in TEXT_NO_EXT_NAMES:
        try:
            with open(path, "rb") as f:
                chunk = f.read(peek_size)
            return b"\x00" not in chunk
        except OSError:
            return False

    # Has an extension but not in the recognised set — skip.
    return False


# Regex for TODO / FIXME / HACK / XXX / BUG markers.
TODO_PATTERN = re.compile(r"\b(TODO|FIXME|HACK|XXX|BUG)\b", re.IGNORECASE)


# ── Detectors ─────────────────────────────────────────────────────────


def detect_readme(files: list[tuple[Path, str]]) -> list[Finding]:
    """Detect README files (present or missing)."""
    readme_files = [
        (path, rel) for path, rel in files
        if path.name in README_NAMES
    ]
    if readme_files:
        path, rel = readme_files[0]
        return [Finding(
            finding_id="doc-readme-present",
            title="README found",
            category=Category.DOCUMENTATION,
            severity=Severity.INFO,
            evidence=f"README detected: {rel}",
            recommendation=(
                "README is present. Verify it includes setup instructions "
                "and usage examples."
            ),
            source_path=rel,
        )]
    return [Finding(
        finding_id="doc-readme-missing",
        title="No README found",
        category=Category.DOCUMENTATION,
        severity=Severity.HIGH,
        evidence="No README file detected in the repository",
        recommendation=(
            "Add a README.md with a project description, setup instructions, "
            "and usage examples."
        ),
        source_path=None,
    )]


def detect_manifests(files: list[tuple[Path, str]]) -> list[Finding]:
    """Detect package manifests (present or missing)."""
    manifest_files = [
        (path, rel) for path, rel in files
        if path.name in MANIFEST_NAMES
    ]
    if manifest_files:
        names = sorted({p.name for p, _ in manifest_files})
        sample = manifest_files[0][1]
        return [Finding(
            finding_id="dep-manifest-present",
            title="Package manifest found",
            category=Category.DEPENDENCIES,
            severity=Severity.INFO,
            evidence=f"Manifest(s) found: {', '.join(names)}",
            recommendation=(
                "Manifest is present. Verify dependencies are pinned and "
                "up to date."
            ),
            source_path=sample,
        )]
    return [Finding(
        finding_id="dep-manifest-missing",
        title="No package manifest found",
        category=Category.DEPENDENCIES,
        severity=Severity.HIGH,
        evidence="No package manifest detected (package.json, pyproject.toml, etc.)",
        recommendation=(
            "Add a package manifest (e.g., package.json, pyproject.toml) "
            "to declare dependencies."
        ),
        source_path=None,
    )]


def detect_lockfiles(files: list[tuple[Path, str]]) -> list[Finding]:
    """Detect dependency lockfiles (present or missing)."""
    lockfile_files = [
        (path, rel) for path, rel in files
        if path.name in LOCKFILE_NAMES
    ]
    if lockfile_files:
        names = sorted({p.name for p, _ in lockfile_files})
        sample = lockfile_files[0][1]
        return [Finding(
            finding_id="dep-lockfile-present",
            title="Dependency lockfile found",
            category=Category.DEPENDENCIES,
            severity=Severity.INFO,
            evidence=f"Lockfile(s) found: {', '.join(names)}",
            recommendation=(
                "Lockfile is present. This helps ensure reproducible builds."
            ),
            source_path=sample,
        )]
    return [Finding(
        finding_id="dep-lockfile-missing",
        title="No dependency lockfile found",
        category=Category.DEPENDENCIES,
        severity=Severity.MEDIUM,
        evidence="No lockfile detected (package-lock.json, poetry.lock, etc.)",
        recommendation=(
            "Add a lockfile (e.g., package-lock.json, poetry.lock) for "
            "reproducible dependency resolution."
        ),
        source_path=None,
    )]


def detect_tests(files: list[tuple[Path, str]]) -> list[Finding]:
    """Detect test files and test directories."""
    test_files: list[tuple[Path, str]] = []
    for path, rel in files:
        # Check file name pattern
        if _is_test_file(path.name):
            test_files.append((path, rel))
            continue
        # Check if any parent directory is a known test directory
        parts = Path(rel).parts
        for part in parts[:-1]:  # exclude the file name itself
            if part.lower() in TEST_DIR_NAMES:
                test_files.append((path, rel))
                break

    if test_files:
        sample = test_files[0][1]
        return [Finding(
            finding_id="test-tests-present",
            title="Tests found",
            category=Category.TESTS,
            severity=Severity.INFO,
            evidence=f"{len(test_files)} test file(s) found, e.g. {sample}",
            recommendation=(
                "Tests are present. Verify they run successfully and cover "
                "critical paths."
            ),
            source_path=sample,
        )]
    return [Finding(
        finding_id="test-tests-missing",
        title="No tests found",
        category=Category.TESTS,
        severity=Severity.HIGH,
        evidence="No test files or test directories detected",
        recommendation=(
            "Add tests (e.g., pytest, Vitest, JUnit) to verify the project "
            "works as expected."
        ),
        source_path=None,
    )]


def detect_ci(files: list[tuple[Path, str]]) -> list[Finding]:
    """Detect CI configuration files."""
    ci_files: list[tuple[Path, str]] = []
    for path, rel in files:
        rel_lower = rel.lower()
        # Check path prefixes (directory-based CI configs)
        for prefix in CI_PATH_PREFIXES:
            if rel_lower.startswith(prefix):
                ci_files.append((path, rel))
                break
        else:
            # Check exact file names
            if path.name in CI_FILE_NAMES:
                ci_files.append((path, rel))

    if ci_files:
        sample = ci_files[0][1]
        return [Finding(
            finding_id="ci-config-present",
            title="CI configuration found",
            category=Category.CI,
            severity=Severity.INFO,
            evidence=f"CI configuration detected: {sample}",
            recommendation=(
                "CI is configured. Verify pipelines cover build, test, "
                "and lint stages."
            ),
            source_path=sample,
        )]
    return [Finding(
        finding_id="ci-config-missing",
        title="No CI configuration found",
        category=Category.CI,
        severity=Severity.MEDIUM,
        evidence=(
            "No CI configuration detected (.github/workflows, "
            ".gitlab-ci.yml, Jenkinsfile, etc.)"
        ),
        recommendation=(
            "Add a CI configuration (e.g., GitHub Actions, GitLab CI) to "
            "automate build and test checks."
        ),
        source_path=None,
    )]


def detect_docker(files: list[tuple[Path, str]]) -> list[Finding]:
    """Detect Dockerfile and Docker Compose files."""
    findings: list[Finding] = []

    dockerfiles = [
        (p, r) for p, r in files
        if p.name in DOCKERFILE_NAMES or p.name.startswith("Dockerfile.")
    ]
    compose_files = [
        (p, r) for p, r in files
        if p.name in COMPOSE_NAMES
    ]

    if dockerfiles:
        sample = dockerfiles[0][1]
        findings.append(Finding(
            finding_id="docker-dockerfile-present",
            title="Dockerfile found",
            category=Category.CONTAINERIZATION,
            severity=Severity.INFO,
            evidence=f"Dockerfile detected: {sample}",
            recommendation=(
                "Dockerfile is present. Verify the image builds successfully."
            ),
            source_path=sample,
        ))
    else:
        findings.append(Finding(
            finding_id="docker-dockerfile-missing",
            title="No Dockerfile found",
            category=Category.CONTAINERIZATION,
            severity=Severity.LOW,
            evidence="No Dockerfile detected in the repository",
            recommendation=(
                "Add a Dockerfile to enable reproducible containerised builds."
            ),
            source_path=None,
        ))

    if compose_files:
        sample = compose_files[0][1]
        findings.append(Finding(
            finding_id="docker-compose-present",
            title="Docker Compose configuration found",
            category=Category.CONTAINERIZATION,
            severity=Severity.INFO,
            evidence=f"Docker Compose file detected: {sample}",
            recommendation="Docker Compose is configured. Verify services start correctly.",
            source_path=sample,
        ))

    return findings


def detect_todos(
    files: list[tuple[Path, str]],
    limits: ScanLimits,
) -> list[Finding]:
    """Detect TODO/FIXME/HACK/XXX/BUG markers in text files.

    Each occurrence becomes a separate finding with the file path and line
    number as evidence. The total number of findings is capped by
    ``limits.max_todo_findings``.
    """
    findings: list[Finding] = []
    count = 0

    for path, rel in files:
        if count >= limits.max_todo_findings:
            break

        if not is_text_file(path):
            continue

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line_num, line in enumerate(f, 1):
                    if count >= limits.max_todo_findings:
                        break
                    match = TODO_PATTERN.search(line)
                    if match:
                        marker = match.group(1).upper()
                        count += 1
                        evidence_line = line.strip()[:200]
                        findings.append(Finding(
                            finding_id=f"code-{marker.lower()}-{count:03d}",
                            title=f"{marker} in {rel}",
                            category=Category.CODE_QUALITY,
                            severity=Severity.LOW,
                            evidence=f"Line {line_num}: {evidence_line}",
                            recommendation=(
                                f"Review and address this {marker} marker "
                                "to reduce technical debt."
                            ),
                            source_path=rel,
                        ))
        except OSError:
            # Skip unreadable files gracefully.
            continue

    return findings
