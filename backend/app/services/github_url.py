"""Strict parsing of public GitHub repository URLs.

Pure functions, no network. Accepted form (exactly, matched with ``fullmatch``
against the raw string, never against a leniently parsed ``urlparse`` result)::

    https://github.com/<owner>/<repo>[.git][/][/tree/<branch>[/]]

Decisions:
- Host must be exactly lowercase ``github.com`` (``www.`` is NOT accepted).
- ``.git`` is stripped once from the repo name; a repo that is empty, ``.``,
  ``..`` or ``.git`` after that is rejected.
- Owner and repo may not contain ``..`` anywhere (conservative).
- The ``/tree/<branch>`` part is ignored, but validated: each segment must
  match ``[A-Za-z0-9._-]+`` and may not be ``.`` or contain ``..``.
- Input longer than ``MAX_URL_LENGTH`` is rejected.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

MAX_URL_LENGTH = 200

_NAME = r"[A-Za-z0-9._-]+"
_URL_RE = re.compile(
    rf"https://github\.com/(?P<owner>{_NAME})/(?P<repo>{_NAME})"
    rf"(?:/tree/(?P<branch>{_NAME}(?:/{_NAME})*))?/?",
    re.ASCII,
)
_SAFE_RE = re.compile(r"[A-Za-z0-9._-]+", re.ASCII)


class InvalidGitHubUrl(ValueError):
    """The URL is not an accepted public GitHub repository URL."""


@dataclass(frozen=True)
class GitHubRepo:
    owner: str
    repo: str


def _bad_name(name: str) -> bool:
    return (
        not name
        or name in (".", "..", ".git")
        or ".." in name
        or _SAFE_RE.fullmatch(name) is None
    )


def parse_github_url(url: str) -> GitHubRepo:
    if not isinstance(url, str):
        raise InvalidGitHubUrl("URL must be a string.")
    if len(url) > MAX_URL_LENGTH:
        raise InvalidGitHubUrl("URL is too long.")
    m = _URL_RE.fullmatch(url)
    if m is None:
        raise InvalidGitHubUrl(
            "Only URLs like https://github.com/<owner>/<repo> are accepted."
        )
    owner = m.group("owner")
    repo = m.group("repo")
    if repo.endswith(".git"):
        repo = repo[: -len(".git")]
    branch = m.group("branch")
    if branch is not None:
        for seg in branch.split("/"):
            if seg in (".", "..") or ".." in seg:
                raise InvalidGitHubUrl("Invalid branch in URL.")
    if _bad_name(owner) or _bad_name(repo):
        raise InvalidGitHubUrl("Invalid owner or repository name.")
    return GitHubRepo(owner=owner, repo=repo)


def archive_url(repo: GitHubRepo) -> str:
    if _bad_name(repo.owner) or _bad_name(repo.repo):
        raise InvalidGitHubUrl("Invalid owner or repository name.")
    return f"https://codeload.github.com/{repo.owner}/{repo.repo}/zip/HEAD"
