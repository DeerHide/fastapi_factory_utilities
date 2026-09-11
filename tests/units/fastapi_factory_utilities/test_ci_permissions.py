"""Guardrail: PR-path CI jobs must not carry unused write token scopes."""

from pathlib import Path

import pytest
import yaml

_CI_WORKFLOW = Path(".github/workflows/ci.yml")
_CANARY_WORKFLOW = Path(".github/workflows/deps-canary.yml")

# Jobs that run on pull_request and must stay least-privilege.
_PR_PATH_JOBS = ("setup", "mandatory-only", "dependency-scan", "pre-commit")
_WRITE_PERMISSIONS = {
    "contents": "write",
    "packages": "write",
    "id-token": "write",
    "security-events": "write",
}


def _load_jobs(path: Path) -> dict[str, dict]:
    document = yaml.safe_load(path.read_text())
    assert isinstance(document.get("jobs"), dict)
    return document["jobs"]


@pytest.mark.parametrize("job_name", _PR_PATH_JOBS)
def test_pr_path_jobs_are_contents_read_only(job_name: str) -> None:
    """PR jobs must not grant write-scoped GITHUB_TOKEN permissions."""
    jobs = _load_jobs(_CI_WORKFLOW)
    assert job_name in jobs, f"missing job {job_name}"
    permissions = jobs[job_name].get("permissions") or {}
    assert permissions.get("contents") == "read"
    for key, write_value in _WRITE_PERMISSIONS.items():
        assert permissions.get(key) != write_value, (
            f"{job_name} must not set {key}: {write_value} (got {permissions})"
        )


def test_dependency_snapshot_is_main_or_tag_only_with_contents_write() -> None:
    """Snapshot publish keeps contents:write but is gated off the PR path."""
    jobs = _load_jobs(_CI_WORKFLOW)
    snapshot = jobs["dependency-snapshot"]
    assert snapshot["permissions"].get("contents") == "write"
    condition = snapshot.get("if", "")
    assert "refs/heads/main" in condition
    assert "refs/tags/v" in condition or "startsWith(github.ref" in condition


def test_deps_canary_is_contents_read_only() -> None:
    """Scheduled canary does not need packages:write."""
    jobs = _load_jobs(_CANARY_WORKFLOW)
    permissions = jobs["canary"]["permissions"]
    assert permissions.get("contents") == "read"
    assert permissions.get("packages") != "write"
