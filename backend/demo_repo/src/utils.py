"""Utility functions.

TODO: Add input validation for all public functions.
"""


def greet(name: str) -> str:
    """Return a greeting message."""
    # TODO: handle empty or None names
    return f"Hello, {name}!"


def parse_config(path: str) -> dict:
    """Parse a configuration file."""
    # FIXME: only supports .ini format, add .yaml support
    return {}
