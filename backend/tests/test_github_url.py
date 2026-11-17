import pytest
from hypothesis import given, settings, strategies as st

from app.services.github_url import (
    GitHubRepo,
    InvalidGitHubUrl,
    archive_url,
    parse_github_url,
)

ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
SAFE = set(ALPHABET)

name = st.text(alphabet=ALPHABET, min_size=1, max_size=30).filter(
    lambda s: ".." not in s and s not in (".", "..") and not s.endswith(".git")
)
branch = st.lists(name, min_size=1, max_size=3).map("/".join)
suffix = st.sampled_from(["", "/", ".git", ".git/"]) | branch.map(
    lambda b: f"/tree/{b}"
) | branch.map(lambda b: f"/tree/{b}/")


@given(name, name, suffix)
def test_valid_roundtrip(owner, repo, suf):
    r = parse_github_url(f"https://github.com/{owner}/{repo}{suf}")
    assert r == GitHubRepo(owner, repo)
    assert set(r.owner) <= SAFE and set(r.repo) <= SAFE


@given(name, name)
def test_archive_url_prefix_and_safe(owner, repo):
    u = archive_url(GitHubRepo(owner, repo))
    prefix = "https://codeload.github.com/"
    assert u.startswith(prefix) and u.endswith("/zip/HEAD")
    assert set(u[len(prefix):-len("/zip/HEAD")]) <= SAFE | {"/"}
    assert u == f"{prefix}{owner}/{repo}/zip/HEAD"


FORBIDDEN_INSERTS = [
    "\n", " ", "\t", "\x00", "%", "\\", "?", "#", "@", ":", "/", "é", "..", "\u2024",
]


@given(name, name, st.sampled_from(FORBIDDEN_INSERTS), st.booleans())
def test_forbidden_element_in_name_rejected(owner, repo, bad, in_owner):
    if in_owner:
        url = f"https://github.com/{owner}{bad}/{repo}"
    else:
        url = f"https://github.com/{owner}/{repo}{bad}x"
    if bad == "/" and not in_owner:
        # becomes /repo/x : extra segment
        pass
    with pytest.raises(InvalidGitHubUrl):
        parse_github_url(url)


@given(
    name,
    name,
    st.sampled_from(
        [
            ("http://github.com/{o}/{r}"),
            ("https://evil.com/{o}/{r}"),
            ("https://github.com.evil.com/{o}/{r}"),
            ("https://www.github.com/{o}/{r}"),
            ("https://user@github.com/{o}/{r}"),
            ("https://github.com:443/{o}/{r}"),
            ("https://github.com/{o}/{r}?x=1"),
            ("https://github.com/{o}/{r}#frag"),
            ("https://github.com/{o}/{r}/issues"),
            ("https://github.com/{o}/{r}/tree/a/../b"),
            ("https://github.com/{o}/{r}/tree/a%2Fb"),
            ("https://github.com/{o}/{r}/tree/a b"),
            ("https://github.com/{o}/{r}\n"),
            ("https://127.0.0.1/{o}/{r}"),
            ("https://github.com/{o}"),
            ("https://github.com/../{r}"),
            ("https://github.com/{o}/.."),
            ("https://github.com/{o}/.git"),
            ("ftp://github.com/{o}/{r}"),
            ("github.com/{o}/{r}"),
        ]
    ),
)
def test_forbidden_structure_rejected(owner, repo, template):
    with pytest.raises(InvalidGitHubUrl):
        parse_github_url(template.format(o=owner, r=repo))


@given(st.text(max_size=300))
@settings(max_examples=300)
def test_arbitrary_text_accepted_only_if_safe(s):
    try:
        r = parse_github_url(s)
    except InvalidGitHubUrl:
        return
    assert set(r.owner) <= SAFE and set(r.repo) <= SAFE
    assert r.owner not in (".", "..") and r.repo not in (".", "..", "")


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com.evil.com/a/b",
        "https://evilgithub.com/a/b",
        "https://github.com@evil.com/a/b",
        "https://a@github.com/a/b",
        "https://github.com:8080/a/b",
        "https://github.com/a/b?x=1",
        "https://github.com/a/b#x",
        "https://github.com/../b",
        "https://github.com/a/..",
        "https://github.com/a/b/../c",
        "https://github.com/a/b\n",
        "https://github.com/a/b\r\n",
        " https://github.com/a/b",
        "https://github.com/a/b ",
        "https://github.com/a/%2e%2e",
        "https://github.com/a\\b",
        "https://github.com/a/.git",
        "https://github.com/a/b/tree/",
        "https://github.com/a/b/blob/main/x",
        "https://github.com/a/b/c",
        "https://gıthub.com/a/b",  # dotless i
        "https://github.com/а/b",  # cyrillic a
        "https://github.com/a/b" + "x" * 200,
        "",
    ],
)
def test_explicit_rejections(url):
    with pytest.raises(InvalidGitHubUrl):
        parse_github_url(url)


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://github.com/a/b", ("a", "b")),
        ("https://github.com/a/b/", ("a", "b")),
        ("https://github.com/a/b.git", ("a", "b")),
        ("https://github.com/a/b/tree/main", ("a", "b")),
        ("https://github.com/a/b/tree/feature/x-1.2/", ("a", "b")),
        ("https://github.com/a/b.c_d", ("a", "b.c_d")),
    ],
)
def test_explicit_accepts(url, expected):
    assert parse_github_url(url) == GitHubRepo(*expected)
