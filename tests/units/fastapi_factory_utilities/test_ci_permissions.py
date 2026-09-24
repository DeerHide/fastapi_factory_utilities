"""Guardrail: PR-path CI jobs must not carry unused write token scopes."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CI_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "ci.yml"
_CANARY_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "deps-canary.yml"

# Jobs that run on pull_request and must stay least-privilege.
_PR_PATH_JOBS = ("setup", "mandatory-only", "dependency-scan", "pre-commit")
_WRITE_PERMISSIONS = {
    "contents": "write",
    "packages": "write",
    "id-token": "write",
    "security-events": "write",
}


def _load_yaml_mapping(path: Path) -> Mapping[str, Any]:
    document = yaml.safe_load(path.read_text())
    assert isinstance(document, Mapping), f"{path.name}: expected mapping root, got {type(document).__name__}"
    return document


def _load_jobs(path: Path) -> Mapping[str, Any]:
    document = _load_yaml_mapping(path)
    jobs = document.get("jobs")
    assert isinstance(jobs, Mapping), f"{path.name}: jobs must be a mapping"
    return jobs


def _job_permissions(jobs: Mapping[str, Any], job_name: str) -> Mapping[str, Any]:
    assert job_name in jobs, f"missing job {job_name}"
    permissions = jobs[job_name].get("permissions") or {}
    assert isinstance(permissions, Mapping), (
        f"{job_name} permissions must be a mapping "
        f"(got {type(permissions).__name__!r}: {permissions!r}; "
        "string forms like read-all/write-all are not allowed here)"
    )
    return permissions


@pytest.mark.parametrize("job_name", _PR_PATH_JOBS)
def test_pr_path_jobs_are_contents_read_only(job_name: str) -> None:
    """PR jobs must not grant write-scoped GITHUB_TOKEN permissions."""
    jobs = _load_jobs(_CI_WORKFLOW)
    permissions = _job_permissions(jobs, job_name)
    assert permissions.get("contents") == "read"
    for key, write_value in _WRITE_PERMISSIONS.items():
        assert permissions.get(key) != write_value, f"{job_name} must not set {key}: {write_value} (got {permissions})"
    # Catch any future write-scoped key, not only the known set above.
    for key, value in permissions.items():
        assert value != "write", f"{job_name} must not set {key}: write (got {permissions})"


def test_dependency_snapshot_is_main_or_tag_only_with_contents_write() -> None:
    """Snapshot publish keeps contents:write but is gated off the PR path."""
    jobs = _load_jobs(_CI_WORKFLOW)
    permissions = _job_permissions(jobs, "dependency-snapshot")
    assert permissions.get("contents") == "write"
    condition = jobs["dependency-snapshot"].get("if", "")
    assert "refs/heads/main" in condition
    assert "refs/tags/v" in condition or "startsWith(github.ref" in condition


def test_deps_canary_is_contents_read_only() -> None:
    """Scheduled canary does not need packages:write."""
    jobs = _load_jobs(_CANARY_WORKFLOW)
    permissions = _job_permissions(jobs, "canary")
    assert permissions.get("contents") == "read"
    assert permissions.get("packages") != "write"
    for key, value in permissions.items():
        assert value != "write", f"canary must not set {key}: write (got {permissions})"
