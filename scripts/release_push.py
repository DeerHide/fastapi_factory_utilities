#!/usr/bin/env python3
"""Commit the rewritten ``CHANGELOG.md`` to the default branch and tag it, via the GitHub API.

Used by the ``cut-release`` CI job with a GitHub App installation token that is
a bypass actor on the default-branch ruleset.

* ``createCommitOnBranch`` produces a GitHub-signed (verified) commit, which
  keeps the ``required_signatures`` history clean, and its ``expectedHeadOid``
  makes the write fail if the branch moved since CI tested ``GITHUB_SHA``.
* The annotated ``vX.Y.Z`` tag is then created on that commit. Because the
  token is an App token (not ``GITHUB_TOKEN``), the tag push triggers the CI
  workflow on ``refs/tags/v*``, which runs the existing ``release`` job
  (``pypi`` environment approval, trusted publishing).

Required env: ``GH_TOKEN``, ``GITHUB_REPOSITORY``, ``GITHUB_SHA``,
``RELEASE_TAG``, ``RELEASE_VERSION``, ``BRANCH``.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = os.environ.get("GITHUB_API_URL", "https://api.github.com")


def call(method: str, path: str, payload: dict) -> dict:
    """Send an authenticated JSON request; exit with the API message on error."""
    request = urllib.request.Request(
        f"{API}{path}",
        data=json.dumps(payload).encode(),
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        sys.exit(f"{method} {path} failed: HTTP {error.code} {error.read().decode(errors='replace')[:500]}")


def main() -> int:
    """Create the release commit and tag."""
    repo = os.environ["GITHUB_REPOSITORY"]
    head = os.environ["GITHUB_SHA"]
    tag = os.environ["RELEASE_TAG"]
    version = os.environ["RELEASE_VERSION"]
    branch = os.environ["BRANCH"]

    mutation = """
    mutation($input: CreateCommitOnBranchInput!) {
      createCommitOnBranch(input: $input) { commit { oid } }
    }"""
    variables = {
        "input": {
            "branch": {"repositoryNameWithOwner": repo, "branchName": branch},
            "expectedHeadOid": head,
            "message": {"headline": f"chore(release): prepare release {tag}"},
            "fileChanges": {
                "additions": [
                    {
                        "path": "CHANGELOG.md",
                        "contents": base64.b64encode(Path("CHANGELOG.md").read_bytes()).decode(),
                    }
                ]
            },
        }
    }
    result = call("POST", "/graphql", {"query": mutation, "variables": variables})
    if result.get("errors"):
        sys.exit(f"createCommitOnBranch failed: {json.dumps(result['errors'])[:500]}")
    oid = result["data"]["createCommitOnBranch"]["commit"]["oid"]
    print(f"Release commit {oid} on {branch}")

    tag_object = call(
        "POST",
        f"/repos/{repo}/git/tags",
        {"tag": tag, "message": f"Release version {version}", "object": oid, "type": "commit"},
    )
    call("POST", f"/repos/{repo}/git/refs", {"ref": f"refs/tags/{tag}", "sha": tag_object["sha"]})
    print(f"Tagged {tag} -> {oid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
