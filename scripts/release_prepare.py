#!/usr/bin/env python3
"""Compute the next release from Conventional Commits and rewrite ``CHANGELOG.md``.

Vendored from ``Laelidona/github-actions/actions/release-prepare`` (the
mechanism velmios_lib uses), trimmed for FFU:

* the package version comes from the git tag (poetry-dynamic-versioning), so no
  manifest file is bumped;
* there is no ``dependency refresh`` fallback: with nothing releasable the
  script emits ``released=false`` and the workflow cuts nothing.

Bump rules, over commits since the latest ``vX.Y.Z`` tag, ``chore(release)``
commits excluded:

* ``type!:`` subject or ``BREAKING CHANGE`` footer -> major
* any ``feat`` -> minor
* otherwise -> patch

Release body, first match wins:

1. curated bullets under ``## [Unreleased]``;
2. notes generated from commit subjects (``feat`` -> Added, ``fix`` -> Fixed,
   ``refactor``/``perf``/``revert``/other -> Changed; ``chore``/``ci``/``docs``/
   ``test``/``style``/``build`` omitted);
3. nothing -> skip.

Outputs ``released``, ``version``, ``tag`` and ``bump`` to ``$GITHUB_OUTPUT``
(stdout when unset). ``--dry-run`` prints the plan without writing the file.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

CHANGELOG = Path("CHANGELOG.md")

TAG_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")
FEAT_RE = re.compile(r"^feat(\([^)]+\))?:")
BREAKING_SUBJECT_RE = re.compile(r"^[a-zA-Z]+(\([^)]+\))?!:")
CONVENTIONAL_RE = re.compile(r"^(?P<type>[a-zA-Z]+)(?:\((?P<scope>[^)]+)\))?!?:\s*(?P<summary>.+)$")
CHORE_RELEASE_RE = re.compile(r"^chore\(release\)")
UNRELEASED_BODY_RE = re.compile(
    r"^## \[Unreleased\][^\n]*\n(.*?)(?=^## \[|^\[Unreleased\]:|\Z)",
    flags=re.MULTILINE | re.DOTALL,
)
UNRELEASED_LINK_RE = re.compile(r"^\[Unreleased\]: [^\n]+\n", flags=re.MULTILINE)
BULLET_RE = re.compile(r"^\s*[-*]\s+\S", flags=re.MULTILINE)
VERSIONED_HEADER_RE = re.compile(r"^## \[(?P<link>v?)(?P<ver>\d+\.\d+\.\d+)\]", flags=re.MULTILINE)

EXCLUDE_TYPES = frozenset({"chore", "ci", "docs", "test", "style", "build"})


def run(*args: str) -> str:
    """Run a command and return its stdout."""
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


def last_tag() -> str | None:
    """Return the latest ``vX.Y.Z`` tag reachable from HEAD, or ``None``."""
    try:
        return run("git", "describe", "--tags", "--abbrev=0", "--match", "v[0-9]*.[0-9]*.[0-9]*").strip()
    except subprocess.CalledProcessError:
        return None


def commits_since(tag: str | None) -> list[tuple[str, str]]:
    """Return ``(subject, body)`` for commits in ``tag..HEAD``, minus ``chore(release)``."""
    separator = "<<<COMMIT>>>"
    out = run("git", "log", f"--pretty=format:{separator}%s%n%b", f"{tag}..HEAD" if tag else "HEAD")
    commits: list[tuple[str, str]] = []
    for raw_chunk in out.split(separator):
        chunk = raw_chunk.strip("\n")
        if not chunk:
            continue
        subject, _, body = chunk.partition("\n")
        if CHORE_RELEASE_RE.match(subject):
            continue
        commits.append((subject, body))
    return commits


def bump_kind(commits: list[tuple[str, str]]) -> str:
    """Return ``major``, ``minor`` or ``patch``."""
    bump = "patch"
    for subject, body in commits:
        if BREAKING_SUBJECT_RE.match(subject) or "BREAKING CHANGE" in body or "BREAKING-CHANGE" in body:
            return "major"
        if FEAT_RE.match(subject):
            bump = "minor"
    return bump


def next_version(prev: str, bump: str) -> str:
    """Bump ``prev`` (``vX.Y.Z``) by ``bump``."""
    match = TAG_RE.match(prev)
    if not match:
        sys.exit(f"unexpected previous tag format: {prev!r}")
    major, minor, patch = (int(part) for part in match.groups())
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def unreleased_body(text: str) -> str:
    """Return the body of ``## [Unreleased]``."""
    match = UNRELEASED_BODY_RE.search(text)
    return match.group(1).strip("\n") if match else ""


def commit_notes(commits: list[tuple[str, str]]) -> str:
    """Render user-facing commit subjects as Keep a Changelog sections."""
    sections: dict[str, list[str]] = {"Added": [], "Fixed": [], "Changed": []}
    for subject, _body in commits:
        match = CONVENTIONAL_RE.match(subject)
        if not match:
            sections["Changed"].append(f"- {subject}")
            continue
        ctype = match.group("type").lower()
        if ctype in EXCLUDE_TYPES:
            continue
        scope = match.group("scope")
        summary = match.group("summary").strip()
        bullet = f"- {scope}: {summary}" if scope else f"- {summary}"
        heading = {"feat": "Added", "fix": "Fixed"}.get(ctype, "Changed")
        sections[heading].append(bullet)
    return "\n\n".join(f"### {heading}\n\n" + "\n".join(bullets) for heading, bullets in sections.items() if bullets)


@dataclass(frozen=True)
class Release:
    """A release about to be written into ``CHANGELOG.md``."""

    version: str
    date: str
    body: str
    prev_tag: str
    prefix: str
    repo: str


def rewrite_changelog(text: str, release: Release) -> str:
    """Finalize ``[Unreleased]`` as ``## [version] - date`` and refresh compare links."""
    version, date, body, prev_tag, repo = release.version, release.date, release.body, release.prev_tag, release.repo
    heading = f"{release.prefix}{version}"
    replacement = f"## [Unreleased]\n\n## [{heading}] - {date}\n\n{body.strip()}\n\n"
    new_text, count = UNRELEASED_BODY_RE.subn(lambda _m: replacement, text, count=1)
    if count != 1:
        sys.exit("could not locate [Unreleased] section to rewrite")
    new_link = (
        f"[Unreleased]: https://github.com/{repo}/compare/v{version}...HEAD\n"
        f"[{heading}]: https://github.com/{repo}/compare/{prev_tag}...v{version}\n"
    )
    new_text, count = UNRELEASED_LINK_RE.subn(lambda _m: new_link, new_text, count=1)
    if count == 0:
        new_text = new_text.rstrip("\n") + "\n\n" + new_link
    return new_text


def emit_outputs(**kwargs: str) -> None:
    """Write outputs to ``$GITHUB_OUTPUT`` or stdout."""
    path = os.environ.get("GITHUB_OUTPUT")
    lines = "".join(f"{key}={value}\n" for key, value in kwargs.items())
    if path:
        with Path(path).open("a", encoding="utf-8") as handle:
            handle.write(lines)
    else:
        print(lines, end="")


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="print the plan, do not write CHANGELOG.md")
    args = parser.parse_args(argv)

    if not CHANGELOG.exists():
        sys.exit("CHANGELOG.md not found")
    text = CHANGELOG.read_text(encoding="utf-8")
    prev_tag = last_tag()
    commits = commits_since(prev_tag)

    curated = unreleased_body(text)
    if BULLET_RE.search(curated):
        body = curated
    else:
        body = commit_notes(commits)
        if body:
            print("::warning::[Unreleased] has no curated entries; generating notes from commits.")
    if not body:
        print("No curated [Unreleased] entries and no user-facing commits since last tag; skipping release.")
        emit_outputs(released="false")
        return 0

    prev = prev_tag or "v0.0.0"
    bump = bump_kind(commits)
    version = next_version(prev, bump)
    header = VERSIONED_HEADER_RE.search(text)
    prefix = header.group("link") if header else ""
    repo = os.environ.get("GITHUB_REPOSITORY", "DeerHide/fastapi_factory_utilities")
    date = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    new_text = rewrite_changelog(
        text, Release(version=version, date=date, body=body, prev_tag=prev, prefix=prefix, repo=repo)
    )

    print(f"Cutting release v{version} ({bump} bump from {prev})")
    if args.dry_run:
        print(new_text[: new_text.find(f"## [{prefix}{version}]") + 2000])
    else:
        CHANGELOG.write_text(new_text, encoding="utf-8")
    emit_outputs(released="true", version=version, tag=f"v{version}", bump=bump)
    return 0


if __name__ == "__main__":
    sys.exit(main())
