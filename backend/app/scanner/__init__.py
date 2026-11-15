"""ReviveOps repository scanner package.

Provides safe, read-only repository scanning with configurable limits.
Never executes scripts or commands discovered in the scanned repository.
"""

from .models import Category, Finding, ScanLimits, ScanResult, Severity
from .scanner import scan_repository
from .traversal import IGNORED_DIR_NAMES, TraversalResult, is_ignored_dir, traverse

__all__ = [
    "Category",
    "Finding",
    "ScanLimits",
    "ScanResult",
    "Severity",
    "scan_repository",
    "traverse",
    "TraversalResult",
    "IGNORED_DIR_NAMES",
    "is_ignored_dir",
]
