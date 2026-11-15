"""Main scanner that orchestrates traversal and detection.

Usage::

    from app.scanner import scan_repository
    from pathlib import Path

    result = scan_repository(Path("/home/user/my-project"))
    for finding in result.findings:
        print(f"[{finding.severity.value}] {finding.title}: {finding.evidence}")
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .detectors import (
    detect_ci,
    detect_docker,
    detect_lockfiles,
    detect_manifests,
    detect_readme,
    detect_tests,
    detect_todos,
)
from .models import Finding, ScanLimits, ScanResult, SEVERITY_ORDER
from .traversal import traverse


def scan_repository(
    root: Path,
    limits: ScanLimits | None = None,
) -> ScanResult:
    """Scan a repository and return all findings.

    Args:
        root:  Path to the repository root directory.
        limits: Optional safety limits. Defaults to ``ScanLimits()`` defaults.

    Returns:
        ScanResult with findings, file count, and any errors.

    Raises:
        ValueError: If *root* does not exist or is not a directory.
    """
    if limits is None:
        limits = ScanLimits()

    if not root.exists():
        raise ValueError(f"Path does not exist: {root}")
    if not root.is_dir():
        raise ValueError(f"Path is not a directory: {root}")

    # Traverse the directory tree.
    traversal = traverse(root, limits)

    # Run all detectors.
    findings: list[Finding] = []
    findings.extend(detect_readme(traversal.files))
    findings.extend(detect_manifests(traversal.files))
    findings.extend(detect_lockfiles(traversal.files))
    findings.extend(detect_tests(traversal.files))
    findings.extend(detect_ci(traversal.files))
    findings.extend(detect_docker(traversal.files))
    findings.extend(detect_todos(traversal.files, limits))

    # Sort findings by severity (most urgent first).
    findings.sort(key=lambda f: SEVERITY_ORDER[f.severity])

    return ScanResult(
        repo_name=root.name,
        scanned_at=datetime.now(timezone.utc).isoformat(),
        findings=findings,
        file_count=traversal.file_count,
        truncated=traversal.truncated,
        errors=traversal.errors,
    )
